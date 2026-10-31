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

    issue = db.session.get(Issue, issue_id)
    assert len(issue.complaint_links) == 1
    assert comp.status == "submitted"

    # Unlink complaint (reversible grouping)
    unlink_res = client.post(f"/api/issues/{issue_id}/unlink/{comp.id}")
    assert unlink_res.status_code == 200

    # Complaint is preserved intact
    assert db.session.get(Complaint, comp.id) is not None
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

    issue = db.session.get(Issue, issue.id)
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


def test_feedback_reopen_workflow_and_alerts(client, handler_user, verified_user, app):
    """Test feedback reopen: not_fixed reverts to in_progress, logs high-priority alert; fixed resolves permanently."""
    # 1. Create complaint and issue
    comp = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Restroom flush leaking continuously",
        description="Water valve broken in 2nd floor restroom.",
        user_category="Sanitation & Plumbing",
        building="Academic Block B",
        idempotency_token="flush-leak-1",
        status="resolved",
    )
    db.session.add(comp)
    db.session.flush()

    issue = Issue(
        title="Academic Block B Restroom Plumbing",
        description="Replaced flush valve assembly.",
        category="Sanitation & Plumbing",
        building="Academic Block B",
        status="resolved",
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

    round_obj = ResolutionRound(
        issue_id=issue.id,
        round_number=1,
        resolution_note="Valve replaced and tested on-site.",
        resolved_by_user_id=handler_user.id,
        status="pending_feedback",
    )
    db.session.add(round_obj)
    db.session.commit()

    # 2. Login as verified student and submit "not_fixed" with observations
    client.post(
        "/api/auth/login",
        json={"email": verified_user.email, "password": "StudentPass123!"},
    )

    obs_text = "Inspected the site. The malfunction remains completely unresolved and continues to cause disruption."
    res = client.post(
        f"/api/feedback/issue/{issue.id}",
        json={"response": "not_fixed", "comments": obs_text},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["ticket_status"] == "in_progress"
    assert data["alert_created"] is True

    # Check database: complaint and issue status must be reverted to in_progress
    db.session.expire_all()
    comp_refreshed = db.session.get(Complaint, comp.id)
    issue_refreshed = db.session.get(Issue, issue.id)
    assert comp_refreshed.status == "in_progress"
    assert issue_refreshed.status == "in_progress"

    # Check audit event alert logged
    from app.models.audit import AuditEvent
    alert = AuditEvent.query.filter_by(
        action="feedback_reopen_alert", target_id=issue.id
    ).first()
    assert alert is not None
    assert "Not Fixed" in alert.justification
    assert obs_text in alert.justification

    # 3. Technician repairs and student confirms "fixed"
    fixed_obs = "Verified on-site. The issue has been completely resolved and functioning properly. Thank you."
    res_fixed = client.post(
        f"/api/feedback/issue/{issue.id}",
        json={"response": "fixed", "comments": fixed_obs},
    )
    assert res_fixed.status_code == 200
    assert res_fixed.get_json()["ticket_status"] == "resolved"

    db.session.expire_all()
    assert db.session.get(Complaint, comp.id).status == "resolved"
    assert db.session.get(Issue, issue.id).status == "resolved"


def test_issue_upvote_and_duplicate_check(client, handler_user, verified_user, app):
    """Test duplicate check endpoint and issue upvoting workflow."""
    # 1. Create an active issue
    issue = Issue(
        title="Boys Hostel 1 Mess Water Cooler Compressor Failure",
        description="Drinking water cooler in mess is not cooling.",
        category="Sanitation & Plumbing",
        building="Hostel Block 1 / Mess",
        status="in_progress",
        priority="Medium (P2)",
        upvotes=12,
        created_by_user_id=handler_user.id,
    )
    db.session.add(issue)
    db.session.commit()

    # Login as student
    client.post(
        "/api/auth/login",
        json={"email": verified_user.email, "password": "StudentPass123!"},
    )

    # 2. Check duplicate with matching keywords
    dup_res = client.post(
        "/api/issues/check-duplicate",
        json={"title": "Water cooler in hostel mess not chilling", "description": "Paani thanda nahi hai"},
    )
    assert dup_res.status_code == 200
    dup_data = dup_res.get_json()
    assert dup_data["has_duplicate"] is True
    assert dup_data["matched_issue"]["id"] == issue.id
    assert dup_data["matched_issue"]["upvotes"] == 12

    # 3. Upvote the issue instead of filing duplicate
    up_res = client.post(f"/api/issues/{issue.id}/upvote")
    assert up_res.status_code == 200
    assert up_res.get_json()["upvotes"] == 13

    # Check database
    db.session.expire_all()
    assert db.session.get(Issue, issue.id).upvotes == 13



