import sys
import os
sys.path.insert(0, os.path.abspath("."))

from app import create_app

app = create_app()
client = app.test_client()

urls_to_test = [
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
    "/api/unknown-route",
    "/assets/index-pFovCmW5.js",
    "/assets/nonexistent.js",
]

print("\n--- Direct GET Requests (When Unauthenticated) ---")
for path in urls_to_test:
    resp = client.get(path, follow_redirects=False)
    status = resp.status_code
    location = resp.headers.get("Location", "")
    content_type = resp.headers.get("Content-Type", "")
    data = resp.get_data(as_text=True)
    is_react = '<div id="root">' in data
    is_legacy_dark = "navbar-dark bg-dark" in data
    
    print(f"URL: {path:26} | Status: {status} | Loc: {location:15} | React: {str(is_react):5} | Legacy: {str(is_legacy_dark):5}")

