from flask import jsonify, request, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db
from app.blueprints.api import api_bp
from app.models.complaint import Complaint
from app.models.issue import Issue
from app.models.feedback import ResolutionRound
from app.models.audit import AuditEvent
from app.services.audit import reveal_complaint_submitter


@api_bp.route("/admin/queue", methods=["GET"])
@login_required
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
def admin_reveal_identity(complaint_id):
    """
    Audited identity reveal:
    - Admin role only.
    - Requires non-empty operational purpose.
    - Commits audit event before returning identity.
    - If audit commit fails, aborts without disclosing.
    - Audit log does not store disclosed PII redundantly.
    """
    if not current_user.is_admin:
        abort(403)

    data = request.get_json() or {}
    justification = (data.get("justification") or "").strip()

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
def set_final_attributes(complaint_id):
    """Handler action to assign final category and priority."""
    if not current_user.is_handler:
        abort(403)

    complaint = Complaint.query.get_or_404(complaint_id)
    data = request.get_json() or {}

    final_cat = (data.get("final_category") or "").strip()
    final_prio = (data.get("final_priority") or "").strip()

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
def admin_dashboard():
    """Live operational metrics strictly computed from SQLite database."""
    if not current_user.is_handler:
        abort(403)

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
        "issue_status_breakdown": status_data,
        "location_breakdown": location_data,
    })


@api_bp.route("/admin/audit-log", methods=["GET"])
@login_required
def admin_audit_log():
    """Immutable audit log of privileged operations."""
    if not current_user.is_admin:
        abort(403)

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

