from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db
from app.blueprints.admin import admin_bp
from app.models.complaint import Complaint
from app.models.issue import Issue, IssueComplaintLink, StatusEvent
from app.models.feedback import ResolutionRound
from app.models.audit import AuditEvent
from app.forms import IdentityRevealForm
from app.services.audit import reveal_complaint_submitter
from app.services.complaint_analysis import run_complaint_analysis


def require_handler():
    if not current_user.is_authenticated or not current_user.is_handler:
        abort(403)


def require_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


@admin_bp.route("/queue")
@login_required
def queue():
    require_handler()

    # Query filter parameters
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

    # Filter options
    categories = ["Infrastructure", "Sanitation", "Academics", "Student services", "IT/connectivity", "Other", "Not sure"]
    from flask import current_app
    locations = current_app.config.get("CAMPUS_LOCATIONS", [])
    statuses = ["submitted", "under_review", "in_progress", "resolved"]
    priorities = ["Urgent review", "High", "Normal", "Low"]

    reveal_form = IdentityRevealForm()

    return render_template(
        "admin/queue.html",
        complaints=complaints,
        categories=categories,
        locations=locations,
        statuses=statuses,
        priorities=priorities,
        selected_category=category,
        selected_building=building,
        selected_status=status,
        selected_priority=priority,
        reveal_form=reveal_form,
    )


@admin_bp.route("/complaint/<int:complaint_id>/reveal-identity", methods=["POST"])
@login_required
def reveal_identity(complaint_id):
    """
    Identity reveal:
    - POST action with CSRF protection.
    - Check explicit permission (admin role only).
    - Requires non-empty operational purpose.
    - Commits audit event before returning identity.
    - If audit fails, identity is NOT revealed.
    """
    require_admin()
    form = IdentityRevealForm()

    if form.validate_on_submit():
        success, message, disclosed_info = reveal_complaint_submitter(
            admin_user=current_user,
            complaint_id=complaint_id,
            justification=form.justification.data,
        )

        if success and disclosed_info:
            flash(
                f"Disclosed Submitter Info: Name: {disclosed_info['full_name']} | "
                f"Email: {disclosed_info['email']} | User ID: #{disclosed_info['user_id']} | "
                f"Logged under Audit Event #{disclosed_info['audit_id']}.",
                "warning",
            )
        else:
            flash(f"Identity Reveal Rejected: {message}", "danger")
    else:
        for err in form.errors.values():
            flash(f"Identity Reveal Rejected: {err[0]}", "danger")

    return redirect(request.referrer or url_for("admin.queue"))


@admin_bp.route("/complaint/<int:complaint_id>/retry-analysis", methods=["POST"])
@login_required
def retry_analysis(complaint_id):
    require_handler()
    complaint = Complaint.query.get_or_404(complaint_id)
    success = run_complaint_analysis(complaint)

    if success:
        flash(f"Analysis successfully re-executed for Complaint #{complaint.id}.", "success")
    else:
        flash(f"Analysis retry for Complaint #{complaint.id} flagged needs_review.", "warning")

    return redirect(request.referrer or url_for("admin.queue"))


@admin_bp.route("/complaint/<int:complaint_id>/set-final-attributes", methods=["POST"])
@login_required
def set_final_attributes(complaint_id):
    require_handler()
    complaint = Complaint.query.get_or_404(complaint_id)

    final_cat = request.form.get("final_category", "").strip()
    final_prio = request.form.get("final_priority", "").strip()

    if final_cat:
        complaint.final_category = final_cat
    if final_prio:
        complaint.final_priority = final_prio

    # Handler manual override resolves analysis state
    complaint.analysis_state = "completed"
    db.session.commit()

    flash(f"Operational attributes updated for Complaint #{complaint.id}.", "success")
    return redirect(request.referrer or url_for("admin.queue"))


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    require_handler()

    # Exact metrics strictly computed from database
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

    # Breakdown by category for complaints
    cat_counts = (
        db.session.query(Complaint.user_category, func.count(Complaint.id))
        .group_by(Complaint.user_category)
        .all()
    )

    # Breakdown by status for issues
    issue_status_counts = (
        db.session.query(Issue.status, func.count(Issue.id))
        .group_by(Issue.status)
        .all()
    )

    # Breakdown by location for complaints
    loc_counts = (
        db.session.query(Complaint.building, func.count(Complaint.id))
        .group_by(Complaint.building)
        .order_by(func.count(Complaint.id).desc())
        .limit(8)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        total_submissions=total_submissions,
        distinct_issues=distinct_issues,
        unresolved_issues=unresolved_issues,
        urgent_reviews=urgent_reviews,
        resolved_issues=resolved_issues,
        disputed_resolutions=disputed_resolutions,
        cat_counts=cat_counts,
        issue_status_counts=issue_status_counts,
        loc_counts=loc_counts,
    )


@admin_bp.route("/audit-log")
@login_required
def audit_log():
    require_admin()
    events = AuditEvent.query.order_by(AuditEvent.created_at.desc()).limit(100).all()
    return render_template("admin/audit_log.html", events=events)
