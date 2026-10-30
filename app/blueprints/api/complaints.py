import os
import uuid
from flask import jsonify, request, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db
from app.blueprints.api import api_bp
from app.models.complaint import Complaint, Attachment, AnalysisResult
from app.models.issue import StatusEvent
from app.services.image import validate_and_process_image
from app.services.complaint_analysis import run_complaint_analysis
from app.services.rate_limiter import rate_limit
from app.services.security import sanitize_text, verified_user_required, handler_required


@api_bp.route("/complaints", methods=["GET"])
@login_required
def list_complaints():
    """Lists current user's complaints."""
    complaints = (
        Complaint.query.filter_by(user_id=current_user.id)
        .order_by(Complaint.created_at.desc())
        .all()
    )

    data = []
    for c in complaints:
        data.append({
            "id": c.id,
            "submission_type": c.submission_type,
            "title": c.title,
            "user_category": c.user_category,
            "display_category": c.display_category,
            "building": c.building,
            "room": c.room,
            "priority": c.display_priority,
            "status": c.status,
            "analysis_state": c.analysis_state,
            "created_at": c.created_at.isoformat(),
            "has_attachment": len(c.attachments) > 0,
            "linked_issue_id": c.issue_link.issue_id if c.issue_link else None,
            "linked_issue_status": c.issue_link.issue.status if c.issue_link and c.issue_link.issue else None,
        })

    return jsonify({"complaints": data})


@api_bp.route("/complaints", methods=["POST"])
@login_required
@verified_user_required
@rate_limit(limit=15, window_seconds=60, key_prefix="complaint")
def create_complaint():
    """
    Submits a complaint or suggestion:
    - Enforces verified email status.
    - Idempotency key prevents double submissions; returns existing result on repeat identical key.
    - Rejects reused key with changed content.
    - Validates inputs and optional image using Pillow.
    - Commits complaint with analysis_state='pending' before analysis.
    """
    # Support multipart/form-data or JSON
    if request.is_json:
        payload = request.get_json() or {}
        image_file = None
    else:
        payload = request.form
        image_file = request.files.get("image")

    title = sanitize_text(payload.get("title") or "")
    description = sanitize_text(payload.get("description") or "")
    submission_type = payload.get("submission_type") or "complaint"
    user_category = sanitize_text(payload.get("user_category") or "Not sure")
    building = sanitize_text(payload.get("building") or "")
    room = sanitize_text(payload.get("room") or "") or None
    submission_key = (payload.get("submission_key") or payload.get("idempotency_token") or "").strip()

    if not submission_key:
        submission_key = uuid.uuid4().hex

    # Check for existing submission key
    existing = Complaint.query.filter_by(idempotency_token=submission_key).first()
    if existing:
        # Check if content matches or was altered
        if existing.title == title and existing.description == description:
            return jsonify({
                "id": existing.id,
                "message": "Duplicate submission detected. Returning existing complaint record.",
                "analysis_state": existing.analysis_state,
                "status": existing.status,
            }), 200
        else:
            return jsonify({
                "error": "Idempotency conflict: submission key already used with different content."
            }), 409

    # Validations
    if not title or len(title) < 5 or len(title) > 200:
        return jsonify({"error": "Title must be between 5 and 200 characters."}), 400

    if not description or len(description) < 10 or len(description) > 4000:
        return jsonify({"error": "Description must be between 10 and 4000 characters."}), 400

    if submission_type not in ("complaint", "suggestion"):
        return jsonify({"error": "Invalid submission type."}), 400

    if not building:
        return jsonify({"error": "Campus building/location is required."}), 400

    # Save Complaint with analysis_state='pending'
    complaint = Complaint(
        user_id=current_user.id,
        submission_type=submission_type,
        title=title,
        description=description,
        user_category=user_category,
        building=building,
        room=room,
        idempotency_token=submission_key,
        analysis_state="pending",
        status="submitted",
    )
    db.session.add(complaint)
    db.session.flush()

    # Process image if provided
    if image_file and image_file.filename:
        valid, err_msg, meta = validate_and_process_image(image_file)
        if not valid:
            db.session.rollback()
            return jsonify({"error": f"Image validation failed: {err_msg}"}), 400

        attachment = Attachment(
            complaint_id=complaint.id,
            filename=meta["filename"],
            original_filename=meta["original_filename"],
            mime_type=meta["mime_type"],
            file_size=meta["file_size"],
            width=meta["width"],
            height=meta["height"],
        )
        db.session.add(attachment)

    # Log initial creation event
    status_event = StatusEvent(
        target_type="complaint",
        target_id=complaint.id,
        actor_id=current_user.id,
        old_status="none",
        new_status="submitted",
        note="Initial verified user submission.",
    )
    db.session.add(status_event)
    db.session.commit()

    return jsonify({
        "success": True,
        "id": complaint.id,
        "title": complaint.title,
        "status": complaint.status,
        "analysis_state": complaint.analysis_state,
        "message": f"{complaint.submission_type.capitalize()} submitted successfully.",
    }), 201


@api_bp.route("/complaints/<int:complaint_id>/analyze", methods=["POST"])
@login_required
def trigger_analysis(complaint_id):
    """Executes AI and rule analysis on a saved complaint."""
    complaint = Complaint.query.get_or_404(complaint_id)
    if complaint.user_id != current_user.id and not current_user.is_handler:
        abort(403)

    success = run_complaint_analysis(complaint)
    return jsonify({
        "success": success,
        "analysis_state": complaint.analysis_state,
        "suggested_category": complaint.suggested_category,
        "suggested_priority": complaint.suggested_priority,
    })


@api_bp.route("/complaints/<int:complaint_id>", methods=["GET"])
@login_required
def get_complaint(complaint_id):
    """Retrieves full details for a complaint with status events and analysis metadata."""
    complaint = Complaint.query.get_or_404(complaint_id)
    if complaint.user_id != current_user.id and not current_user.is_handler:
        abort(403)

    # Attachments
    attachments = [{
        "filename": att.filename,
        "original_filename": att.original_filename,
        "file_size": att.file_size,
        "mime_type": att.mime_type,
        "url": f"/api/complaints/attachment/{att.filename}",
    } for att in complaint.attachments]

    # Analysis result
    ar = complaint.analysis_result
    analysis_data = None
    if ar:
        analysis_data = {
            "model_identifier": ar.model_identifier,
            "analysis_version": ar.analysis_version,
            "suggested_category": ar.suggested_category,
            "category_similarity": ar.category_similarity,
            "category_reason": ar.category_reason,
            "suggested_priority": ar.suggested_priority,
            "priority_reason": ar.priority_reason,
            "matched_phrase": ar.matched_phrase,
            "is_ambiguous": ar.is_ambiguous,
            "is_semantic_available": ar.is_semantic_available,
        }

    # Status events
    events = (
        StatusEvent.query.filter_by(target_type="complaint", target_id=complaint.id)
        .order_by(StatusEvent.created_at.asc())
        .all()
    )
    event_data = [{
        "id": ev.id,
        "old_status": ev.old_status,
        "new_status": ev.new_status,
        "note": ev.note,
        "created_at": ev.created_at.isoformat(),
    } for ev in events]

    # Linked issue info
    issue_info = None
    if complaint.issue_link and complaint.issue_link.issue:
        iss = complaint.issue_link.issue
        current_round = iss.current_resolution_round
        
        # User feedback for this round if any
        user_feedback = None
        if current_round:
            for fb in current_round.feedbacks:
                if fb.user_id == current_user.id:
                    user_feedback = {
                        "response": fb.response,
                        "comments": fb.comments,
                        "created_at": fb.created_at.isoformat(),
                    }
                    break

        issue_info = {
            "id": iss.id,
            "title": iss.title,
            "status": iss.status,
            "priority": iss.priority,
            "relationship_type": complaint.issue_link.relationship_type,
            "current_round": {
                "round_number": current_round.round_number,
                "status": current_round.status,
                "resolution_note": current_round.resolution_note,
            } if current_round else None,
            "user_feedback": user_feedback,
        }

    return jsonify({
        "id": complaint.id,
        "submission_type": complaint.submission_type,
        "title": complaint.title,
        "description": complaint.description,
        "user_category": complaint.user_category,
        "suggested_category": complaint.suggested_category,
        "final_category": complaint.final_category,
        "display_category": complaint.display_category,
        "building": complaint.building,
        "room": complaint.room,
        "suggested_priority": complaint.suggested_priority,
        "final_priority": complaint.final_priority,
        "display_priority": complaint.display_priority,
        "status": complaint.status,
        "analysis_state": complaint.analysis_state,
        "created_at": complaint.created_at.isoformat(),
        "attachments": attachments,
        "analysis": analysis_data,
        "status_events": event_data,
        "linked_issue": issue_info,
    })


@api_bp.route("/complaints/attachment/<filename>", methods=["GET"])
@login_required
def serve_attachment(filename):
    """Secure, authorized file server for attachments."""
    safe_filename = secure_filename(os.path.basename(filename))
    attachment = Attachment.query.filter_by(filename=safe_filename).first_or_404()
    complaint = attachment.complaint

    if complaint.user_id != current_user.id and not current_user.is_handler:
        abort(403)

    return send_from_directory(current_app.config["UPLOAD_FOLDER"], safe_filename)


@api_bp.route("/complaints/<int:complaint_id>/retry-analysis", methods=["POST"])
@login_required
@handler_required
def retry_analysis(complaint_id):
    """Handler action to re-run AI and rule analysis."""
    complaint = Complaint.query.get_or_404(complaint_id)
    success = run_complaint_analysis(complaint)
    return jsonify({
        "success": success,
        "analysis_state": complaint.analysis_state,
        "suggested_category": complaint.suggested_category,
        "suggested_priority": complaint.suggested_priority,
    })

