import urllib.request
import urllib.parse
import http.cookiejar
import json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Fetch CSRF
req_csrf = urllib.request.Request("https://digital-campus-sczg.onrender.com/api/auth/csrf")
with opener.open(req_csrf) as resp:
    data = json.loads(resp.read().decode())
    csrf = data.get("csrf_token")

# 2. Try login with admin@campus.edu / AdminPass123!
login_data = json.dumps({"email": "admin@campus.edu", "password": "AdminPass123!"}).encode()
req_login = urllib.request.Request(
    "https://digital-campus-sczg.onrender.com/api/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json", "X-CSRFToken": csrf}
)
try:
    with opener.open(req_login) as resp:
        print("HTTP Status:", resp.status)
        data = json.loads(resp.read().decode())
        print("Success:", data.get("success"), "User:", data.get("user", {}).get("email"))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print("Response:", e.read().decode())

