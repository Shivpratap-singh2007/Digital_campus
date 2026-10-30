import urllib.request
import urllib.parse
import http.cookiejar
import json

BASE_URL = "http://127.0.0.1:5000"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# First, test unauthenticated requests
urls = [
    "/",
    "/admin/dashboard",
    "/dashboard",
    "/admin/queue",
    "/tracker",
    "/settings",
    "/my-complaints",
    "/login",
    "/register",
    "/public-issues",
    "/complaints/1",
    "/issues/1",
    "/admin/audit-log",
    "/api/admin/dashboard",
    "/api/unknown-test-route",
    "/assets/index-pFovCmW5.js",
]

print("=== Testing Live Server Unauthenticated ===")
for path in urls:
    try:
        req = urllib.request.Request(f"{BASE_URL}{path}")
        with opener.open(req) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            is_react = '<div id="root">' in body
            is_legacy = "navbar-dark bg-dark" in body
            print(f"URL: {path:26} | Status: {resp.status} | React: {str(is_react):5} | Legacy Dark: {str(is_legacy):5}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        is_react = '<div id="root">' in body
        is_legacy = "navbar-dark bg-dark" in body
        print(f"URL: {path:26} | Status: {e.code} | React: {str(is_react):5} | Legacy Dark: {str(is_legacy):5}")

print("\n=== Authenticating as Admin ===")
# Fetch CSRF token first
with opener.open(f"{BASE_URL}/api/auth/csrf-token") as resp:
    csrf_res = json.loads(resp.read().decode())
    csrf_token = csrf_res.get("csrf_token")
    print(f"CSRF token obtained: {bool(csrf_token)}")

login_payload = json.dumps({"email": "admin@campus.edu", "password": "AdminPass123!"}).encode("utf-8")
login_req = urllib.request.Request(
    f"{BASE_URL}/api/auth/login",
    data=login_payload,
    headers={"Content-Type": "application/json", "X-CSRFToken": csrf_token}
)

with opener.open(login_req) as resp:
    login_body = json.loads(resp.read().decode())
    print(f"Login success: {login_body.get('user', {}).get('email')}")

print("\n=== Testing Live Server Authenticated as Admin ===")
for path in urls:
    try:
        req = urllib.request.Request(f"{BASE_URL}{path}")
        with opener.open(req) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            is_react = '<div id="root">' in body
            is_legacy = "navbar-dark bg-dark" in body
            print(f"URL: {path:26} | Status: {resp.status} | React: {str(is_react):5} | Legacy Dark: {str(is_legacy):5}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        is_react = '<div id="root">' in body
        is_legacy = "navbar-dark bg-dark" in body
        print(f"URL: {path:26} | Status: {e.code} | React: {str(is_react):5} | Legacy Dark: {str(is_legacy):5}")

