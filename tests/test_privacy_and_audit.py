from app.models import Complaint, AuditEvent
from app.extensions import db


def test_ordinary_queue_omits_submitter_identity(client, handler_user, verified_user, app):
    """Test ordinary queue responses mask submitter names and emails."""
    comp = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Restroom tap dripping",
        description="Continuous water dripping in 1st floor restroom.",
        user_category="Sanitation",
        building="Academic Block A",
        idempotency_token="tap-1",
        status="submitted",
    )
    db.session.add(comp)
    db.session.commit()

    client.post(
        "/api/auth/login",
        json={"email": handler_user.email, "password": "HandlerPass123!"},
    )

    res = client.get("/api/admin/queue")
    assert res.status_code == 200
    data = res.get_json()["complaints"]
    assert len(data) >= 1

    found = next(c for c in data if c["id"] == comp.id)
    # Must contain anonymous identifier
    assert "Anonymous Submitter" in found["anonymous_submitter"]
    # Must NOT contain submitter email or name in payload
    assert "email" not in found
    assert verified_user.email not in str(found)
    assert verified_user.full_name not in str(found)


def test_audited_identity_reveal_lifecycle(client, admin_user, handler_user, verified_user, app):
    """Test identity reveal: admin permission check, mandatory justification, audit commit."""
    comp = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Fire alarm chirping",
        description="Smoke detector chirping low battery in lab.",
        user_category="Infrastructure",
        building="Computer Center / IT Labs",
        idempotency_token="alarm-1",
        status="submitted",
    )
    db.session.add(comp)
    db.session.commit()

    # 1. Non-admin (handler) is rejected
    client.post(
        "/api/auth/login",
        json={"email": handler_user.email, "password": "HandlerPass123!"},
    )
    res_handler = client.post(
        f"/api/admin/complaint/{comp.id}/reveal-identity",
        json={"justification": "Checking submitter info for follow up"},
    )
    assert res_handler.status_code == 403

    # 2. Admin without justification is rejected
    client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "AdminPass123!"},
    )
    res_no_just = client.post(
        f"/api/admin/complaint/{comp.id}/reveal-identity",
        json={"justification": "Too short"},
    )
    assert res_no_just.status_code == 400

    # 3. Admin with valid justification succeeds and commits AuditEvent
    justification = "Emergency maintenance team needs to confirm lab room key access directly."
    res_admin = client.post(
        f"/api/admin/complaint/{comp.id}/reveal-identity",
        json={"justification": justification},
    )
    assert res_admin.status_code == 200
    id_data = res_admin.get_json()["identity"]
    assert id_data["email"] == verified_user.email
    assert id_data["full_name"] == verified_user.full_name

    # Check AuditEvent committed
    audit_ev = AuditEvent.query.filter_by(target_id=comp.id).first()
    assert audit_ev is not None
    assert audit_ev.actor_id == admin_user.id
    assert audit_ev.action == "reveal_identity"
    assert audit_ev.justification == justification
    # Privacy rule: Disclosed personal data is NOT redundantly copied into the audit log
    assert verified_user.email not in audit_ev.justification


def test_admin_dashboard_metrics_breakdowns_and_recurring(client, handler_user, verified_user, app):
    """Test R6 Admin Dashboard: category, priority, 14-day trend, recurring issues."""
    from app.models.issue import Issue, IssueComplaintLink

    c1 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Dashboard Test 1",
        description="Hazardous sparking wire",
        user_category="Infrastructure",
        suggested_priority="Urgent review",
        building="Academic Block A",
        idempotency_token="dash-1",
        status="under_review",
    )
    c2 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Dashboard Test 2",
        description="Another broken socket",
        user_category="Infrastructure",
        suggested_priority="Urgent review",
        building="Academic Block A",
        idempotency_token="dash-2",
        status="under_review",
    )
    db.session.add_all([c1, c2])
    db.session.commit()

    issue = Issue(
        title="Recurring Electrical Issue",
        description="Aggregated electrical repairs",
        category="Infrastructure",
        building="Academic Block A",
        status="under_review",
        priority="Urgent review",
        created_by_user_id=handler_user.id,
    )
    db.session.add(issue)
    db.session.flush()

    db.session.add(IssueComplaintLink(issue_id=issue.id, complaint_id=c1.id, linked_by_user_id=handler_user.id))
    db.session.add(IssueComplaintLink(issue_id=issue.id, complaint_id=c2.id, linked_by_user_id=handler_user.id))
    db.session.commit()

    # Login as handler
    client.post(
        "/api/auth/login",
        json={"email": handler_user.email, "password": "HandlerPass123!"},
    )

    res = client.get("/api/admin/dashboard")
    assert res.status_code == 200
    data = res.get_json()
    assert "metrics" in data
    assert "category_breakdown" in data
    assert "priority_breakdown" in data
    assert "submission_trend" in data
    assert len(data["submission_trend"]) == 14
    assert "multi_report_issues" in data
    assert "recurring_issues" in data
    assert len(data["multi_report_issues"]) >= 1
    rec = data["multi_report_issues"][0]
    assert rec["id"] == issue.id
    assert rec["report_count"] == 2

