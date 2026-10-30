import urllib.request
import http.cookiejar
import json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Fetch CSRF
req_csrf = urllib.request.Request("https://digital-campus-sczg.onrender.com/api/auth/csrf")
with opener.open(req_csrf) as resp:
    csrf = json.loads(resp.read().decode()).get("csrf_token")

data = json.dumps({"email": "admin@campus.edu"}).encode()
req = urllib.request.Request(
    "https://digital-campus-sczg.onrender.com/api/auth/resend-verification",
    data=data,
    headers={"Content-Type": "application/json", "X-CSRFToken": csrf}
)
try:
    with opener.open(req) as resp:
        print("Response:", resp.read().decode())
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode())
