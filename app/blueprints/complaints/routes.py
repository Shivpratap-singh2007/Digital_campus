import os
from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request,
    abort,
    current_app,
    send_from_directory,
)
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.complaints import complaints_bp
from app.models.complaint import Complaint, Attachment
from app.models.issue import Issue, IssueComplaintLink, StatusEvent
from app.forms import ComplaintForm, ResolutionFeedbackForm
from app.services.image import validate_and_process_image
from app.services.complaint_analysis import run_complaint_analysis
from app.services.ai_pipeline import classify_issue, detect_priority, find_duplicate_issues


@complaints_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_complaint():
    # Enforce role boundaries: Admins and handlers manage issues, they do not file student complaints
    if current_user.is_handler or current_user.is_admin or current_user.role in ("admin", "handler"):
        flash("Administrators and handlers cannot submit student complaints. Redirected to All Issues Queue.", "info")
        return redirect(url_for("admin.queue"))

    frontend_dist = os.path.abspath(os.path.join(current_app.root_path, "..", "frontend", "dist"))
    if request.method == "GET" and os.path.exists(frontend_dist):
        return send_from_directory(frontend_dist, "index.html")

    # Enforce verified email prerequisite
    if not current_user.is_verified and current_user.role == "user":
        flash(
            "Access Restricted: You must verify your college email before submitting complaints or suggestions.",
            "warning",
        )
        return redirect(url_for("auth.verification_guidance", email=current_user.email))

    form = ComplaintForm()
    if form.validate_on_submit():
        # Check idempotency token to prevent double-click duplicate creation
        existing_submission = Complaint.query.filter_by(
            idempotency_token=form.idempotency_token.data
        ).first()
        if existing_submission:
            flash("This report was already submitted. Redirecting to your report.", "info")
            return redirect(url_for("complaints.detail", complaint_id=existing_submission.id))

        # Execute Core AI Pipeline before saving to database
        full_text = f"{form.title.data.strip()}\n{form.description.data.strip()}"
        ai_category = classify_issue(full_text)
        ai_priority = detect_priority(full_text)

        # Check for duplicate candidates against active issues (> 0.70 similarity)
        active_issues = Issue.query.filter(
            Issue.status.in_(["submitted", "under_review", "in_progress"])
        ).all()
        dup_result = find_duplicate_issues(form.title.data.strip(), form.description.data.strip(), active_issues)

        # Create Complaint record with automated AI classification & priority
        complaint = Complaint(
            user_id=current_user.id,
            submission_type=form.submission_type.data,
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            user_category=form.user_category.data,
            building=form.building.data,
            room=form.room.data.strip() if form.room.data else None,
            idempotency_token=form.idempotency_token.data,
            suggested_category=ai_category,
            suggested_priority=ai_priority,
            analysis_state="completed",
            status="submitted",
        )
        db.session.add(complaint)
        db.session.flush()  # Generates complaint.id

        # If duplicate candidate detected with active issue, link automatically
        if dup_result.get("is_duplicate") and dup_result.get("matched_issue_id"):
            matched_issue = db.session.get(Issue, dup_result["matched_issue_id"])
            if matched_issue:
                link = IssueComplaintLink(
                    issue_id=matched_issue.id,
                    complaint_id=complaint.id,
                    relationship_type="same_incident",
                    linked_by_user_id=current_user.id,
                )
                db.session.add(link)
                complaint.status = matched_issue.status
                db.session.add(StatusEvent(
                    target_type="complaint",
                    target_id=complaint.id,
                    actor_id=current_user.id,
                    old_status="submitted",
                    new_status=matched_issue.status,
                    note=f"Auto-grouped with Issue #{matched_issue.id} (TF-IDF similarity: {dup_result['similarity_score']:.2f}) by AI Pipeline.",
                ))

        # Handle optional image attachment
        image_file = form.image.data
        if image_file and image_file.filename:
            valid, err_msg, meta = validate_and_process_image(image_file)
            if not valid:
                db.session.rollback()
                flash(f"Image attachment error: {err_msg}", "danger")
                return render_template("complaints/new.html", form=form)

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

        # Record initial creation status event
        status_event = StatusEvent(
            target_type="complaint",
            target_id=complaint.id,
            actor_id=current_user.id,
            old_status="none",
            new_status="submitted",
            note="Initial submission by verified user.",
        )
        db.session.add(status_event)
        
        # Save complaint before attempting AI analysis
        db.session.commit()

        # Run analysis (guarantees complaint preservation if analysis encounters any error)
        run_complaint_analysis(complaint)

        flash(
            f"Your {complaint.submission_type} has been successfully submitted! Reference ID: #{complaint.id}.",
            "success",
        )
        return redirect(url_for("complaints.detail", complaint_id=complaint.id))

    return render_template("complaints/new.html", form=form)


@complaints_bp.route("/my-complaints")
@login_required
def my_complaints():
    frontend_dist = os.path.abspath(os.path.join(current_app.root_path, "..", "frontend", "dist"))
    if os.path.exists(frontend_dist):
        return send_from_directory(frontend_dist, "index.html")

    complaints = (
        Complaint.query.filter_by(user_id=current_user.id)
        .order_by(Complaint.created_at.desc())
        .all()
    )
    return render_template("complaints/my_complaints.html", complaints=complaints)


@complaints_bp.route("/<int:complaint_id>")
@login_required
def detail(complaint_id):
    frontend_dist = os.path.abspath(os.path.join(current_app.root_path, "..", "frontend", "dist"))
    if os.path.exists(frontend_dist):
        return send_from_directory(frontend_dist, "index.html")

    complaint = db.get_or_404(Complaint, complaint_id)

    # Authorization check: only owner, handler, or admin can view complaint details
    if complaint.user_id != current_user.id and not current_user.is_handler:
        abort(403)

    # Fetch status history events
    status_events = (
        StatusEvent.query.filter_by(target_type="complaint", target_id=complaint.id)
        .order_by(StatusEvent.created_at.asc())
        .all()
    )

    # Check if linked to an issue with active or past resolution rounds
    linked_issue = complaint.issue_link.issue if complaint.issue_link else None
    feedback_form = None
    existing_feedback = None

    if linked_issue and linked_issue.status == "resolved" and linked_issue.current_resolution_round:
        round_obj = linked_issue.current_resolution_round
        feedback_form = ResolutionFeedbackForm()
        # Check if current user already submitted feedback for this round
        for fb in round_obj.feedbacks:
            if fb.user_id == current_user.id:
                existing_feedback = fb
                break

    return render_template(
        "complaints/detail.html",
        complaint=complaint,
        status_events=status_events,
        linked_issue=linked_issue,
        feedback_form=feedback_form,
        existing_feedback=existing_feedback,
    )


@complaints_bp.route("/attachment/<filename>")
@login_required
def serve_attachment(filename):
    """
    Authorized file server for attachments stored outside static/.
    Verifies that the requester is the complaint submitter, handler, or admin.
    """
    attachment = Attachment.query.filter_by(filename=filename).first_or_404()
    complaint = attachment.complaint

    # Check permission
    if complaint.user_id != current_user.id and not current_user.is_handler:
        abort(403)

    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    return send_from_directory(upload_folder, filename)
