import urllib.request
import urllib.parse
import http.cookiejar
import json
import uuid
import sys
import io

BASE_URL = "http://127.0.0.1:5000"

def get_client():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    return opener, cj

results = {}

print("================================================================")
print("RUNNING VERIFICATION SUITE: CSRF & SESSION SECURITY FIX")
print("================================================================\n")

# -------------------------------------------------------------
# TEST 1: Fresh session -> fetch CSRF -> valid login succeeds
# -------------------------------------------------------------
print("[TEST 1] Fresh session -> fetch CSRF -> valid login succeeds")
c1, cj1 = get_client()

# Fetch CSRF from /api/auth/csrf
req_csrf = urllib.request.Request(f"{BASE_URL}/api/auth/csrf")
with c1.open(req_csrf) as resp:
    csrf_headers = dict(resp.headers)
    csrf_data = json.loads(resp.read().decode())
    token1 = csrf_data.get("csrf_token")
    cache_control = csrf_headers.get("Cache-Control", "")
    has_no_store = "no-store" in cache_control

# Verify session cookie exists in cookiejar
session_cookies = [c for c in cj1 if c.name == "session"]
has_session_cookie = len(session_cookies) == 1

# Now login with valid fixture credentials
login_body = json.dumps({"email": "admin@campus.edu", "password": "AdminPass123!"}).encode("utf-8")
req_login = urllib.request.Request(
    f"{BASE_URL}/api/auth/login",
    data=login_body,
    headers={"Content-Type": "application/json", "X-CSRFToken": token1}
)
with c1.open(req_login) as resp:
    login_status = resp.status
    login_data = json.loads(resp.read().decode())
    login_success = login_data.get("success") is True and login_data.get("user", {}).get("email") == "admin@campus.edu"

t1_pass = has_no_store and has_session_cookie and (login_status == 200) and login_success
results["test1_fresh_csrf_login"] = {
    "status": "PASS" if t1_pass else "FAIL",
    "evidence": f"Cache-Control: '{cache_control}' (no-store: {has_no_store}), Session cookie set: {has_session_cookie}, Login status: {login_status}, Authenticated user: {login_data.get('user', {}).get('email')}"
}
print(f"Result: {results['test1_fresh_csrf_login']['status']} -> {results['test1_fresh_csrf_login']['evidence']}\n")

# -------------------------------------------------------------
# TEST 2: Missing CSRF header is rejected
# -------------------------------------------------------------
print("[TEST 2] Missing CSRF header is rejected (with session cookie present)")
c2, cj2 = get_client()

# Establish session cookie via GET /api/auth/csrf
with c2.open(f"{BASE_URL}/api/auth/csrf") as resp:
    pass

# Attempt POST login WITHOUT X-CSRFToken header
req_no_csrf = urllib.request.Request(
    f"{BASE_URL}/api/auth/login",
    data=login_body,
    headers={"Content-Type": "application/json"} # NO X-CSRFToken
)
try:
    with c2.open(req_no_csrf) as resp:
        t2_status = resp.status
        t2_err = resp.read().decode()
except urllib.error.HTTPError as e:
    t2_status = e.code
    t2_err = json.loads(e.read().decode())

t2_pass = (t2_status == 400) and (t2_err.get("code") == "CSRF_ERROR")
results["test2_missing_header_rejected"] = {
    "status": "PASS" if t2_pass else "FAIL",
    "evidence": f"Status: {t2_status} (expected 400), Code: '{t2_err.get('code')}', Message: '{t2_err.get('error')}'"
}
print(f"Result: {results['test2_missing_header_rejected']['status']} -> {results['test2_missing_header_rejected']['evidence']}\n")

# -------------------------------------------------------------
# TEST 3: Token without its matching session is rejected
# -------------------------------------------------------------
print("[TEST 3] Token without its matching session is rejected ('The CSRF session token is missing.')")
# Client 3 has a valid token string from Client 1, but NO session cookie
c3_no_cookie = urllib.request.build_opener() # No cookie processor
req_no_session = urllib.request.Request(
    f"{BASE_URL}/api/auth/login",
    data=login_body,
    headers={"Content-Type": "application/json", "X-CSRFToken": token1}
)
try:
    with c3_no_cookie.open(req_no_session) as resp:
        t3_status = resp.status
        t3_err = resp.read().decode()
except urllib.error.HTTPError as e:
    t3_status = e.code
    t3_err = json.loads(e.read().decode())

t3_is_missing_session = "CSRF session token is missing" in str(t3_err.get("error")) or "CSRF session token is missing" in str(t3_err.get("message"))
t3_pass = (t3_status == 400) and (t3_err.get("code") == "CSRF_ERROR") and t3_is_missing_session
results["test3_token_without_session_rejected"] = {
    "status": "PASS" if t3_pass else "FAIL",
    "evidence": f"Status: {t3_status} (expected 400), Code: '{t3_err.get('code')}', Error text: '{t3_err.get('error')}', Missing session verified: {t3_is_missing_session}"
}
print(f"Result: {results['test3_token_without_session_rejected']['status']} -> {results['test3_token_without_session_rejected']['evidence']}\n")

# -------------------------------------------------------------
# TEST 4: Incorrect password with valid CSRF still returns auth failure (401)
# -------------------------------------------------------------
print("[TEST 4] Incorrect password with valid CSRF returns 401 Authentication Failure")
c4, cj4 = get_client()
with c4.open(f"{BASE_URL}/api/auth/csrf") as resp:
    token4 = json.loads(resp.read().decode())["csrf_token"]

bad_pass_body = json.dumps({"email": "admin@campus.edu", "password": "WrongPassword999!"}).encode("utf-8")
req_bad_pass = urllib.request.Request(
    f"{BASE_URL}/api/auth/login",
    data=bad_pass_body,
    headers={"Content-Type": "application/json", "X-CSRFToken": token4}
)
try:
    with c4.open(req_bad_pass) as resp:
        t4_status = resp.status
        t4_data = resp.read().decode()
except urllib.error.HTTPError as e:
    t4_status = e.code
    t4_data = json.loads(e.read().decode())

t4_pass = (t4_status == 401) and ("Invalid email address or password" in t4_data.get("error", ""))
results["test4_bad_password_returns_401"] = {
    "status": "PASS" if t4_pass else "FAIL",
    "evidence": f"Status: {t4_status} (expected 401), Error message: '{t4_data.get('error')}' (CSRF passed, credentials failed)"
}
print(f"Result: {results['test4_bad_password_returns_401']['status']} -> {results['test4_bad_password_returns_401']['evidence']}\n")

# -------------------------------------------------------------
# TEST 5: Logout -> fresh CSRF -> login works again
# -------------------------------------------------------------
print("[TEST 5] Logout -> fresh CSRF -> login works again")
c5, cj5 = get_client()
with c5.open(f"{BASE_URL}/api/auth/csrf") as resp:
    tok5_pre = json.loads(resp.read().decode())["csrf_token"]

# Log in Aarav
aarav_login = json.dumps({"email": "student.aarav@campus.edu", "password": "StudentPass123!"}).encode("utf-8")
req_login5 = urllib.request.Request(
    f"{BASE_URL}/api/auth/login",
    data=aarav_login,
    headers={"Content-Type": "application/json", "X-CSRFToken": tok5_pre}
)
with c5.open(req_login5) as resp:
    pass

# Verify logged in
with c5.open(f"{BASE_URL}/api/auth/me") as resp:
    me_data = json.loads(resp.read().decode())
    assert me_data.get("authenticated") is True

# Logout
logout_req = urllib.request.Request(
    f"{BASE_URL}/api/auth/logout",
    data=b"{}",
    headers={"Content-Type": "application/json", "X-CSRFToken": tok5_pre}
)
with c5.open(logout_req) as resp:
    logout_stat = resp.status

# Check unauthenticated
with c5.open(f"{BASE_URL}/api/auth/me") as resp:
    me_logged_out = json.loads(resp.read().decode()).get("authenticated") is False

# Fetch fresh token for next login
with c5.open(f"{BASE_URL}/api/auth/csrf") as resp:
    tok5_post = json.loads(resp.read().decode())["csrf_token"]

# Re-login Aarav with fresh token
req_relogin = urllib.request.Request(
    f"{BASE_URL}/api/auth/login",
    data=aarav_login,
    headers={"Content-Type": "application/json", "X-CSRFToken": tok5_post}
)
with c5.open(req_relogin) as resp:
    relogin_stat = resp.status
    relogin_data = json.loads(resp.read().decode())
    relogin_ok = relogin_data.get("success") is True

t5_pass = (logout_stat == 200) and me_logged_out and (relogin_stat == 200) and relogin_ok
results["test5_logout_relogin_flow"] = {
    "status": "PASS" if t5_pass else "FAIL",
    "evidence": f"Logout status: {logout_stat}, Logged out me check: {me_logged_out}, Re-login status: {relogin_stat}, User re-authenticated: {relogin_data.get('user', {}).get('email')}"
}
print(f"Result: {results['test5_logout_relogin_flow']['status']} -> {results['test5_logout_relogin_flow']['evidence']}\n")

# -------------------------------------------------------------
# TEST 6: Complaint submission and multipart upload still work
# -------------------------------------------------------------
print("[TEST 6] Complaint submission and multipart upload with CSRF")
from PIL import Image as PILImage
test_img = PILImage.new("RGB", (30, 30), color="blue")
img_buf = io.BytesIO()
test_img.save(img_buf, format="PNG")
png_bytes = img_buf.getvalue()

boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
body_io = io.BytesIO()

def add_field(name, value):
    body_io.write(f"--{boundary}\r\n".encode())
    body_io.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
    body_io.write(f"{value}\r\n".encode())

add_field("submission_type", "complaint")
add_field("title", "[QA TEST] CSRF Multipart Image Upload Test")
add_field("description", "Testing multipart form submission with image attachment under active CSRF enforcement.")
add_field("user_category", "Sanitation")
add_field("building", "Academic Block A")
add_field("room", "101")
add_field("idempotency_token", str(uuid.uuid4()))

# File field
body_io.write(f"--{boundary}\r\n".encode())
body_io.write(b'Content-Disposition: form-data; name="image"; filename="test_photo.png"\r\n')
body_io.write(b'Content-Type: image/png\r\n\r\n')
body_io.write(png_bytes)
body_io.write(b'\r\n')
body_io.write(f"--{boundary}--\r\n".encode())

multipart_payload = body_io.getvalue()

# Get fresh token for c5 (logged in as Aarav)
with c5.open(f"{BASE_URL}/api/auth/csrf") as resp:
    complaint_token = json.loads(resp.read().decode())["csrf_token"]

req_multipart = urllib.request.Request(
    f"{BASE_URL}/api/complaints",
    data=multipart_payload,
    headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "X-CSRFToken": complaint_token
    }
)
with c5.open(req_multipart) as resp:
    comp_status = resp.status
    comp_json = json.loads(resp.read().decode())
    new_cid = comp_json.get("id")

# Fetch complaint details to confirm image was processed
with c5.open(f"{BASE_URL}/api/complaints/{new_cid}") as resp:
    cid_data = json.loads(resp.read().decode())
    attachments = cid_data.get("attachments", [])
    has_photo = len(attachments) > 0

t6_pass = (comp_status == 201) and (new_cid is not None) and has_photo
results["test6_multipart_complaint_csrf"] = {
    "status": "PASS" if t6_pass else "FAIL",
    "evidence": f"Created Complaint #{new_cid} (Status: {comp_status}), Multipart attachment stored: {has_photo} (count={len(attachments)})"
}
print(f"Result: {results['test6_multipart_complaint_csrf']['status']} -> {results['test6_multipart_complaint_csrf']['evidence']}\n")

# -------------------------------------------------------------
# TEST 7: Role permissions remain enforced
# -------------------------------------------------------------
print("[TEST 7] Role permissions remain enforced")
# A. Student Aarav blocked from queue
try:
    with c5.open(f"{BASE_URL}/api/admin/queue") as resp:
        student_blocked = False
except urllib.error.HTTPError as e:
    student_blocked = (e.code == 403)

# B. Handler can access queue
c_handler, _ = get_client()
with c_handler.open(f"{BASE_URL}/api/auth/csrf") as resp:
    h_token = json.loads(resp.read().decode())["csrf_token"]

h_login = json.dumps({"email": "handler@campus.edu", "password": "HandlerPass123!"}).encode("utf-8")
req_h_login = urllib.request.Request(
    f"{BASE_URL}/api/auth/login",
    data=h_login,
    headers={"Content-Type": "application/json", "X-CSRFToken": h_token}
)
with c_handler.open(req_h_login) as resp:
    pass

with c_handler.open(f"{BASE_URL}/api/admin/queue") as resp:
    handler_ok = (resp.status == 200)

# C. Unverified student blocked from submit
c_unver, _ = get_client()
with c_unver.open(f"{BASE_URL}/api/auth/csrf") as resp:
    u_token = json.loads(resp.read().decode())["csrf_token"]

u_login = json.dumps({"email": "student.unverified@campus.edu", "password": "StudentPass123!"}).encode("utf-8")
req_u_login = urllib.request.Request(
    f"{BASE_URL}/api/auth/login",
    data=u_login,
    headers={"Content-Type": "application/json", "X-CSRFToken": u_token}
)
with c_unver.open(req_u_login) as resp:
    pass

with c_unver.open(f"{BASE_URL}/api/auth/csrf") as resp:
    u_submit_tok = json.loads(resp.read().decode())["csrf_token"]

sub_blocked_payload = json.dumps({
    "title": "[QA TEST] Should be blocked",
    "description": "Unverified student submitting",
    "user_category": "Sanitation",
    "building": "Academic Block A",
    "idempotency_token": str(uuid.uuid4())
}).encode("utf-8")

req_sub_blocked = urllib.request.Request(
    f"{BASE_URL}/api/complaints",
    data=sub_blocked_payload,
    headers={"Content-Type": "application/json", "X-CSRFToken": u_submit_tok}
)
try:
    with c_unver.open(req_sub_blocked) as resp:
        unver_blocked = False
except urllib.error.HTTPError as e:
    unver_blocked = (e.code == 403)

t7_pass = student_blocked and handler_ok and unver_blocked
results["test7_role_permissions"] = {
    "status": "PASS" if t7_pass else "FAIL",
    "evidence": f"Student blocked from queue: {student_blocked} (403), Handler queue access: {handler_ok} (200), Unverified submit blocked: {unver_blocked} (403)"
}
print(f"Result: {results['test7_role_permissions']['status']} -> {results['test7_role_permissions']['evidence']}\n")

# -------------------------------------------------------------
# SUMMARY
# -------------------------------------------------------------
print("================================================================")
print("CSRF & SESSION SECURITY VERIFICATION SUMMARY")
print("================================================================")
all_tests_passed = True
for name, data in results.items():
    print(f"[{data['status']}] {name}: {data['evidence']}")
    if data["status"] != "PASS":
        all_tests_passed = False

print(f"\nOVERALL RESULT: {'ALL 7 CSRF ACCEPTANCE TESTS PASSED' if all_tests_passed else 'SOME TESTS FAILED'}")
print("================================================================")
