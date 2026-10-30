import sys
import os
sys.path.insert(0, os.path.abspath("."))

from app import create_app
from app.models.user import User
from flask_login import login_user

app = create_app()

with app.test_request_context():
    admin = User.query.filter_by(email="admin@campus.edu").first()

client = app.test_client()

# Set up authenticated session using test_request_context / session_transaction
with client.session_transaction() as sess:
    sess['_user_id'] = str(admin.id)
    sess['_fresh'] = True

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
]

print("\n--- Direct GET Requests (When Authenticated as Admin) ---")
for path in urls_to_test:
    resp = client.get(path, follow_redirects=False)
    status = resp.status_code
    location = resp.headers.get("Location", "")
    content_type = resp.headers.get("Content-Type", "")
    data = resp.get_data(as_text=True)
    is_react = '<div id="root">' in data
    is_legacy_dark = "navbar-dark bg-dark" in data
    
    print(f"URL: {path:22} | Status: {status} | Loc: {location:20} | React: {str(is_react):5} | Legacy Dark: {str(is_legacy_dark):5}")
    if is_legacy_dark:
        first_lines = [l.strip() for l in data.splitlines() if "<title>" in l or "navbar" in l][:2]
        print(f"   -> Legacy snippet: {first_lines}")
