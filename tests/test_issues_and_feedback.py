from app.models import Issue, Complaint, IssueComplaintLink, ResolutionRound, User
from app.extensions import db


def test_issue_creation_and_reversible_grouping(client, handler_user, verified_user, app):
    """Test handler can create issue, link complaint, and unlink (reversible grouping)."""
    client.post(
        "/api/auth/login",
        json={"email": handler_user.email, "password": "HandlerPass123!"},
    )

    # Create a test complaint
    comp = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Elevator door jammed",
        description="Lift jammed on 2nd floor in library.",
        user_category="Infrastructure",
        building="Central Library",
        idempotency_token="elem-1",
        status="submitted",
    )
    db.session.add(comp)
    db.session.commit()

    # Create an issue
    res = client.post(
        "/api/issues",
        json={
            "title": "Central Library Elevator Jammed",
            "description": "Technician dispatched to reset elevator hoist motor.",
            "category": "Infrastructure",
            "building": "Central Library",
            "priority": "High",
            "seed_complaint_id": comp.id,
        },
    )
    assert res.status_code == 201
    issue_id = res.get_json()["id"]

    issue = Issue.query.get(issue_id)
    assert len(issue.complaint_links) == 1
    assert comp.status == "submitted"

    # Unlink complaint (reversible grouping)
    unlink_res = client.post(f"/api/issues/{issue_id}/unlink/{comp.id}")
    assert unlink_res.status_code == 200

    # Complaint is preserved intact
    assert Complaint.query.get(comp.id) is not None
    assert IssueComplaintLink.query.filter_by(issue_id=issue_id, complaint_id=comp.id).first() is None


def test_verified_resolution_feedback_rules(client, handler_user, verified_user, app):
    """Test resolution feedback: only linked submitters can vote, round statuses evaluated strictly."""
    # 1. Setup issue and linked complaint
    comp = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Fan regulator broken",
        description="Fan regulator switch broken in classroom.",
        user_category="Infrastructure",
        building="Academic Block A",
        idempotency_token="fan-1",
        status="under_review",
    )
    db.session.add(comp)
    db.session.commit()

    issue = Issue(
        title="Academic Block A Fan Regulators",
        description="Replaced rotary switches in classroom.",
        category="Infrastructure",
        building="Academic Block A",
        status="under_review",
        created_by_user_id=handler_user.id,
    )
    db.session.add(issue)
    db.session.flush()

    link = IssueComplaintLink(
        issue_id=issue.id,
        complaint_id=comp.id,
        relationship_type="same_incident",
        linked_by_user_id=handler_user.id,
    )
    db.session.add(link)
    db.session.commit()

    # 2. Handler marks issue Resolved (requires note)
    client.post(
        "/api/auth/login",
        json={"email": handler_user.email, "password": "HandlerPass123!"},
    )
    res_status = client.post(
        f"/api/issues/{issue.id}/status",
        json={"new_status": "resolved", "note": "Replaced switch mechanism and tested speed steps."},
    )
    assert res_status.status_code == 200

    issue = Issue.query.get(issue.id)
    assert issue.status == "resolved"
    round1 = issue.current_resolution_round
    assert round1 is not None
    assert round1.status == "pending_feedback"

    # 3. Unauthorized user cannot submit feedback
    other_user = User(
        email="other.student@campus.edu",
        full_name="Other Student",
        role="user",
        is_verified=True,
    )
    other_user.set_password("Pass12345!")
    db.session.add(other_user)
    db.session.commit()

    client.post(
        "/api/auth/login",
        json={"email": other_user.email, "password": "Pass12345!"},
    )
    unauth_fb = client.post(
        f"/api/feedback/issue/{issue.id}",
        json={"response": "fixed"},
    )
    assert unauth_fb.status_code == 403

    # 4. Verified original submitter submits "partially_fixed" -> round marks disputed
    client.post(
        "/api/auth/login",
        json={"email": verified_user.email, "password": "StudentPass123!"},
    )
    fb_res1 = client.post(
        f"/api/feedback/issue/{issue.id}",
        json={"response": "partially_fixed", "comments": "Fan works on high only, switch knob is loose."},
    )
    assert fb_res1.status_code == 200
    assert fb_res1.get_json()["round_status"] == "disputed"

    # 5. Verified submitter updates response to "fixed" -> round marks submitter_confirmed
    fb_res2 = client.post(
        f"/api/feedback/issue/{issue.id}",
        json={"response": "fixed", "comments": "Technician returned and tightened knob, fully working now."},
    )
    assert fb_res2.status_code == 200
    assert fb_res2.get_json()["round_status"] == "submitter_confirmed"

