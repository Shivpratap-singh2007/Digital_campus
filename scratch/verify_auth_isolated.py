import os
import sys
import tempfile
import json
import uuid
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Setup isolated environment
temp_dir = tempfile.mkdtemp(prefix="cv_test_auth_")
test_db_path = os.path.join(temp_dir, "test_auth_isolated.db")

os.environ["SQLITE_PATH"] = test_db_path
os.environ["BOOTSTRAP_DEMO_DATA"] = "true"
os.environ["FIXTURE_ADMIN_PASSWORD"] = "AdminAuthTest123!"
os.environ["FIXTURE_HANDLER_PASSWORD"] = "HandlerAuthTest123!"
os.environ["FIXTURE_STUDENT_PASSWORD"] = "StudentAuthTest123!"
os.environ["SECRET_KEY"] = "test-secret-key-for-isolated-auth-run-12345678"

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.complaint import Complaint
from app.models.issue import Issue

app = create_app()

results = {}

with app.test_client() as client:
    print("=================================================================")
    print("RUNNING ISOLATED AUTHENTICATION & PROVISIONING VERIFICATION SUITE")
    print(f"Isolated DB Path: {test_db_path}")
    print("=================================================================\n")

    # -------------------------------------------------------------
    # STEP 1: Verify bootstrap created synthetic fixtures
    # -------------------------------------------------------------
    with app.app_context():
        admin = User.query.filter_by(email="admin@campus.edu").first()
        handler = User.query.filter_by(email="handler@campus.edu").first()
        student = User.query.filter_by(email="student.aarav@campus.edu").first()
        
        assert admin is not None, "Admin was not provisioned"
        assert admin.role == "admin", "Admin role mismatch"
        assert admin.is_verified is True, "Admin is_verified mismatch"
        assert admin.is_synthetic_fixture is True, "Admin fixture flag mismatch"
        assert admin.check_password("AdminAuthTest123!"), "Admin password verification failed"
        
        assert handler is not None, "Handler was not provisioned"
        assert handler.role == "handler", "Handler role mismatch"
        
        assert student is not None, "Student was not provisioned"
        assert student.role == "user", "Student role mismatch"
        
        # Check baseline complaint exists
        baseline_complaint = Complaint.query.first()
        assert baseline_complaint is not None, "Baseline complaint was not seeded"
        baseline_complaint_id = baseline_complaint.id
        print("  [PASS] Step 1: Idempotent synthetic fixtures successfully provisioned in isolated DB.")

    # -------------------------------------------------------------
    # STEP 2: Fetch CSRF token
    # -------------------------------------------------------------
    csrf_resp = client.get("/api/auth/csrf")
    assert csrf_resp.status_code == 200, f"CSRF fetch failed: {csrf_resp.status_code}"
    csrf_data = csrf_resp.get_json()
    csrf_token = csrf_data.get("csrf_token")
    assert csrf_token is not None, "No CSRF token returned"
    print("  [PASS] Step 2: Proactive CSRF token fetched successfully.")

    # -------------------------------------------------------------
    # STEP 3: Missing or Invalid CSRF is rejected
    # -------------------------------------------------------------
    # 3a. Missing CSRF header
    no_csrf_resp = client.post(
        "/api/auth/login",
        json={"email": "admin@campus.edu", "password": "AdminAuthTest123!"},
    )
    assert no_csrf_resp.status_code == 400, f"Expected 400 for missing CSRF, got {no_csrf_resp.status_code}"
    print("  [PASS] Step 3a: Login request without X-CSRFToken header correctly rejected with HTTP 400.")

    # 3b. Invalid CSRF header
    bad_csrf_resp = client.post(
        "/api/auth/login",
        json={"email": "admin@campus.edu", "password": "AdminAuthTest123!"},
        headers={"X-CSRFToken": "invalid-garbage-token"},
    )
    assert bad_csrf_resp.status_code == 400, f"Expected 400 for invalid CSRF, got {bad_csrf_resp.status_code}"
    print("  [PASS] Step 3b: Login request with invalid CSRF token correctly rejected with HTTP 400.")

    # -------------------------------------------------------------
    # STEP 4: Incorrect password returns 401
    # -------------------------------------------------------------
    bad_pw_resp = client.post(
        "/api/auth/login",
        json={"email": "admin@campus.edu", "password": "WrongPassword999!"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert bad_pw_resp.status_code == 401, f"Expected 401 for bad password, got {bad_pw_resp.status_code}"
    bad_pw_data = bad_pw_resp.get_json()
    assert bad_pw_data.get("error") == "Invalid email address or password."
    print("  [PASS] Step 4: Login attempt with wrong password returned HTTP 401 (generic failure).")

    # -------------------------------------------------------------
    # STEP 5: Provisioned synthetic admin can log in
    # -------------------------------------------------------------
    # Re-fetch CSRF to ensure clean token
    csrf_token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "admin@campus.edu", "password": "AdminAuthTest123!"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert login_resp.status_code == 200, f"Expected 200, got {login_resp.status_code}: {login_resp.get_data(as_text=True)}"
    login_data = login_resp.get_json()
    assert login_data.get("success") is True
    assert login_data["user"]["email"] == "admin@campus.edu"
    assert login_data["user"]["role"] == "admin"
    assert login_data["user"]["is_admin"] is True
    print("  [PASS] Step 5: Provisioned synthetic admin logged in successfully (HTTP 200).")

    # -------------------------------------------------------------
    # STEP 6: Authenticated /api/auth/me identifies correct account/role
    # -------------------------------------------------------------
    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    me_data = me_resp.get_json()
    assert me_data["authenticated"] is True
    assert me_data["user"]["email"] == "admin@campus.edu"
    assert me_data["user"]["role"] == "admin"
    assert me_data["user"]["is_admin"] is True
    print("  [PASS] Step 6: GET /api/auth/me accurately identifies admin role and verification state.")

    # -------------------------------------------------------------
    # STEP 7: Admin can access privileged endpoint
    # -------------------------------------------------------------
    queue_resp = client.get("/api/admin/queue")
    assert queue_resp.status_code == 200, f"Expected 200 for admin queue, got {queue_resp.status_code}"
    print("  [PASS] Step 7: Authenticated admin successfully accessed /api/admin/queue.")

    # -------------------------------------------------------------
    # STEP 8: Logout blocks authenticated access
    # -------------------------------------------------------------
    csrf_token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    logout_resp = client.post("/api/auth/logout", headers={"X-CSRFToken": csrf_token})
    assert logout_resp.status_code == 200
    me_after_logout = client.get("/api/auth/me").get_json()
    assert me_after_logout["authenticated"] is False
    post_logout_queue = client.get("/api/admin/queue")
    assert post_logout_queue.status_code in (401, 403), "Access was not revoked after logout"
    print("  [PASS] Step 8: POST /api/auth/logout revoked session; protected routes return 401/403.")

    # -------------------------------------------------------------
    # STEP 9: Student cannot access admin actions
    # -------------------------------------------------------------
    csrf_token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    student_login = client.post(
        "/api/auth/login",
        json={"email": "student.aarav@campus.edu", "password": "StudentAuthTest123!"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert student_login.status_code == 200
    student_queue = client.get("/api/admin/queue")
    assert student_queue.status_code == 403, f"Expected 403 for student accessing admin queue, got {student_queue.status_code}"
    
    # Student reveal identity attempt
    student_reveal = client.post(
        f"/api/admin/complaint/{baseline_complaint_id}/reveal-identity",
        json={"justification": "Malicious attempt by student"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert student_reveal.status_code == 403, f"Expected 403 for student reveal identity, got {student_reveal.status_code}"
    print("  [PASS] Step 9: Authenticated student strictly forbidden (HTTP 403) from admin queue and identity reveal.")

    # -------------------------------------------------------------
    # STEP 10: Existing records remain intact on second bootstrap run
    # -------------------------------------------------------------
    with app.app_context():
        from app.services.fixtures import provision_synthetic_fixtures
        # Run bootstrap again with DIFFERENT password parameter to ensure existing password is NOT changed
        second_run = provision_synthetic_fixtures(admin_password="NewAttemptPassword999!")
        
        # Verify preserved
        preserved_emails = [p["email"] for p in second_run["preserved"]]
        assert "admin@campus.edu" in preserved_emails, "Admin was not preserved"
        
        # Verify admin password was NOT changed to NewAttemptPassword999!
        admin_refetch = User.query.filter_by(email="admin@campus.edu").first()
        assert admin_refetch.check_password("AdminAuthTest123!"), "Existing admin password was improperly overwritten!"
        assert not admin_refetch.check_password("NewAttemptPassword999!"), "New password should not have been set!"
        
        # Verify complaint count didn't drop or reset
        assert Complaint.query.count() >= 1, "Existing complaints were lost!"
        print("  [PASS] Step 10: Idempotency verified: re-running bootstrap preserved existing accounts and did NOT overwrite passwords.")

print("\n=================================================================")
print("ALL 10 ISOLATED AUTHENTICATION VERIFICATIONS PASSED SUCCESSFULLY!")
print("=================================================================")
