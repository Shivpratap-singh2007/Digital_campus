from flask import redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.feedback import feedback_bp
from app.models.issue import Issue
from app.models.feedback import ResolutionFeedback
from app.forms import ResolutionFeedbackForm


@feedback_bp.route("/issue/<int:issue_id>", methods=["POST"])
@login_required
def submit_feedback(issue_id):
    """
    Records verified resolution feedback from original submitters:
    - Enforces that requester submitted a complaint linked to this issue.
    - One response per user per resolution round.
    - Re-evaluates round status (submitter_confirmed, disputed, pending_feedback).
    - Preserves all feedback history.
    """
    issue = Issue.query.get_or_404(issue_id)
    current_round = issue.current_resolution_round

    if not current_round or issue.status != "resolved":
        flash("This issue does not currently have an open resolution feedback round.", "warning")
        return redirect(url_for("complaints.my_complaints"))

    # Verify authorization: current user must be an original submitter linked to this issue
    user_complaint = None
    for link in issue.complaint_links:
        if link.complaint.user_id == current_user.id:
            user_complaint = link.complaint
            break

    if not user_complaint:
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
                complaint_id=user_complaint.id,
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

        db.session.commit()

        if new_round_status == "disputed":
            flash(
                "Notice: One or more submitters reported that the issue remains unresolved. "
                "This issue has been flagged for administrator review.",
                "warning",
            )
        elif new_round_status == "submitter_confirmed":
            flash(
                "All linked submitters have confirmed this issue is fixed! Resolution confirmed.",
                "success",
            )

        return redirect(url_for("complaints.detail", complaint_id=user_complaint.id))

    flash("Please select a valid feedback option.", "danger")
    return redirect(url_for("complaints.detail", complaint_id=user_complaint.id))
