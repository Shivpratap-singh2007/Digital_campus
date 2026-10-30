from flask import jsonify, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.api import api_bp
from app.models.issue import Issue
from app.models.feedback import ResolutionFeedback
from app.services.security import sanitize_text
from app.services.rate_limiter import rate_limit


@api_bp.route("/feedback/issue/<int:issue_id>", methods=["POST"])
@login_required
@rate_limit(limit=10, window_seconds=60, key_prefix="feedback")
def submit_resolution_feedback(issue_id):
    """
    Records verified submitter feedback on a resolved issue:
    - Enforces that requester is an original submitter linked to this issue.
    - One response per user per resolution round.
    - Re-evaluates round status:
        * Any 'partially_fixed' or 'not_fixed' -> 'disputed'.
        * ALL linked unique submitters must respond 'fixed' -> 'submitter_confirmed'.
        * Missing responses NEVER count as fixed.
    """
    issue = Issue.query.get_or_404(issue_id)
    current_round = issue.current_resolution_round

    if not current_round or issue.status != "resolved":
        return jsonify({"error": "This issue is not currently open for resolution feedback."}), 400

    # Find the user's linked complaint
    user_complaint = None
    for link in issue.complaint_links:
        if link.complaint.user_id == current_user.id:
            user_complaint = link.complaint
            break

    if not user_complaint:
        return jsonify({
            "error": "Access Denied: Only original submitters linked to this issue can submit resolution feedback."
        }), 403

    data = request.get_json() or {}
    response_val = data.get("response")
    comments_val = sanitize_text(data.get("comments") or "") or None

    valid_responses = ("fixed", "partially_fixed", "not_fixed")
    if response_val not in valid_responses:
        return jsonify({"error": f"Invalid feedback response. Choose from: {valid_responses}"}), 400

    # Check for existing response in this round
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
            complaint_id=user_complaint.id,
            response=response_val,
            comments=comments_val,
        )
        db.session.add(fb)

    db.session.flush()

    # Re-evaluate round status with all unique linked submitters
    unique_submitter_ids = {
        link.complaint.user_id for link in issue.complaint_links if link.complaint
    }
    new_status = current_round.evaluate_status(unique_submitter_ids)
    current_round.status = new_status
    db.session.commit()

    return jsonify({
        "success": True,
        "round_number": current_round.round_number,
        "round_status": current_round.status,
        "response": response_val,
        "message": "Resolution feedback recorded successfully.",
    })

