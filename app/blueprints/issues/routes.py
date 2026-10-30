from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.issues import issues_bp
from app.models.complaint import Complaint
from app.models.issue import Issue, IssueComplaintLink, StatusEvent
from app.models.feedback import ResolutionRound
from app.forms import CreateIssueForm, StatusUpdateForm, LinkComplaintForm
from app.services.semantic import semantic_engine


def require_handler():
    """Ensure user is handler or admin."""
    if not current_user.is_authenticated or not current_user.is_handler:
        abort(403)


@issues_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_issue():
    require_handler()
    form = CreateIssueForm()

    # Pre-fill from a seed complaint if complaint_id is in query
    seed_complaint_id = request.args.get("from_complaint", type=int)
    seed_complaint = None
    if seed_complaint_id:
        seed_complaint = Complaint.query.get(seed_complaint_id)
        if seed_complaint and request.method == "GET":
            form.title.data = f"Issue: {seed_complaint.title}"
            form.description.data = seed_complaint.description
            form.category.data = seed_complaint.display_category if seed_complaint.display_category in [c[0] for c in form.category.choices] else "Infrastructure"
            form.building.data = seed_complaint.building
            form.room.data = seed_complaint.room or ""
            form.priority.data = seed_complaint.display_priority

    if form.validate_on_submit():
        issue = Issue(
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            category=form.category.data,
            building=form.building.data,
            room=form.room.data.strip() if form.room.data else None,
            priority=form.priority.data,
            status="submitted",
            created_by_user_id=current_user.id,
        )
        db.session.add(issue)
        db.session.flush()

        # Link seed complaint if provided
        if seed_complaint:
            link = IssueComplaintLink(
                issue_id=issue.id,
                complaint_id=seed_complaint.id,
                relationship_type="same_incident",
                linked_by_user_id=current_user.id,
            )
            db.session.add(link)

            # Log link event
            status_event = StatusEvent(
                target_type="complaint",
                target_id=seed_complaint.id,
                actor_id=current_user.id,
                old_status=seed_complaint.status,
                new_status=issue.status,
                note=f"Linked to synthesized Issue #{issue.id} as primary incident report.",
            )
            db.session.add(status_event)
            seed_complaint.status = issue.status

        # Issue creation event
        issue_event = StatusEvent(
            target_type="issue",
            target_id=issue.id,
            actor_id=current_user.id,
            old_status="none",
            new_status=issue.status,
            note="Issue created by handler.",
        )
        db.session.add(issue_event)
        db.session.commit()

        flash(f"Issue #{issue.id} created successfully.", "success")
        return redirect(url_for("issues.detail", issue_id=issue.id))

    return render_template("issues/create.html", form=form, seed_complaint=seed_complaint)


@issues_bp.route("/<int:issue_id>")
@login_required
def detail(issue_id):
    require_handler()
    issue = Issue.query.get_or_404(issue_id)

    status_form = StatusUpdateForm(new_status=issue.status)
    link_form = LinkComplaintForm()

    # Get linked complaints
    linked_complaints = [link.complaint for link in issue.complaint_links]

    # Status events for this issue
    issue_status_events = (
        StatusEvent.query.filter_by(target_type="issue", target_id=issue.id)
        .order_by(StatusEvent.created_at.asc())
        .all()
    )

    # Resolution rounds and feedback statistics
    resolution_rounds = issue.resolution_rounds

    # Find related/similar unlinked complaints using semantic engine
    # Use the primary complaint embedding or create text query
    candidate_unlinked = (
        Complaint.query.filter(
            ~Complaint.id.in_([c.id for c in linked_complaints]) if linked_complaints else True
        )
        .order_by(Complaint.created_at.desc())
        .limit(25)
        .all()
    )

    seed_embedding_json = None
    if linked_complaints and linked_complaints[0].analysis_result:
        seed_embedding_json = linked_complaints[0].analysis_result.embedding_json

    suggested_matches = semantic_engine.find_related_complaints(
        current_complaint_id=linked_complaints[0].id if linked_complaints else 0,
        current_embedding_json=seed_embedding_json,
        current_building=issue.building,
        current_room=issue.room,
        candidate_complaints=candidate_unlinked,
        top_k=6,
    )

    return render_template(
        "issues/detail.html",
        issue=issue,
        linked_complaints=linked_complaints,
        status_form=status_form,
        link_form=link_form,
        issue_status_events=issue_status_events,
        resolution_rounds=resolution_rounds,
        suggested_matches=suggested_matches,
    )


@issues_bp.route("/<int:issue_id>/update-status", methods=["POST"])
@login_required
def update_status(issue_id):
    require_handler()
    issue = Issue.query.get_or_404(issue_id)
    form = StatusUpdateForm()

    if form.validate_on_submit():
        old_status = issue.status
        new_status = form.new_status.data
        note = form.note.data.strip()

        if old_status == new_status:
            flash("The selected status is identical to current status.", "info")
            return redirect(url_for("issues.detail", issue_id=issue.id))

        # Check resolution requirements
        if new_status == "resolved":
            if not note or len(note) < 5:
                flash("A detailed resolution note describing the fix is required when resolving an issue.", "danger")
                return redirect(url_for("issues.detail", issue_id=issue.id))

            # Create a new ResolutionRound
            next_round_number = len(issue.resolution_rounds) + 1
            round_obj = ResolutionRound(
                issue_id=issue.id,
                round_number=next_round_number,
                resolution_note=note,
                resolved_by_user_id=current_user.id,
                status="pending_feedback",
            )
            db.session.add(round_obj)

        elif old_status == "resolved" and new_status != "resolved":
            # Reopening an issue: close previous resolution round if not already closed
            if issue.current_resolution_round and not issue.current_resolution_round.closed_at:
                issue.current_resolution_round.closed_at = datetime.now(timezone.utc)

        # Update issue status
        issue.status = new_status
        issue_event = StatusEvent(
            target_type="issue",
            target_id=issue.id,
            actor_id=current_user.id,
            old_status=old_status,
            new_status=new_status,
            note=note,
        )
        db.session.add(issue_event)

        # Synchronize linked complaints and log status events
        for link in issue.complaint_links:
            comp = link.complaint
            comp_old_status = comp.status
            comp.status = new_status
            comp_event = StatusEvent(
                target_type="complaint",
                target_id=comp.id,
                actor_id=current_user.id,
                old_status=comp_old_status,
                new_status=new_status,
                note=f"Status synchronized with parent Issue #{issue.id}: {note}",
            )
            db.session.add(comp_event)

        db.session.commit()
        flash(f"Issue #{issue.id} status updated from '{old_status}' to '{new_status}'.", "success")
    else:
        for err in form.errors.values():
            flash(f"Update failed: {err[0]}", "danger")

    return redirect(url_for("issues.detail", issue_id=issue.id))


@issues_bp.route("/<int:issue_id>/link", methods=["POST"])
@login_required
def link_complaint(issue_id):
    require_handler()
    issue = Issue.query.get_or_404(issue_id)
    form = LinkComplaintForm()

    if form.validate_on_submit():
        complaint_id = form.complaint_id.data
        rel_type = form.relationship_type.data

        complaint = Complaint.query.get(complaint_id)
        if not complaint:
            flash(f"Complaint #{complaint_id} not found.", "danger")
            return redirect(url_for("issues.detail", issue_id=issue.id))

        if complaint.issue_link:
            flash(
                f"Complaint #{complaint_id} is already linked to Issue #{complaint.issue_link.issue_id}. "
                "Unlink it first if you wish to reassign.",
                "warning",
            )
            return redirect(url_for("issues.detail", issue_id=issue.id))

        # Create link
        link = IssueComplaintLink(
            issue_id=issue.id,
            complaint_id=complaint.id,
            relationship_type=rel_type,
            linked_by_user_id=current_user.id,
        )
        db.session.add(link)

        # Synchronize complaint status
        old_comp_status = complaint.status
        complaint.status = issue.status
        event = StatusEvent(
            target_type="complaint",
            target_id=complaint.id,
            actor_id=current_user.id,
            old_status=old_comp_status,
            new_status=issue.status,
            note=f"Linked to Issue #{issue.id} ({rel_type}).",
        )
        db.session.add(event)
        db.session.commit()

        flash(f"Complaint #{complaint.id} linked to Issue #{issue.id} as '{rel_type}'.", "success")
    else:
        flash("Invalid form data for linking complaint.", "danger")

    return redirect(url_for("issues.detail", issue_id=issue.id))


@issues_bp.route("/<int:issue_id>/unlink/<int:complaint_id>", methods=["POST"])
@login_required
def unlink_complaint(issue_id, complaint_id):
    """
    Reversible grouping: Unlinks a complaint from an issue,
    preserving the original complaint and logging the action.
    """
    require_handler()
    issue = Issue.query.get_or_404(issue_id)
    link = IssueComplaintLink.query.filter_by(issue_id=issue.id, complaint_id=complaint_id).first_or_404()

    complaint = link.complaint
    db.session.delete(link)

    # Restore complaint to 'under_review' or previous status
    old_status = complaint.status
    complaint.status = "under_review"
    event = StatusEvent(
        target_type="complaint",
        target_id=complaint.id,
        actor_id=current_user.id,
        old_status=old_status,
        new_status="under_review",
        note=f"Unlinked from Issue #{issue.id} by handler {current_user.full_name}.",
    )
    db.session.add(event)
    db.session.commit()

    flash(f"Complaint #{complaint_id} unlinked from Issue #{issue.id}. Report preserved intact.", "info")
    return redirect(url_for("issues.detail", issue_id=issue.id))
