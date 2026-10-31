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
from app.services.audit import reveal_complaint_submitter
from app.services.security import admin_required, handler_required, sanitize_text
from app.services.rate_limiter import rate_limit


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

    return jsonify({
        "metrics": {
            "total_submissions": total_submissions,
            "distinct_issues": distinct_issues,
            "unresolved_issues": unresolved_issues,
            "urgent_reviews": urgent_reviews,
            "resolved_issues": resolved_issues,
            "disputed_resolutions": disputed_resolutions,
        },
        "category_breakdown": category_data,
        "priority_breakdown": priority_data,
        "submission_trend": submission_trend,
        "multi_report_issues": multi_report_issues,
        "recurring_issues": multi_report_issues,  # Preserved as backwards-compatible alias
        "issue_status_breakdown": status_data,
        "location_breakdown": location_data,
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

