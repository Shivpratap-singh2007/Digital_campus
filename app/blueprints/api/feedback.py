import logging
from flask import jsonify, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.api import api_bp
from app.models.issue import Issue, StatusEvent
from app.models.complaint import Complaint
from app.models.feedback import ResolutionFeedback, ResolutionRound
from app.models.audit import AuditEvent
from app.services.security import sanitize_text
from app.services.rate_limiter import rate_limit

logger = logging.getLogger(__name__)


@api_bp.route("/feedback/issue/<int:issue_id>", methods=["POST"])
@login_required
@rate_limit(limit=10, window_seconds=60, key_prefix="feedback")
def submit_resolution_feedback(issue_id):
    """
    Records verified submitter feedback on a resolved issue:
    - Enforces that requester is an original submitter linked to this issue (or handler/admin).
    - One response per user per resolution round.
    - AI observations suggestion & professional feedback workflow:
        * 'fixed': Marks complaint permanently as 'resolved' in database.
        * 'partially_fixed' / 'not_fixed':
            - Automatically reverts ticket status back to 'in_progress' in database.
            - Creates high-priority notification/alert for Admin/Handler.
            - Logs feedback event in feedback.py with observations text.
    """
    issue = db.get_or_404(Issue, issue_id)
    current_round = issue.current_resolution_round

    # Check if feedback is eligible
    is_eligible = (
        issue.status == "resolved"
        or (current_round and current_round.status in ("pending_feedback", "disputed"))
    )
    if not is_eligible:
        return jsonify({"error": "This issue is not currently open for resolution feedback."}), 400

    # Find the user's linked complaint
    user_complaint = None
    for link in issue.complaint_links:
        if link.complaint and link.complaint.user_id == current_user.id:
            user_complaint = link.complaint
            break

    # If requester is handler or admin verifying on behalf of submitter
    if not user_complaint:
        if current_user.is_handler:
            user_complaint = issue.complaint_links[0].complaint if issue.complaint_links else None
        else:
            return jsonify({
                "error": "Access Denied: Only original submitters linked to this issue can submit resolution feedback."
            }), 403

    data = request.get_json() or {}
    response_val = data.get("response")
    comments_val = sanitize_text(data.get("comments") or "") or None

    valid_responses = ("fixed", "partially_fixed", "not_fixed")
    if response_val not in valid_responses:
        return jsonify({"error": f"Invalid feedback response. Choose from: {valid_responses}"}), 400

    # Ensure active resolution round exists
    if not current_round:
        current_round = ResolutionRound(
            issue_id=issue.id,
            round_number=len(issue.resolution_rounds) + 1,
            resolution_note="Issue resolved and opened for verified submitter feedback.",
            resolved_by_user_id=current_user.id,
            status="pending_feedback",
        )
        db.session.add(current_round)
        db.session.flush()

    # Check for existing response in this round (update or create)
    existing_feedback = ResolutionFeedback.query.filter_by(
        round_id=current_round.id, user_id=current_user.id
    ).first()

    if existing_feedback:
        existing_feedback.response = response_val
        existing_feedback.comments = comments_val
    else:
        fb = ResolutionFeedback(
            round_id=current_round.id,
            user_id=current_user.id,
            complaint_id=user_complaint.id if user_complaint else None,
            response=response_val,
            comments=comments_val,
        )
        db.session.add(fb)

    db.session.flush()

    # Re-evaluate round status with all unique linked submitters
    unique_submitter_ids = {
        link.complaint.user_id for link in issue.complaint_links if link.complaint
    }
    new_round_status = current_round.evaluate_status(unique_submitter_ids)
    current_round.status = new_round_status

    response_label = "Fixed" if response_val == "fixed" else (
        "Partially Fixed" if response_val == "partially_fixed" else "Not Fixed"
    )

    if response_val == "fixed":
        # 1. Permanently mark complaint as 'resolved' in campusvoice.db
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

        # Log this feedback event in feedback.py with observations text
        logger.info(
            "Verified resolution confirmation recorded: Issue #%s (Complaint #%s) confirmed 'Fixed' by User #%s (%s). Observations: %s",
            issue.id,
            user_complaint.id if user_complaint else "N/A",
            current_user.id,
            current_user.full_name,
            comments_val or "None",
        )
        message = "Resolution verified and confirmed. Ticket permanently marked as resolved."

    else:
        # 1. Automatically revert ticket status back to 'in_progress' in database
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
            note=f"Issue re-opened to In Progress: Ticket #{issue.id} marked as {response_label} by student #{current_user.id}. Re-inspection required. Observations: {comments_val or 'None'}",
        ))

        # 2. Create high-priority notification / audit alert for Admin/Handler
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

        # 3. Log this feedback event in feedback.py with observations text
        logger.warning(
            "HIGH-PRIORITY ALERT: Ticket #%s marked as %s by student #%s (%s). Re-inspection required. Observations: %s",
            issue.id,
            response_label,
            current_user.id,
            current_user.full_name,
            comments_val or "None",
        )
        message = f"Alert dispatched to facilities desk: Ticket #{issue.id} re-opened to In Progress for re-inspection."

    db.session.commit()

    return jsonify({
        "success": True,
        "round_number": current_round.round_number,
        "round_status": current_round.status,
        "ticket_status": user_complaint.status if user_complaint else issue.status,
        "issue_status": issue.status,
        "response": response_val,
        "comments": comments_val,
        "alert_created": response_val in ("partially_fixed", "not_fixed"),
        "message": message,
    })


@api_bp.route("/feedback/complaint/<int:complaint_id>", methods=["POST"])
@login_required
@rate_limit(limit=10, window_seconds=60, key_prefix="feedback_complaint")
def submit_complaint_feedback(complaint_id):
    """
    Direct resolution verification endpoint by Complaint ID.
    Routes to linked master issue if present, or executes workflow on complaint directly.
    """
    complaint = db.get_or_404(Complaint, complaint_id)
    if complaint.user_id != current_user.id and not current_user.is_handler:
        abort(403)

    if complaint.issue_link and complaint.issue_link.issue:
        return submit_resolution_feedback(complaint.issue_link.issue_id)

    data = request.get_json() or {}
    response_val = data.get("response")
    comments_val = sanitize_text(data.get("comments") or "") or None

    valid_responses = ("fixed", "partially_fixed", "not_fixed")
    if response_val not in valid_responses:
        return jsonify({"error": f"Invalid feedback response. Choose from: {valid_responses}"}), 400

    response_label = "Fixed" if response_val == "fixed" else (
        "Partially Fixed" if response_val == "partially_fixed" else "Not Fixed"
    )

    if response_val == "fixed":
        complaint.status = "resolved"
        db.session.add(StatusEvent(
            target_type="complaint",
            target_id=complaint.id,
            actor_id=current_user.id,
            old_status="resolved",
            new_status="resolved",
            note=f"Verified Resolution Confirmed: Submitter verified fix on-site. Observations: {comments_val or 'None'}",
        ))
        logger.info(
            "Verified resolution confirmation recorded: Complaint #%s confirmed 'Fixed' by User #%s (%s). Observations: %s",
            complaint.id, current_user.id, current_user.full_name, comments_val or "None"
        )
        message = "Resolution verified and confirmed. Ticket permanently marked as resolved."
    else:
        old_status = complaint.status
        complaint.status = "in_progress"
        db.session.add(StatusEvent(
            target_type="complaint",
            target_id=complaint.id,
            actor_id=current_user.id,
            old_status=old_status,
            new_status="in_progress",
            note=f"Status reverted to In Progress: Submitter verified as {response_label}. Observations: {comments_val or 'None'}",
        ))

        alert_text = f"Alert: Ticket #{complaint.id} marked as {response_label} by student. Re-inspection required."
        audit_alert = AuditEvent(
            actor_id=current_user.id,
            action="feedback_reopen_alert",
            target_type="complaint",
            target_id=complaint.id,
            justification=f"{alert_text} Submitter Observations: {comments_val or 'None'}",
            ip_address=request.remote_addr if request else None,
        )
        db.session.add(audit_alert)

        logger.warning(
            "HIGH-PRIORITY ALERT: Complaint #%s marked as %s by student #%s (%s). Re-inspection required. Observations: %s",
            complaint.id, response_label, current_user.id, current_user.full_name, comments_val or "None"
        )
        message = f"Alert dispatched to facilities desk: Ticket #{complaint.id} re-opened to In Progress for re-inspection."

    db.session.commit()

    return jsonify({
        "success": True,
        "round_number": 1,
        "round_status": "submitter_confirmed" if response_val == "fixed" else "disputed",
        "ticket_status": complaint.status,
        "response": response_val,
        "comments": comments_val,
        "alert_created": response_val in ("partially_fixed", "not_fixed"),
        "message": message,
    })
