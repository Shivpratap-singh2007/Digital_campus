from datetime import datetime, timezone
from flask import jsonify, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.api import api_bp
from app.models.issue import Issue, IssueComplaintLink, StatusEvent
from app.models.complaint import Complaint
from app.models.feedback import ResolutionRound
from app.services.semantic import semantic_engine


@api_bp.route("/issues", methods=["GET"])
def list_issues():
    """
    Returns public synthesized issue summaries.
    Conceals raw personal descriptions and submitter identities.
    """
    status_filter = request.args.get("status", "").strip()
    category_filter = request.args.get("category", "").strip()
    building_filter = request.args.get("building", "").strip()

    query = Issue.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if category_filter:
        query = query.filter_by(category=category_filter)
    if building_filter:
        query = query.filter_by(building=building_filter)

    issues = query.order_by(Issue.created_at.desc()).all()

    data = []
    for iss in issues:
        round_status = None
        if iss.current_resolution_round:
            round_status = iss.current_resolution_round.status

        data.append({
            "id": iss.id,
            "title": iss.title,
            "description": iss.description,
            "category": iss.category,
            "building": iss.building,
            "room": iss.room,
            "priority": iss.priority,
            "status": iss.status,
            "created_at": iss.created_at.isoformat(),
            "linked_reports_count": len(iss.complaint_links),
            "resolution_round_status": round_status,
        })

    return jsonify({"issues": data})


@api_bp.route("/issues", methods=["POST"])
@login_required
def create_issue():
    """Handler action: creates an operational synthesized issue."""
    if not current_user.is_handler:
        abort(403)

    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    category = data.get("category") or "Infrastructure"
    building = (data.get("building") or "").strip()
    room = (data.get("room") or "").strip() or None
    priority = data.get("priority") or "Normal"
    seed_complaint_id = data.get("seed_complaint_id")

    if not title or len(title) < 5:
        return jsonify({"error": "Issue title must be at least 5 characters."}), 400
    if not description or len(description) < 10:
        return jsonify({"error": "Synthesized description must be at least 10 characters."}), 400
    if not building:
        return jsonify({"error": "Building location is required."}), 400

    issue = Issue(
        title=title,
        description=description,
        category=category,
        building=building,
        room=room,
        priority=priority,
        status="submitted",
        created_by_user_id=current_user.id,
    )
    db.session.add(issue)
    db.session.flush()

    # Link seed complaint if provided
    if seed_complaint_id:
        seed_complaint = Complaint.query.get(seed_complaint_id)
        if seed_complaint and not seed_complaint.issue_link:
            link = IssueComplaintLink(
                issue_id=issue.id,
                complaint_id=seed_complaint.id,
                relationship_type="same_incident",
                linked_by_user_id=current_user.id,
            )
            db.session.add(link)
            seed_complaint.status = issue.status
            db.session.add(StatusEvent(
                target_type="complaint",
                target_id=seed_complaint.id,
                actor_id=current_user.id,
                old_status=seed_complaint.status,
                new_status=issue.status,
                note=f"Linked to Master Issue #{issue.id} as primary incident report.",
            ))

    db.session.add(StatusEvent(
        target_type="issue",
        target_id=issue.id,
        actor_id=current_user.id,
        old_status="none",
        new_status=issue.status,
        note="Master issue created by handler.",
    ))
    db.session.commit()

    return jsonify({"success": True, "id": issue.id, "title": issue.title}), 201


@api_bp.route("/issues/<int:issue_id>", methods=["GET"])
@login_required
def get_issue(issue_id):
    """Retrieves issue details with linked reports, status events, and AI recommendations."""
    if not current_user.is_handler:
        abort(403)

    issue = Issue.query.get_or_404(issue_id)

    # Linked complaints
    linked = []
    for link in issue.complaint_links:
        c = link.complaint
        linked.append({
            "complaint_id": c.id,
            "title": c.title,
            "submission_type": c.submission_type,
            "category": c.display_category,
            "building": c.building,
            "room": c.room,
            "priority": c.display_priority,
            "relationship_type": link.relationship_type,
            "created_at": c.created_at.isoformat(),
        })

    # Status events
    events = (
        StatusEvent.query.filter_by(target_type="issue", target_id=issue.id)
        .order_by(StatusEvent.created_at.asc())
        .all()
    )
    status_events = [{
        "id": ev.id,
        "old_status": ev.old_status,
        "new_status": ev.new_status,
        "note": ev.note,
        "actor_name": ev.actor.full_name if ev.actor else "System",
        "created_at": ev.created_at.isoformat(),
    } for ev in events]

    # Resolution rounds and feedback statistics
    rounds_data = []
    for r in issue.resolution_rounds:
        feedbacks = r.feedbacks
        fixed_cnt = sum(1 for f in feedbacks if f.response == "fixed")
        partial_cnt = sum(1 for f in feedbacks if f.response == "partially_fixed")
        not_fixed_cnt = sum(1 for f in feedbacks if f.response == "not_fixed")

        rounds_data.append({
            "round_number": r.round_number,
            "status": r.status,
            "resolution_note": r.resolution_note,
            "created_at": r.created_at.isoformat(),
            "closed_at": r.closed_at.isoformat() if r.closed_at else None,
            "resolved_by_name": r.resolved_by.full_name if r.resolved_by else "Handler",
            "aggregate_counts": {
                "fixed": fixed_cnt,
                "partially_fixed": partial_cnt,
                "not_fixed": not_fixed_cnt,
                "total_responses": len(feedbacks),
            },
        })

    # Find suggested related complaints via semantic engine
    linked_ids = [l.complaint_id for l in issue.complaint_links]
    candidates = (
        Complaint.query.filter(~Complaint.id.in_(linked_ids) if linked_ids else True)
        .order_by(Complaint.created_at.desc())
        .limit(20)
        .all()
    )

    seed_embedding_json = None
    if issue.complaint_links and issue.complaint_links[0].complaint.analysis_result:
        seed_embedding_json = issue.complaint_links[0].complaint.analysis_result.embedding_json

    matches = semantic_engine.find_related_complaints(
        current_complaint_id=linked_ids[0] if linked_ids else 0,
        current_embedding_json=seed_embedding_json,
        current_building=issue.building,
        current_room=issue.room,
        candidate_complaints=candidates,
        top_k=5,
    )

    suggested_matches = [{
        "complaint_id": m["complaint"].id,
        "title": m["complaint"].title,
        "building": m["complaint"].building,
        "room": m["complaint"].room,
        "similarity": m["similarity"],
        "match_details": m["match_details"],
        "is_possible_recurrence": m["is_possible_recurrence"],
    } for m in matches]

    return jsonify({
        "id": issue.id,
        "title": issue.title,
        "description": issue.description,
        "category": issue.category,
        "building": issue.building,
        "room": issue.room,
        "priority": issue.priority,
        "status": issue.status,
        "created_at": issue.created_at.isoformat(),
        "linked_complaints": linked,
        "status_events": status_events,
        "resolution_rounds": rounds_data,
        "suggested_matches": suggested_matches,
    })


@api_bp.route("/issues/<int:issue_id>/status", methods=["POST"])
@login_required
def update_status(issue_id):
    """Updates operational status; requires non-empty resolution note when resolving."""
    if not current_user.is_handler:
        abort(403)

    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json() or {}
    new_status = data.get("new_status")
    note = (data.get("note") or "").strip()

    valid_statuses = ("submitted", "under_review", "in_progress", "resolved")
    if new_status not in valid_statuses:
        return jsonify({"error": "Invalid operational status."}), 400

    if not note or len(note) < 5:
        return jsonify({"error": "An operational note (min 5 characters) is required for status changes."}), 400

    old_status = issue.status
    if old_status == new_status:
        return jsonify({"message": "Status is already set to this value."})

    # Resolving requires creating a new resolution round
    if new_status == "resolved":
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
        # Reopening issue
        if issue.current_resolution_round and not issue.current_resolution_round.closed_at:
            issue.current_resolution_round.closed_at = datetime.now(timezone.utc)

    issue.status = new_status
    db.session.add(StatusEvent(
        target_type="issue",
        target_id=issue.id,
        actor_id=current_user.id,
        old_status=old_status,
        new_status=new_status,
        note=note,
    ))

    # Synchronize all linked complaints
    for link in issue.complaint_links:
        c = link.complaint
        comp_old = c.status
        c.status = new_status
        db.session.add(StatusEvent(
            target_type="complaint",
            target_id=c.id,
            actor_id=current_user.id,
            old_status=comp_old,
            new_status=new_status,
            note=f"Synchronized with Issue #{issue.id}: {note}",
        ))

    db.session.commit()
    return jsonify({
        "success": True,
        "old_status": old_status,
        "new_status": new_status,
        "message": f"Status updated to '{new_status}'.",
    })


@api_bp.route("/issues/<int:issue_id>/link", methods=["POST"])
@login_required
def link_complaint(issue_id):
    """Links a complaint to this issue as same_incident or related_only."""
    if not current_user.is_handler:
        abort(403)

    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json() or {}
    complaint_id = data.get("complaint_id")
    rel_type = data.get("relationship_type") or "same_incident"

    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({"error": f"Complaint #{complaint_id} not found."}), 404

    if complaint.issue_link:
        return jsonify({
            "error": f"Complaint #{complaint_id} is already linked to Issue #{complaint.issue_link.issue_id}. Unlink it first."
        }), 400

    link = IssueComplaintLink(
        issue_id=issue.id,
        complaint_id=complaint.id,
        relationship_type=rel_type,
        linked_by_user_id=current_user.id,
    )
    db.session.add(link)

    old_status = complaint.status
    complaint.status = issue.status
    db.session.add(StatusEvent(
        target_type="complaint",
        target_id=complaint.id,
        actor_id=current_user.id,
        old_status=old_status,
        new_status=issue.status,
        note=f"Linked to Issue #{issue.id} ({rel_type}).",
    ))
    db.session.commit()

    return jsonify({"success": True, "message": f"Complaint #{complaint.id} linked to Issue #{issue.id}."})


@api_bp.route("/issues/<int:issue_id>/unlink/<int:complaint_id>", methods=["POST"])
@login_required
def unlink_complaint(issue_id, complaint_id):
    """Reversible grouping: unlinks a complaint, restoring it without data loss."""
    if not current_user.is_handler:
        abort(403)

    issue = Issue.query.get_or_404(issue_id)
    link = IssueComplaintLink.query.filter_by(issue_id=issue.id, complaint_id=complaint_id).first_or_404()

    complaint = link.complaint
    db.session.delete(link)

    old_status = complaint.status
    complaint.status = "under_review"
    db.session.add(StatusEvent(
        target_type="complaint",
        target_id=complaint.id,
        actor_id=current_user.id,
        old_status=old_status,
        new_status="under_review",
        note=f"Unlinked from Issue #{issue.id} by handler {current_user.full_name}.",
    ))
    db.session.commit()

    return jsonify({"success": True, "message": f"Complaint #{complaint_id} unlinked successfully."})

