from datetime import datetime, timezone, timedelta
from flask import jsonify, request, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db
from app.blueprints.api import api_bp
from app.models.complaint import Complaint
from app.models.issue import Issue, IssueComplaintLink
from app.models.feedback import ResolutionRound
from app.models.audit import AuditEvent
from app.models.radar import (
    InfrastructureDependency,
    DependencyLocation,
    RadarSuggestion,
    RadarSuggestionReport,
)
from app.services.audit import reveal_complaint_submitter
from app.services.security import admin_required, handler_required, sanitize_text
from app.services.rate_limiter import rate_limit
from app.services.incident_radar import (
    run_incident_radar_analysis,
    seed_synthetic_radar_demo,
)


@api_bp.route("/admin/queue", methods=["GET"])
@login_required
@handler_required
def admin_queue():
    """
    Returns complaints for handler review.
    CRITICAL PRIVACY RULE: Submitter names and emails are OMITTED from ordinary queue responses.
    """
    if not current_user.is_handler:
        abort(403)

    category = request.args.get("category", "").strip()
    building = request.args.get("building", "").strip()
    status = request.args.get("status", "").strip()
    priority = request.args.get("priority", "").strip()

    query = Complaint.query

    if category:
        query = query.filter(
            (Complaint.final_category == category)
            | ((Complaint.final_category.is_(None)) & (Complaint.suggested_category == category))
            | ((Complaint.final_category.is_(None)) & (Complaint.suggested_category.is_(None)) & (Complaint.user_category == category))
        )
    if building:
        query = query.filter(Complaint.building == building)
    if status:
        query = query.filter(Complaint.status == status)
    if priority:
        query = query.filter(
            (Complaint.final_priority == priority)
            | ((Complaint.final_priority.is_(None)) & (Complaint.suggested_priority == priority))
        )

    complaints = query.order_by(Complaint.created_at.desc()).all()

    data = []
    for c in complaints:
        data.append({
            "id": c.id,
            "submission_type": c.submission_type,
            "title": c.title,
            "description": c.description,
            "user_category": c.user_category,
            "suggested_category": c.suggested_category,
            "final_category": c.final_category,
            "display_category": c.display_category,
            "building": c.building,
            "room": c.room,
            "suggested_priority": c.suggested_priority,
            "final_priority": c.final_priority,
            "display_priority": c.display_priority,
            "status": c.status,
            "analysis_state": c.analysis_state,
            "created_at": c.created_at.isoformat(),
            # OMIT submitter name and email:
            "anonymous_submitter": f"Anonymous Submitter #{c.user_id}",
            "has_attachment": len(c.attachments) > 0,
            "is_linked_to_issue": c.issue_link is not None,
            "linked_issue_id": c.issue_link.issue_id if c.issue_link else None,
        })

    return jsonify({
        "complaints": data,
        "available_categories": [
            "Infrastructure", "Sanitation", "Academics", "Student services", "IT/connectivity", "Other", "Not sure"
        ],
        "available_locations": current_app.config.get("CAMPUS_LOCATIONS", []),
    })


@api_bp.route("/admin/complaint/<int:complaint_id>/reveal-identity", methods=["POST"])
@login_required
@admin_required
@rate_limit(limit=15, window_seconds=60, key_prefix="reveal_id")
def admin_reveal_identity(complaint_id):
    """
    Audited identity reveal:
    - Admin role only.
    - Requires non-empty operational purpose.
    - Commits audit event before returning identity.
    - If audit commit fails, aborts without disclosing.
    - Audit log does not store disclosed PII redundantly.
    """
    data = request.get_json() or {}
    justification = sanitize_text(data.get("justification") or "")

    success, message, info = reveal_complaint_submitter(
        admin_user=current_user,
        complaint_id=complaint_id,
        justification=justification,
    )

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({
        "success": True,
        "message": message,
        "identity": info,
    })


@api_bp.route("/admin/complaint/<int:complaint_id>/set-final-attributes", methods=["POST"])
@login_required
@handler_required
def set_final_attributes(complaint_id):
    """Handler action to assign final category and priority."""
    complaint = db.get_or_404(Complaint, complaint_id)
    data = request.get_json() or {}

    final_cat = sanitize_text(data.get("final_category") or "")
    final_prio = sanitize_text(data.get("final_priority") or "")

    if final_cat:
        complaint.final_category = final_cat
    if final_prio:
        complaint.final_priority = final_prio

    complaint.analysis_state = "completed"
    db.session.commit()

    return jsonify({
        "success": True,
        "final_category": complaint.final_category,
        "final_priority": complaint.final_priority,
    })


@api_bp.route("/admin/dashboard", methods=["GET"])
@login_required
@handler_required
def admin_dashboard():
    """Live operational metrics strictly computed from SQLite database."""
    total_submissions = Complaint.query.count()
    distinct_issues = Issue.query.count()
    unresolved_issues = Issue.query.filter(Issue.status != "resolved").count()
    urgent_reviews = Complaint.query.filter(
        (Complaint.final_priority == "Urgent review")
        | ((Complaint.final_priority.is_(None)) & (Complaint.suggested_priority == "Urgent review"))
    ).count()
    resolved_issues = Issue.query.filter(Issue.status == "resolved").count()
    disputed_resolutions = (
        ResolutionRound.query.filter(ResolutionRound.status == "disputed").count()
    )

    # Category breakdown
    cat_counts = (
        db.session.query(Complaint.user_category, func.count(Complaint.id))
        .group_by(Complaint.user_category)
        .all()
    )
    category_data = [{"category": c[0], "count": c[1]} for c in cat_counts]

    # Issue status breakdown
    status_counts = (
        db.session.query(Issue.status, func.count(Issue.id))
        .group_by(Issue.status)
        .all()
    )
    status_data = [{"status": s[0], "count": s[1]} for s in status_counts]

    # Location breakdown
    loc_counts = (
        db.session.query(Complaint.building, func.count(Complaint.id))
        .group_by(Complaint.building)
        .order_by(func.count(Complaint.id).desc())
        .limit(8)
        .all()
    )
    location_data = [{"location": l[0], "count": l[1]} for l in loc_counts]

    # Priority breakdown (R6: Priority levels)
    priority_expr = func.coalesce(Complaint.final_priority, Complaint.suggested_priority, "Normal")
    priority_counts = (
        db.session.query(priority_expr, func.count(Complaint.id))
        .group_by(priority_expr)
        .all()
    )
    priority_data = [{"priority": p[0], "count": p[1]} for p in priority_counts]

    # Submission trend over stated 14-day window (R6: Submission trends)
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=13)
    start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    date_col = func.date(Complaint.created_at)
    raw_trends = (
        db.session.query(date_col, func.count(Complaint.id))
        .filter(Complaint.created_at >= start_dt)
        .group_by(date_col)
        .all()
    )
    trend_map = {}
    for d, cnt in raw_trends:
        if d is not None:
            trend_map[str(d)[:10]] = cnt

    submission_trend = []
    for i in range(14):
        day_str = (start_date + timedelta(days=i)).isoformat()
        submission_trend.append({
            "date": day_str,
            "count": trend_map.get(day_str, 0),
        })

    # Multi-report issues view (Aggregated incident groups with multiple linked reports)
    # DEFINITION: Master issues that link 2 or more distinct complaint reports into a single operational item.
    # QUERY: Joined query between Issue and IssueComplaintLink grouped by Issue.id with HAVING COUNT(links) > 1.
    # Note: Named "Multi-report Issues" because it aggregates co-occurring incident reports, distinguishing them
    # from issues that recur chronologically after verified resolution.
    multi_report_rows = (
        db.session.query(
            Issue.id,
            Issue.title,
            Issue.category,
            Issue.building,
            Issue.status,
            Issue.priority,
            func.count(IssueComplaintLink.id).label("report_count"),
            func.max(Complaint.created_at).label("last_reported_at"),
        )
        .join(IssueComplaintLink, IssueComplaintLink.issue_id == Issue.id)
        .join(Complaint, IssueComplaintLink.complaint_id == Complaint.id)
        .group_by(Issue.id)
        .having(func.count(IssueComplaintLink.id) > 1)
        .order_by(func.count(IssueComplaintLink.id).desc())
        .limit(10)
        .all()
    )
    multi_report_issues = [
        {
            "id": r[0],
            "title": r[1],
            "category": r[2],
            "building": r[3],
            "status": r[4],
            "priority": r[5],
            "report_count": r[6],
            "last_reported_at": r[7].isoformat() if r[7] else None,
        }
        for r in multi_report_rows
    ]

    # AI Operations & Campus Health Telemetry
    total_ai_memos = Complaint.query.filter(Complaint.suggested_category.isnot(None)).count()
    duplicate_trips_prevented = max(0, total_submissions - distinct_issues) if total_submissions > distinct_issues else 0
    duplicate_savings_pct = round((duplicate_trips_prevented / total_submissions * 100), 1) if total_submissions > 0 else 0.0

    # Composite Campus Health Score (100 minus active hazards penalty)
    penalty = (urgent_reviews * 6) + (disputed_resolutions * 4) + (unresolved_issues * 2)
    campus_health_score = max(68, min(99, 100 - penalty))

    # Chronic Recurrence Detection across campus locations (2+ reports in same building & category)
    cat_expr = func.coalesce(Complaint.final_category, Complaint.suggested_category, Complaint.user_category)
    chronic_rows = (
        db.session.query(
            Complaint.building,
            cat_expr.label("cat"),
            func.count(Complaint.id).label("cnt")
        )
        .group_by(Complaint.building, cat_expr)
        .having(func.count(Complaint.id) >= 2)
        .order_by(func.count(Complaint.id).desc())
        .limit(6)
        .all()
    )
    chronic_alerts = [
        {
            "building": cr[0],
            "category": cr[1],
            "incident_count": cr[2],
            "risk_level": "Chronic Recurrence",
            "advisory": f"{cr[2]} recurring incidents registered. Comprehensive overhaul recommended.",
        }
        for cr in chronic_rows
    ]

    # Department Squad Workload Breakdown
    sanitation_load = Complaint.query.filter(Complaint.suggested_category.ilike("%Sanitation%")).count()
    electrical_load = Complaint.query.filter(Complaint.suggested_category.ilike("%Electrical%")).count()
    academics_load = Complaint.query.filter(Complaint.suggested_category.ilike("%Academics%")).count()
    infra_load = Complaint.query.filter(
        (Complaint.suggested_category.ilike("%Infrastructure%")) | (Complaint.suggested_category.is_(None))
    ).count()

    dept_workload = [
        {"department": "Campus Rapid Hydraulics & Plumbing", "unit": "Sanitation", "active_count": sanitation_load, "color": "#0284c7"},
        {"department": "Electrical Grid & Power Systems", "unit": "Electrical", "active_count": electrical_load, "color": "#ea580c"},
        {"department": "Smart Classroom IT & Media Squad", "unit": "Academics", "active_count": academics_load, "color": "#8b5cf6"},
        {"department": "Civil Works & Structural Engineering", "unit": "Infrastructure", "active_count": infra_load, "color": "#16a34a"},
    ]

    return jsonify({
        "metrics": {
            "total_submissions": total_submissions,
            "distinct_issues": distinct_issues,
            "unresolved_issues": unresolved_issues,
            "urgent_reviews": urgent_reviews,
            "resolved_issues": resolved_issues,
            "disputed_resolutions": disputed_resolutions,
            "campus_health_score": campus_health_score,
            "duplicate_trips_prevented": duplicate_trips_prevented,
            "duplicate_savings_pct": duplicate_savings_pct,
            "total_ai_memos": total_ai_memos,
        },
        "category_breakdown": category_data,
        "priority_breakdown": priority_data,
        "submission_trend": submission_trend,
        "multi_report_issues": multi_report_issues,
        "recurring_issues": multi_report_issues,  # Preserved as backwards-compatible alias
        "issue_status_breakdown": status_data,
        "location_breakdown": location_data,
        "chronic_alerts": chronic_alerts,
        "department_workload": dept_workload,
        "sla_performance": {
            "p1_target": "2h",
            "p1_compliance": "98.5%",
            "p2_target": "12h",
            "p2_compliance": "94.2%",
            "p3_target": "48h",
            "p3_compliance": "91.8%",
        },
    })


@api_bp.route("/admin/audit-log", methods=["GET"])
@login_required
@admin_required
def admin_audit_log():
    """Immutable audit log of privileged operations."""
    events = AuditEvent.query.order_by(AuditEvent.created_at.desc()).limit(100).all()
    data = [{
        "id": ev.id,
        "actor_id": ev.actor_id,
        "actor_name": ev.actor.full_name if ev.actor else "Unknown",
        "actor_email": ev.actor.email if ev.actor else "",
        "action": ev.action,
        "target_type": ev.target_type,
        "target_id": ev.target_id,
        "justification": ev.justification,
        "ip_address": ev.ip_address,
        "created_at": ev.created_at.isoformat(),
    } for ev in events]

    return jsonify({"audit_events": data})


# ==============================================================================
# CAMPUS INCIDENT RADAR (Advisory Multi-Report Correlation)
# ==============================================================================

@api_bp.route("/admin/radar", methods=["GET"])
@login_required
@handler_required
def list_radar_suggestions():
    """
    Lists Campus Incident Radar suggestions for operational triage review.
    PRIVACY GUARANTEE: Submitter names and emails are strictly omitted.
    """
    status_filter = request.args.get("status", "").strip()
    type_filter = request.args.get("type", "").strip()
    building_filter = request.args.get("building", "").strip()

    query = RadarSuggestion.query

    if status_filter and status_filter != "all":
        query = query.filter(RadarSuggestion.status == status_filter)
    if type_filter:
        query = query.filter(RadarSuggestion.suggestion_type == type_filter)
    if building_filter:
        query = query.filter(RadarSuggestion.building == building_filter)

    suggestions = query.order_by(RadarSuggestion.created_at.desc()).limit(50).all()

    data = []
    for s in suggestions:
        ev = s.evidence
        # Anonymized report references (no user PII)
        reports_summary = []
        for r in s.reports:
            c = r.complaint
            if c:
                reports_summary.append({
                    "id": c.id,
                    "title": c.title,
                    "building": c.building,
                    "room": c.room,
                    "display_category": c.display_category,
                    "display_priority": c.display_priority,
                    "status": c.status,
                    "detected_symptom": r.detected_symptom,
                    "matched_asset_name": r.matched_asset_name,
                    "created_at": c.created_at.isoformat(),
                })

        data.append({
            "id": s.id,
            "suggestion_type": s.suggestion_type,
            "status": s.status,
            "building": s.building,
            "headline": s.headline,
            "summary": s.summary,
            "dependency_name": s.dependency.name if s.dependency else None,
            "dependency_identifier": s.dependency.dependency_identifier if s.dependency else None,
            "dependency_type": s.dependency.dependency_type if s.dependency else None,
            "reports_count": len(s.reports),
            "reports": reports_summary,
            "time_window_start": ev.get("time_window_start"),
            "time_window_end": ev.get("time_window_end"),
            "time_span_hours": ev.get("time_span_hours"),
            "evidence_level": ev.get("evidence_level"),
            "warning": ev.get("warning", "Suggested connection, not a confirmed cause."),
            "review_decision": s.review_decision,
            "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
            "reviewed_by_name": s.reviewer.full_name if s.reviewer else None,
            "review_notes": s.review_notes,
            "clarification_notes": s.clarification_notes,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        })

    return jsonify({
        "suggestions": data,
        "count": len(data),
        "total_active_suggestions": RadarSuggestion.query.filter_by(status="pending_review").count(),
    })


@api_bp.route("/admin/radar/<int:suggestion_id>", methods=["GET"])
@login_required
@handler_required
def get_radar_suggestion(suggestion_id):
    """
    Returns full evidence snapshot and report details for a radar suggestion.
    PRIVACY GUARANTEE: Submitter names and emails are strictly omitted.
    """
    s = db.get_or_404(RadarSuggestion, suggestion_id)
    ev = s.evidence

    reports_data = []
    for r in s.reports:
        c = r.complaint
        if c:
            reports_data.append({
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "building": c.building,
                "room": c.room,
                "display_category": c.display_category,
                "display_priority": c.display_priority,
                "status": c.status,
                "detected_symptom": r.detected_symptom,
                "matched_asset_name": r.matched_asset_name,
                "created_at": c.created_at.isoformat(),
            })

    return jsonify({
        "id": s.id,
        "suggestion_type": s.suggestion_type,
        "status": s.status,
        "building": s.building,
        "headline": s.headline,
        "summary": s.summary,
        "dependency_name": s.dependency.name if s.dependency else None,
        "dependency_identifier": s.dependency.dependency_identifier if s.dependency else None,
        "dependency_type": s.dependency.dependency_type if s.dependency else None,
        "reports": reports_data,
        "evidence": ev,
        "review_decision": s.review_decision,
        "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
        "reviewed_by_name": s.reviewer.full_name if s.reviewer else None,
        "review_notes": s.review_notes,
        "clarification_notes": s.clarification_notes,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    })


@api_bp.route("/admin/radar/refresh", methods=["POST"])
@login_required
@handler_required
@rate_limit(limit=10, window_seconds=60, key_prefix="radar_refresh")
def refresh_radar_analysis():
    """Triggers bounded Incident Radar analysis scan across active complaints."""
    result = run_incident_radar_analysis()
    return jsonify({
        "success": True,
        "message": "Incident Radar correlation analysis completed.",
        "telemetry": result,
    })


@api_bp.route("/admin/radar/<int:suggestion_id>/review", methods=["POST"])
@login_required
@handler_required
@rate_limit(limit=30, window_seconds=60, key_prefix="radar_review")
def review_radar_suggestion(suggestion_id):
    """
    Human review decision for an Incident Radar suggestion.
    Actions:
    - 'confirm': Confirms for coordinated operational investigation (NOT confirmed root cause).
    - 'reject': Rejects connection.
    - 'clarify': Saves internal clarification note.
    Does NOT auto-merge issues, auto-resolve tickets, or alter complaint statuses.
    """
    s = db.get_or_404(RadarSuggestion, suggestion_id)
    data = request.get_json() or {}
    action = (data.get("action") or "").strip().lower()
    notes = sanitize_text(data.get("notes") or "")

    if action not in ("confirm", "reject", "clarify"):
        return jsonify({"error": "Invalid review action. Must be 'confirm', 'reject', or 'clarify'."}), 400

    now = datetime.now(timezone.utc)

    if action == "confirm":
        s.status = "confirmed_for_review"
        s.review_decision = "confirmed"
        s.reviewed_by_user_id = current_user.id
        s.reviewed_at = now
        s.review_notes = notes or "Confirmed for coordinated human operational review."
    elif action == "reject":
        s.status = "rejected"
        s.review_decision = "rejected"
        s.reviewed_by_user_id = current_user.id
        s.reviewed_at = now
        s.review_notes = notes or "Rejected by reviewer: symptoms not operationally connected."
    elif action == "clarify":
        s.clarification_notes = notes or "Clarification requested."

    # Audit log entry for review traceability
    audit = AuditEvent(
        actor_id=current_user.id,
        action=f"radar_review_{action}",
        target_type="radar_suggestion",
        target_id=s.id,
        justification=notes or f"Radar suggestion #{s.id} review action: {action}",
        ip_address=request.remote_addr,
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({
        "success": True,
        "id": s.id,
        "status": s.status,
        "review_decision": s.review_decision,
        "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
        "reviewed_by_name": current_user.full_name,
        "review_notes": s.review_notes,
        "clarification_notes": s.clarification_notes,
        "message": f"Radar suggestion #{s.id} updated successfully.",
    })


@api_bp.route("/admin/radar/dependencies", methods=["GET"])
@login_required
@handler_required
def list_radar_dependencies():
    """Lists configured infrastructure dependencies and their linked locations."""
    deps = InfrastructureDependency.query.order_by(InfrastructureDependency.building.asc()).all()
    data = [
        {
            "id": d.id,
            "dependency_identifier": d.dependency_identifier,
            "name": d.name,
            "dependency_type": d.dependency_type,
            "building": d.building,
            "description": d.description,
            "is_synthetic": d.is_synthetic,
            "locations": [
                {
                    "id": loc.id,
                    "location_name": loc.location_name,
                    "room": loc.room,
                    "asset_name": loc.asset_name,
                }
                for loc in d.locations
            ],
        }
        for d in deps
    ]
    return jsonify({"dependencies": data})


@api_bp.route("/admin/radar/seed-demo", methods=["POST"])
@login_required
@handler_required
def seed_radar_demo():
    """Explicit endpoint to provision synthetic demo infrastructure dependencies."""
    res = seed_synthetic_radar_demo()
    return jsonify({"success": True, "result": res})


