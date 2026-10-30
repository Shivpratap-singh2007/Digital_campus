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

