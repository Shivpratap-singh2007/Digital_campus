from app.models.user import User, VerificationToken
from app.services.email import create_verification_token, verify_token


def test_registration_allowed_domain(client, app):
    """Test registration succeeds with allowed domain and creates unverified user."""
    res = client.post(
        "/api/auth/register",
        json={
            "full_name": "Rohan Sharma",
            "email": "rohan@campus.edu",
            "password": "Password123!",
        },
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True

    user = User.query.filter_by(email="rohan@campus.edu").first()
    assert user is not None
    assert user.is_verified is False
    assert user.role == "user"
    assert user.check_password("Password123!") is True


def test_registration_disallowed_domain(client, app):
    """Test registration is rejected for external/disallowed domains."""
    res = client.post(
        "/api/auth/register",
        json={
            "full_name": "External User",
            "email": "attacker@gmail.com",
            "password": "Password123!",
        },
    )
    assert res.status_code == 400
    data = res.get_json()
    assert "Registration is restricted" in data["error"]


def test_registration_subdomain_bypass_prevention(client, app):
    """Test domain matching is exact parsed-domain matching, not substring match."""
    # Attempting tricky subdomain: campus.edu.attacker.com
    res = client.post(
        "/api/auth/register",
        json={
            "full_name": "Tricky User",
            "email": "user@campus.edu.attacker.com",
            "password": "Password123!",
        },
    )
    assert res.status_code == 400


def test_verification_token_lifecycle(app, unverified_user):
    """Test single-use verification token lifecycle and hashing."""
    raw_token, token_obj = create_verification_token(unverified_user)
    
    # Raw token is not stored in DB, only the SHA-256 hash
    stored_token = VerificationToken.query.filter_by(user_id=unverified_user.id).first()
    assert stored_token.token_hash != raw_token
    assert stored_token.used_at is None

    # Verify token
    success, msg, user = verify_token(raw_token)
    assert success is True
    assert user.is_verified is True
    assert stored_token.used_at is not None

    # Re-using the same token fails
    success_reuse, msg_reuse, _ = verify_token(raw_token)
    assert success_reuse is False
    assert "already been used" in msg_reuse


def test_login_and_logout(client, verified_user):
    """Test login sets session and logout clears session."""
    # Login
    res = client.post(
        "/api/auth/login",
        json={"email": verified_user.email, "password": "StudentPass123!"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["email"] == verified_user.email

    # Check /api/auth/me
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["authenticated"] is True

    # Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    # Check /api/auth/me again
    me_after = client.get("/api/auth/me")
    assert me_after.get_json()["authenticated"] is False


def test_provision_synthetic_fixtures_and_baseline_data(app):
    """Test R9: synthetic demo fixture provisioning covers accounts, categories, suggestions, grouping, and feedback."""
    from app.services.fixtures import provision_synthetic_fixtures
    from app.models.issue import Issue, IssueComplaintLink
    from app.models.complaint import Complaint
    from app.models.feedback import ResolutionRound

    res = provision_synthetic_fixtures(
        app=app,
        admin_password="AdminSecure123!",
        handler_password="HandlerSecure123!",
        student_password="StudentSecure123!",
    )
    assert len(res["created"]) >= 4

    # Check complaints across categories
    categories = set(c.user_category for c in Complaint.query.all())
    assert "Infrastructure" in categories
    assert "Sanitation" in categories
    assert "Academics" in categories
    assert "Student services" in categories
    assert "IT / connectivity" in categories

    # Check suggestion exists
    suggestion = Complaint.query.filter_by(submission_type="suggestion").first()
    assert suggestion is not None

    # Check issues with grouping
    issues = Issue.query.all()
    assert len(issues) >= 3

    # Check resolved issue and round
    resolved = Issue.query.filter_by(status="resolved").first()
    assert resolved is not None
    assert resolved.current_resolution_round is not None
    assert resolved.current_resolution_round.status == "submitter_confirmed"

    # Check disputed round
    disputed = ResolutionRound.query.filter_by(status="disputed").first()
    assert disputed is not None

