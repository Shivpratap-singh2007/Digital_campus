import logging
from flask import redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.feedback import feedback_bp
from app.models.issue import Issue, StatusEvent
from app.models.feedback import ResolutionFeedback
from app.models.audit import AuditEvent
from app.forms import ResolutionFeedbackForm

logger = logging.getLogger(__name__)


@feedback_bp.route("/issue/<int:issue_id>", methods=["POST"])
@login_required
def submit_feedback(issue_id):
    """
    Records verified resolution feedback from original submitters:
    - Enforces that requester submitted a complaint linked to this issue.
    - One response per user per resolution round.
    - Re-evaluates round status (submitter_confirmed, disputed, pending_feedback).
    - If fixed: Marks complaint as permanently resolved.
    - If partially_fixed or not_fixed:
        * Reverts ticket status back to in_progress in database.
        * Dispatches high-priority notification/alert for Admin/Handler.
        * Logs feedback event with observations text.
    """
    issue = db.get_or_404(Issue, issue_id)
    current_round = issue.current_resolution_round

    if not current_round or issue.status != "resolved":
        flash("This issue does not currently have an open resolution feedback round.", "warning")
        return redirect(url_for("complaints.my_complaints"))

    # Verify authorization: current user must be an original submitter linked to this issue
    user_complaint = None
    for link in issue.complaint_links:
        if link.complaint and link.complaint.user_id == current_user.id:
            user_complaint = link.complaint
            break

    if not user_complaint:
        if current_user.is_handler:
            user_complaint = issue.complaint_links[0].complaint if issue.complaint_links else None
        else:
            flash("Access Denied: Only original submitters linked to this issue can submit resolution feedback.", "danger")
            abort(403)

    form = ResolutionFeedbackForm()
    if form.validate_on_submit():
        response_val = form.response.data
        comments_val = form.comments.data.strip() if form.comments.data else None

        # Check for existing response in this round (one response per user per round)
        existing_feedback = ResolutionFeedback.query.filter_by(
            round_id=current_round.id, user_id=current_user.id
        ).first()

        if existing_feedback:
            existing_feedback.response = response_val
            existing_feedback.comments = comments_val
            flash("Your resolution feedback for this round has been updated.", "info")
        else:
            fb = ResolutionFeedback(
                round_id=current_round.id,
                user_id=current_user.id,
                complaint_id=user_complaint.id if user_complaint else None,
                response=response_val,
                comments=comments_val,
            )
            db.session.add(fb)
            flash("Thank you! Your verified resolution feedback has been recorded.", "success")

        db.session.flush()

        # Re-evaluate round status based on all unique linked submitters
        unique_submitter_ids = {
            link.complaint.user_id for link in issue.complaint_links if link.complaint
        }
        new_round_status = current_round.evaluate_status(unique_submitter_ids)
        current_round.status = new_round_status

        response_label = "Fixed" if response_val == "fixed" else (
            "Partially Fixed" if response_val == "partially_fixed" else "Not Fixed"
        )

        if response_val == "fixed":
            if user_complaint:
                user_complaint.status = "resolved"
                db.session.add(StatusEvent(
                    target_type="complaint",
                    target_id=user_complaint.id,
                    actor_id=current_user.id,
                    old_status=user_complaint.status,
                    new_status="resolved",
                    note=f"Verified Resolution Confirmed: Submitter verified fix on-site. Observations: {comments_val or 'None'}",
                ))
            if new_round_status == "submitter_confirmed":
                issue.status = "resolved"
                db.session.add(StatusEvent(
                    target_type="issue",
                    target_id=issue.id,
                    actor_id=current_user.id,
                    old_status="resolved",
                    new_status="resolved",
                    note=f"All linked submitters confirmed fix. Issue permanently resolved. Submitter observations: {comments_val or 'None'}",
                ))
            logger.info(
                "Verified resolution confirmation recorded: Issue #%s confirmed 'Fixed' by User #%s. Observations: %s",
                issue.id, current_user.id, comments_val or "None"
            )
        else:
            # Revert ticket status back to in_progress
            if user_complaint:
                old_comp_status = user_complaint.status
                user_complaint.status = "in_progress"
                db.session.add(StatusEvent(
                    target_type="complaint",
                    target_id=user_complaint.id,
                    actor_id=current_user.id,
                    old_status=old_comp_status,
                    new_status="in_progress",
                    note=f"Status reverted to In Progress: Submitter verified as {response_label}. Observations: {comments_val or 'None'}",
                ))

            old_issue_status = issue.status
            issue.status = "in_progress"
            current_round.status = "disputed"

            db.session.add(StatusEvent(
                target_type="issue",
                target_id=issue.id,
                actor_id=current_user.id,
                old_status=old_issue_status,
                new_status="in_progress",
                note=f"Issue re-opened to In Progress: Ticket #{issue.id} marked as {response_label} by student. Re-inspection required. Observations: {comments_val or 'None'}",
            ))

            # High-priority alert
            alert_text = f"Alert: Ticket #{issue.id} marked as {response_label} by student. Re-inspection required."
            audit_alert = AuditEvent(
                actor_id=current_user.id,
                action="feedback_reopen_alert",
                target_type="issue",
                target_id=issue.id,
                justification=f"{alert_text} Submitter Observations: {comments_val or 'None'}",
                ip_address=request.remote_addr if request else None,
            )
            db.session.add(audit_alert)

            logger.warning(
                "HIGH-PRIORITY ALERT: Ticket #%s marked as %s by student #%s. Re-inspection required. Observations: %s",
                issue.id, response_label, current_user.id, comments_val or "None"
            )

        db.session.commit()

        if new_round_status == "disputed":
            flash(
                f"Alert: Ticket re-opened to In Progress. Submitter verified as {response_label}. Facilities desk alerted for re-inspection.",
                "warning",
            )
        elif new_round_status == "submitter_confirmed":
            flash(
                "All linked submitters have confirmed this issue is fixed! Resolution permanently confirmed.",
                "success",
            )

        redirect_target = user_complaint.id if user_complaint else issue.id
        return redirect(url_for("complaints.detail", complaint_id=redirect_target))

    flash("Please select a valid feedback option.", "danger")
    redirect_target = user_complaint.id if user_complaint else issue.id
    return redirect(url_for("complaints.detail", complaint_id=redirect_target))
