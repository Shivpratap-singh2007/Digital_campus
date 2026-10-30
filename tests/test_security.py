import pytest
from app.models.user import User
from app.models.complaint import Complaint
from app.extensions import db
from app.services.rate_limiter import limiter
from app.services.security import validate_password_strength, sanitize_text


def test_security_headers_present(client):
    """Verifies standard OWASP security headers on all HTTP responses."""
    res = client.get("/api/auth/me")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in res.headers
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in res.headers.get("Permissions-Policy", "")


def test_password_strength_enforcement(client):
    """Verifies that weak and easily guessed passwords are systematically rejected."""
    # Too short
    valid, msg = validate_password_strength("Short1!")
    assert valid is False

    # Common password
    valid, msg = validate_password_strength("password123")
    assert valid is False

    # Missing uppercase/symbol
    valid, msg = validate_password_strength("alllowercase123")
    assert valid is False

    # Strong password
    valid, msg = validate_password_strength("ComplexPass2026!Secure")
    assert valid is True

    # Attempt registration with weak password
    res = client.post(
        "/api/auth/register",
        json={
            "full_name": "Weak Password User",
            "email": "weak@campus.edu",
            "password": "password",
        },
    )
    assert res.status_code == 400
    data = res.get_json()
    assert "password" in data["error"].lower()


def test_xss_input_sanitization():
    """Verifies that dangerous HTML/script injection attempts are neutralized."""
    malicious_input = "<script>alert('XSS')</script><img src=x onerror=alert(1)>"
    sanitized = sanitize_text(malicious_input)
    assert "<script>" not in sanitized
    assert "&lt;script&gt;" in sanitized
    assert "<img" not in sanitized


def test_admin_route_unauthorized_rejection(client, verified_user):
    """Verifies that non-admin users cannot access administrative endpoints."""
    # 1. Unauthenticated request
    res = client.get("/api/admin/audit-log")
    assert res.status_code in (401, 403)

    # 2. Authenticated as ordinary user
    client.post(
        "/api/auth/login",
        json={"email": verified_user.email, "password": "StudentPass123!"},
    )
    res = client.get("/api/admin/audit-log")
    assert res.status_code == 403
    assert "Access Denied" in res.get_json()["error"]


def test_handler_route_ordinary_user_rejection(client, verified_user):
    """Verifies that ordinary users cannot access handler queue or issue synthesis."""
    client.post(
        "/api/auth/login",
        json={"email": verified_user.email, "password": "StudentPass123!"},
    )

    # Try accessing operations queue
    res = client.get("/api/admin/queue")
    assert res.status_code == 403

    # Try creating master issue
    res = client.post(
        "/api/issues",
        json={
            "title": "Unauthorized Master Issue",
            "description": "Attempting to create master issue as ordinary student.",
            "building": "Academic Block A",
        },
    )
    assert res.status_code == 403


def test_idor_complaint_access_control(app):
    """Verifies Insecure Direct Object Reference (IDOR) protection: User A cannot access User B's report."""
    client_a = app.test_client()
    client_b = app.test_client()

    with app.app_context():
        user_a = User(email="usera@campus.edu", full_name="User A", role="user", is_verified=True)
        user_a.set_password("StudentPass123!")
        user_b = User(email="userb@campus.edu", full_name="User B", role="user", is_verified=True)
        user_b.set_password("StudentPass123!")
        db.session.add_all([user_a, user_b])
        db.session.commit()

        # Login User A
        client_a.post("/api/auth/login", json={"email": "usera@campus.edu", "password": "StudentPass123!"})

        # User A submits a complaint
        res_a = client_a.post(
            "/api/complaints",
            json={
                "title": "User A Private Malfunction",
                "description": "Sensitive report submitted by User A.",
                "building": "Academic Block A",
                "submission_type": "complaint",
            },
        )
        assert res_a.status_code == 201
        complaint_a_id = res_a.get_json()["id"]

        # Login User B on separate client session
        client_b.post("/api/auth/login", json={"email": "userb@campus.edu", "password": "StudentPass123!"})

        # User B attempts to access User A's private complaint
        res_b = client_b.get(f"/api/complaints/{complaint_a_id}")
        assert res_b.status_code == 403


def test_rate_limiting_enforcement():
    """Verifies that the sliding window rate limiter returns 429 when threshold exceeded."""
    limiter.reset()
    key = "test_endpoint:127.0.0.1"
    limit = 3
    window = 60

    # First 3 hits allowed
    for _ in range(limit):
        allowed, _ = limiter.is_allowed(key, limit=limit, window_seconds=window)
        assert allowed is True

    # 4th hit must be rejected
    allowed, retry_after = limiter.is_allowed(key, limit=limit, window_seconds=window)
    assert allowed is False
    assert retry_after > 0


def test_unknown_api_route_returns_json_404(client):
    """Verifies that unknown /api/* requests return JSON 404, never an HTML SPA template."""
    res = client.get("/api/nonexistent-endpoint-test")
    assert res.status_code == 404
    assert res.is_json
    data = res.get_json()
    assert "error" in data
    assert data["error"] == "Resource not found."


def test_health_check_endpoints(client):
    """Verifies that /api/health and /healthz return status 200 with JSON health report."""
    res_api = client.get("/api/health")
    assert res_api.status_code == 200
    assert res_api.is_json
    assert res_api.get_json()["status"] == "healthy"

    res_root = client.get("/healthz")
    assert res_root.status_code == 200
    assert res_root.is_json
    assert res_root.get_json()["status"] == "healthy"
