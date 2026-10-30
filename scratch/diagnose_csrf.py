import urllib.request
import urllib.parse
import http.cookiejar
import json
import ssl

def diagnose_target(base_url, label):
    print(f"\n=======================================================")
    print(f"DIAGNOSING: {label} ({base_url})")
    print(f"=======================================================")
    
    cj = http.cookiejar.CookieJar()
    ctx = ssl.create_default_context()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=ctx)
    )
    
    # 1. Fetch CSRF token
    csrf_url = f"{base_url}/api/auth/csrf-token"
    print(f"[1] Requesting GET {csrf_url}...")
    try:
        req = urllib.request.Request(csrf_url)
        with opener.open(req) as resp:
            headers = dict(resp.headers)
            body = resp.read().decode()
            print(f"  Status: {resp.status}")
            print(f"  Content-Type: {headers.get('Content-Type')}")
            print(f"  Cache-Control: {headers.get('Cache-Control')}")
            print(f"  Set-Cookie raw: {headers.get('Set-Cookie')}")
            print(f"  Body: {body}")
            csrf_data = json.loads(body)
            token = csrf_data.get("csrf_token")
    except Exception as e:
        print(f"  GET CSRF failed: {e}")
        return

    # Inspect cookies stored in jar
    print(f"\n[2] Inspecting stored cookies in CookieJar:")
    cookies = list(cj)
    print(f"  Total cookies: {len(cookies)}")
    session_cookie = None
    for c in cookies:
        print(f"  Cookie: name={c.name}, domain={c.domain}, path={c.path}, secure={c.secure}, httponly={c.has_nonstandard_attr('httponly') or 'HttpOnly' in str(c._rest)}, value_len={len(c.value)}")
        if c.name == "session":
            session_cookie = c

    # 3. Attempt POST /api/auth/login WITH cookie and WITH X-CSRFToken
    login_url = f"{base_url}/api/auth/login"
    print(f"\n[3] Testing POST {login_url} WITH session cookie & WITH X-CSRFToken header...")
    login_payload = json.dumps({"email": "admin@campus.edu", "password": "AdminPass123!"}).encode("utf-8")
    login_req = urllib.request.Request(
        login_url,
        data=login_payload,
        headers={"Content-Type": "application/json", "X-CSRFToken": token}
    )
    try:
        with opener.open(login_req) as resp:
            print(f"  Status: {resp.status}")
            print(f"  Response: {resp.read().decode()}")
    except urllib.error.HTTPError as e:
        print(f"  Status: {e.code}")
        print(f"  Error Response: {e.read().decode()}")

    # 4. Attempt POST /api/auth/login WITHOUT session cookie (simulating missing session)
    print(f"\n[4] Testing POST {login_url} WITHOUT session cookie (fresh opener, sending token header only)...")
    fresh_opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    req_no_cookie = urllib.request.Request(
        login_url,
        data=login_payload,
        headers={"Content-Type": "application/json", "X-CSRFToken": token}
    )
    try:
        with fresh_opener.open(req_no_cookie) as resp:
            print(f"  Status: {resp.status}")
            print(f"  Response: {resp.read().decode()}")
    except urllib.error.HTTPError as e:
        print(f"  Status: {e.code}")
        print(f"  Error Response: {e.read().decode()}")

    # 5. Check deployed frontend bundle
    print(f"\n[5] Checking deployed HTML and script tags at {base_url}/login...")
    try:
        req_login_page = urllib.request.Request(f"{base_url}/login")
        with opener.open(req_login_page) as resp:
            html = resp.read().decode()
            scripts = [line.strip() for line in html.splitlines() if "<script" in line]
            print(f"  Status: {resp.status}")
            print(f"  Script tags: {scripts}")
    except Exception as e:
        print(f"  Failed: {e}")

if __name__ == "__main__":
    diagnose_target("http://127.0.0.1:5000", "LOCAL SERVER")
    diagnose_target("https://digital-campus-sczg.onrender.com", "LIVE RENDER SERVER")

