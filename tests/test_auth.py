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

