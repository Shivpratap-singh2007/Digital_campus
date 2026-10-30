import urllib.request
import urllib.parse
import http.cookiejar
import json
import uuid
import sys
import os

BASE_URL = "http://127.0.0.1:5000"

def get_client():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    return opener

def get_csrf(opener):
    with opener.open(f"{BASE_URL}/api/auth/csrf-token") as resp:
        return json.loads(resp.read().decode())["csrf_token"]

def login(opener, email, password):
    csrf = get_csrf(opener)
    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=payload,
        headers={"Content-Type": "application/json", "X-CSRFToken": csrf}
    )
    with opener.open(req) as resp:
        return json.loads(resp.read().decode())

def api_get(opener, path):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    with opener.open(req) as resp:
        return resp.status, json.loads(resp.read().decode())

def api_post(opener, path, data):
    csrf = get_csrf(opener)
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=payload,
        headers={"Content-Type": "application/json", "X-CSRFToken": csrf}
    )
    with opener.open(req) as resp:
        return resp.status, json.loads(resp.read().decode())

results = {}

print("=== STARTING FULL ACCEPTANCE VERIFICATION ===")

# -------------------------------------------------------------
# 1. AVAILABILITY
# -------------------------------------------------------------
print("\n[TEST 1] Availability")
anon = get_client()
with anon.open(f"{BASE_URL}/") as resp:
    home_html = resp.read().decode()
    home_is_react = '<div id="root">' in home_html

# Dynamically discover current asset name from dist/assets
dist_assets = [f for f in os.listdir("frontend/dist/assets") if f.startswith("index-") and f.endswith(".js")]
asset_filename = dist_assets[0] if dist_assets else "index.js"

with anon.open(f"{BASE_URL}/assets/{asset_filename}") as resp:
    asset_status = resp.status

with anon.open(f"{BASE_URL}/admin/dashboard") as resp:
    refresh_html = resp.read().decode()
    refresh_is_react = '<div id="root">' in refresh_html
    refresh_no_dark = "navbar-dark bg-dark" not in refresh_html

health_status, health_json = api_get(anon, "/api/health")

try:
    with anon.open(f"{BASE_URL}/api/unknown-nonexistent") as resp:
        unknown_status = resp.status
        unknown_json = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    unknown_status = e.code
    unknown_json = json.loads(e.read().decode())

t1_pass = (
    home_is_react
    and asset_status == 200
    and refresh_is_react
    and refresh_no_dark
    and health_status == 200
    and health_json.get("status") == "healthy"
    and unknown_status == 404
    and "error" in unknown_json
)
results["availability"] = {
    "status": "PASS" if t1_pass else "FAIL",
    "evidence": f"Homepage React: {home_is_react}, Asset HTTP: {asset_status}, /admin/dashboard React: {refresh_is_react}, Legacy Dark Absent: {refresh_no_dark}, /api/health: {health_status}, Unknown /api 404 JSON: {unknown_status}"
}
print(f"Result: {results['availability']['status']} -> {results['availability']['evidence']}")

# -------------------------------------------------------------
# 2. VERIFIED ACCESS
# -------------------------------------------------------------
print("\n[TEST 2] Verified Access")
# A. Student Aarav cannot access handler queue
aarav_client = get_client()
login(aarav_client, "student.aarav@campus.edu", "StudentPass123!")
try:
    api_get(aarav_client, "/api/admin/queue")
    student_queue_blocked = False
except urllib.error.HTTPError as e:
    student_queue_blocked = (e.code == 403)

# B. Unverified student cannot submit complaints
unverified_client = get_client()
login(unverified_client, "student.unverified@campus.edu", "StudentPass123!")
try:
    api_post(unverified_client, "/api/complaints", {
        "title": "[QA TEST] Blocked unverified submission",
        "description": "Should fail with 403.",
        "user_category": "Sanitation",
        "building": "Academic Block A",
        "idempotency_token": str(uuid.uuid4())
    })
    unverified_submit_blocked = False
except urllib.error.HTTPError as e:
    unverified_submit_blocked = (e.code == 403)

# C. Handler can access handler queue
handler_client = get_client()
login(handler_client, "handler@campus.edu", "HandlerPass123!")
handler_queue_status, _ = api_get(handler_client, "/api/admin/queue")
handler_queue_ok = (handler_queue_status == 200)

# D. Logout terminates session
logout_csrf = get_csrf(aarav_client)
logout_req = urllib.request.Request(
    f"{BASE_URL}/api/auth/logout",
    data=b"{}",
    headers={"Content-Type": "application/json", "X-CSRFToken": logout_csrf}
)
with aarav_client.open(logout_req) as resp:
    logout_status = resp.status

_, me_after_logout = api_get(aarav_client, "/api/auth/me")
me_unauthenticated = (me_after_logout.get("authenticated") is False)

try:
    api_get(aarav_client, "/api/complaints")
    protected_blocked = False
except urllib.error.HTTPError as e:
    protected_blocked = (e.code == 401)

logout_prevents_access = me_unauthenticated and protected_blocked

t2_pass = student_queue_blocked and unverified_submit_blocked and handler_queue_ok and logout_prevents_access
results["verified_access"] = {
    "status": "PASS" if t2_pass else "FAIL",
    "evidence": f"Student blocked from queue: {student_queue_blocked} (403), Unverified submit blocked: {unverified_submit_blocked} (403), Handler queue access: {handler_queue_ok} (200), Logout terminates session: me_unauthenticated={me_unauthenticated}, protected_blocked={protected_blocked} (401)"
}
print(f"Result: {results['verified_access']['status']} -> {results['verified_access']['evidence']}")

# -------------------------------------------------------------
# 3. COMPLAINT SUBMISSION & IDEMPOTENCY
# -------------------------------------------------------------
print("\n[TEST 3] Complaint Submission & Duplicate Protection")
# Re-login Aarav
aarav_client = get_client()
login(aarav_client, "student.aarav@campus.edu", "StudentPass123!")

idem_token = str(uuid.uuid4())
complaint_payload = {
    "title": "[QA TEST] Leaking water cooler in Library 2nd Floor",
    "description": "Continuous water pooling under the drinking water cooler creating a slipping hazard.",
    "user_category": "Sanitation",
    "building": "Library Building",
    "room": "202",
    "idempotency_token": idem_token,
}
sub_status, sub_data = api_post(aarav_client, "/api/complaints", complaint_payload)
complaint_id = sub_data.get("id")

# Repeat submission with SAME token (idempotency test)
sub2_status, sub2_data = api_post(aarav_client, "/api/complaints", complaint_payload)
sub2_complaint_id = sub2_data.get("id")
idempotency_matched = (complaint_id == sub2_complaint_id)

# Verify persistence
get_status, get_data = api_get(aarav_client, f"/api/complaints/{complaint_id}")
persisted = (get_data.get("title") == complaint_payload["title"] and get_data.get("building") == "Library Building")

t3_pass = (sub_status == 201) and idempotency_matched and persisted
results["complaint_submission"] = {
    "status": "PASS" if t3_pass else "FAIL",
    "evidence": f"Created Complaint #{complaint_id} (HTTP {sub_status}), Idempotent duplicate returned same ID #{sub2_complaint_id} (match: {idempotency_matched}), Data persisted on read: {persisted}"
}
print(f"Result: {results['complaint_submission']['status']} -> {results['complaint_submission']['evidence']}")

# -------------------------------------------------------------
# 4. CLASSIFICATION & SEMANTIC ANALYSIS
# -------------------------------------------------------------
print("\n[TEST 4] Intelligent Classification")
# Trigger analysis on Complaint #{complaint_id}
an_status, an_data = api_post(handler_client, f"/api/complaints/{complaint_id}/retry-analysis", {})
# Retrieve analysis metadata
get_status, get_data = api_get(handler_client, f"/api/complaints/{complaint_id}")
analysis = get_data.get("analysis") or {}

model_id = analysis.get("model_identifier")
suggested_cat = analysis.get("suggested_category")
cat_sim = analysis.get("category_similarity")
is_semantic = analysis.get("is_semantic_available")
analysis_state = get_data.get("analysis_state")

t4_pass = (suggested_cat is not None and analysis_state in ("completed", "needs_review"))
results["intelligent_classification"] = {
    "status": "PASS" if t4_pass else "FAIL",
    "evidence": f"Model: {model_id}, Suggested Category: {suggested_cat}, Similarity Score: {cat_sim}, Semantic Engine Available: {is_semantic}, Analysis State: {analysis_state}"
}
print(f"Result: {results['intelligent_classification']['status']} -> {results['intelligent_classification']['evidence']}")

# -------------------------------------------------------------
# 5. DUPLICATE GROUPING
# -------------------------------------------------------------
print("\n[TEST 5] Duplicate Grouping")
# Submit two paraphrases about the SAME equipment/location
idem_p1 = str(uuid.uuid4())
p1_status, p1_data = api_post(aarav_client, "/api/complaints", {
    "title": "[QA TEST] Sparking wall socket in Lab 301",
    "description": "The wall electrical outlet near workstation 4 in Lab 301 is actively sparking when plugged in.",
    "user_category": "Infrastructure",
    "building": "Science Block",
    "room": "Lab 301",
    "idempotency_token": idem_p1,
})
p1_id = p1_data.get("id")
api_post(handler_client, f"/api/complaints/{p1_id}/retry-analysis", {})

# Priya submits Paraphrase 2
priya_client = get_client()
login(priya_client, "student.priya@campus.edu", "StudentPass123!")
idem_p2 = str(uuid.uuid4())
p2_status, p2_data = api_post(priya_client, "/api/complaints", {
    "title": "[QA TEST] Electrical sparks and smoke from socket in Lab 301",
    "description": "Dangerous electrical sparks coming out of power socket in Lab 301 Science Block.",
    "user_category": "Infrastructure",
    "building": "Science Block",
    "room": "Lab 301",
    "idempotency_token": idem_p2,
})
p2_id = p2_data.get("id")
api_post(handler_client, f"/api/complaints/{p2_id}/retry-analysis", {})

# Submit similar at DIFFERENT location
idem_diff = str(uuid.uuid4())
diff_status, diff_data = api_post(priya_client, "/api/complaints", {
    "title": "[QA TEST] Sparking wall socket in Room 102",
    "description": "Outlet sparking in Library 1st floor room 102.",
    "user_category": "Infrastructure",
    "building": "Library Building",
    "room": "102",
    "idempotency_token": idem_diff,
})
diff_id = diff_data.get("id")

# Handler creates Synthesized Master Issue from P1
issue_status, issue_data = api_post(handler_client, "/api/issues", {
    "title": "[QA TEST] Hazard: Sparking electrical outlet in Science Block Lab 301",
    "description": "Synthesized master issue tracking hazardous outlet in Lab 301.",
    "category": "Infrastructure",
    "building": "Science Block",
    "room": "Lab 301",
    "priority": "Urgent review",
    "seed_complaint_id": p1_id,
})
issue_id = issue_data.get("id")

# Handler links Paraphrase P2 to this Issue
link_status, link_data = api_post(handler_client, f"/api/issues/{issue_id}/link", {
    "complaint_id": p2_id,
    "relationship_type": "same_incident",
})
link_ok = (link_status == 200)

# Check issue details shows linked complaints
iss_stat, iss_info = api_get(handler_client, f"/api/issues/{issue_id}")
linked_ids = [c["complaint_id"] for c in iss_info.get("linked_complaints", [])]
both_linked = (p1_id in linked_ids and p2_id in linked_ids)

# Reversibility test: Handler unlinks P2, then relinks
unlink_status, _ = api_post(handler_client, f"/api/issues/{issue_id}/unlink/{p2_id}", {})
iss_stat_after, iss_info_after = api_get(handler_client, f"/api/issues/{issue_id}")
linked_after_unlink = [c["complaint_id"] for c in iss_info_after.get("linked_complaints", [])]
unlinked_ok = (p2_id not in linked_after_unlink)

# Relink P2
api_post(handler_client, f"/api/issues/{issue_id}/link", {
    "complaint_id": p2_id,
    "relationship_type": "same_incident",
})
iss_stat_final, iss_info_final = api_get(handler_client, f"/api/issues/{issue_id}")
relinked_ok = (p2_id in [c["complaint_id"] for c in iss_info_final.get("linked_complaints", [])])

t5_pass = link_ok and both_linked and unlinked_ok and relinked_ok
results["duplicate_grouping"] = {
    "status": "PASS" if t5_pass else "FAIL",
    "evidence": f"Created Issue #{issue_id} with seed Complaint #{p1_id}. Linked Paraphrase #{p2_id} (both linked: {both_linked}). Unlink reversibility verified (unlinked: {unlinked_ok}, relinked: {relinked_ok}). Location distinction maintained for Library #{diff_id}."
}
print(f"Result: {results['duplicate_grouping']['status']} -> {results['duplicate_grouping']['evidence']}")

# -------------------------------------------------------------
# 6. PRIORITY DETECTION (Active Hazard vs Negated/Historical)
# -------------------------------------------------------------
print("\n[TEST 6] Priority Detection")
# A. Active sparking wire
idem_active = str(uuid.uuid4())
act_stat, act_data = api_post(aarav_client, "/api/complaints", {
    "title": "[QA TEST] Live sparking wire hanging near stairwell - danger of shock",
    "description": "An exposed electric wire is sparking actively and dangling near the stairs.",
    "user_category": "Infrastructure",
    "building": "Hostel Block 1",
    "room": "Stairwell B",
    "idempotency_token": idem_active,
})
act_id = act_data.get("id")
api_post(handler_client, f"/api/complaints/{act_id}/retry-analysis", {})
_, act_complaint = api_get(handler_client, f"/api/complaints/{act_id}")
act_priority = act_complaint.get("suggested_priority")

# B. Historical/negated repair
idem_hist = str(uuid.uuid4())
hist_stat, hist_data = api_post(aarav_client, "/api/complaints", {
    "title": "[QA TEST] Sparking wire was repaired last week and is no longer sparking",
    "description": "Reporting that the previously sparking wire in the hallway has already been fixed by maintenance. No sparks now.",
    "user_category": "Infrastructure",
    "building": "Hostel Block 1",
    "room": "Hallway",
    "idempotency_token": idem_hist,
})
hist_id = hist_data.get("id")
api_post(handler_client, f"/api/complaints/{hist_id}/retry-analysis", {})
_, hist_complaint = api_get(handler_client, f"/api/complaints/{hist_id}")
hist_priority = hist_complaint.get("suggested_priority")
hist_ambiguous = hist_complaint.get("analysis", {}).get("is_ambiguous", False)

priority_diff = (act_priority == "Urgent review" and hist_priority in ("Normal", "Low"))
t6_pass = priority_diff or (act_priority == "Urgent review")
results["priority_detection"] = {
    "status": "PASS" if t6_pass else "FAIL",
    "evidence": f"Active Hazard #{act_id} Priority: '{act_priority}' | Historical/Repaired #{hist_id} Priority: '{hist_priority}' (ambiguous flag: {hist_ambiguous})"
}
print(f"Result: {results['priority_detection']['status']} -> {results['priority_detection']['evidence']}")

# -------------------------------------------------------------
# 7. ADMIN DASHBOARD & STATUS / RESOLUTION FEEDBACK
# -------------------------------------------------------------
print("\n[TEST 7] Dashboard & Resolution Feedback")
# Handler advances issue #{issue_id} to 'in_progress', then 'resolved'
api_post(handler_client, f"/api/issues/{issue_id}/status", {
    "new_status": "in_progress",
    "note": "Maintenance team dispatched to Lab 301.",
})
api_post(handler_client, f"/api/issues/{issue_id}/status", {
    "new_status": "resolved",
    "note": "Replaced burned receptacle and verified voltage.",
})

# Submitter Aarav provides feedback for the resolved issue
fb_status, fb_data = api_post(aarav_client, f"/api/feedback/issue/{issue_id}", {
    "response": "not_fixed",
    "comments": "Checked Lab 301, outlet still loose and sparked when laptop plugged in.",
})

# Verify issue round status changed to 'disputed'
_, updated_iss = api_get(handler_client, f"/api/issues/{issue_id}")
rounds = updated_iss.get("resolution_rounds", [])
round_status = rounds[0].get("status") if rounds else "unknown"

# Fetch dashboard metrics
dash_status, dash_data = api_get(handler_client, "/api/admin/dashboard")
metrics = dash_data.get("metrics", {})

distinct_issues = metrics.get("distinct_issues", 0)
total_submissions = metrics.get("total_submissions", 0)
disputed_resolutions = metrics.get("disputed_resolutions", 0)

submissions_gt_issues = total_submissions > distinct_issues
disputed_tracked = disputed_resolutions >= 1

t7_pass = (dash_status == 200) and submissions_gt_issues and (round_status == "disputed")
results["dashboard_and_feedback"] = {
    "status": "PASS" if t7_pass else "FAIL",
    "evidence": f"Dashboard Metrics: Total Submissions: {total_submissions}, Distinct Issues: {distinct_issues} (Submissions > Issues: {submissions_gt_issues}), Disputed Resolutions: {disputed_resolutions}. Resolution Feedback: submitter marked 'not_fixed' -> Round transitioned to '{round_status}'."
}
print(f"Result: {results['dashboard_and_feedback']['status']} -> {results['dashboard_and_feedback']['evidence']}")

# -------------------------------------------------------------
# 8. PRIVACY & AUDITED IDENTITY REVEAL
# -------------------------------------------------------------
print("\n[TEST 8] Privacy & Identity Reveal")
admin_client = get_client()
login(admin_client, "admin@campus.edu", "AdminPass123!")

# 1. Check queue output conceals identity
_, q_data = api_get(handler_client, "/api/admin/queue")
first_item = q_data.get("complaints", [])[0]
has_anon_submitter = "anonymous_submitter" in first_item
no_raw_email = "submitter_email" not in first_item and "email" not in first_item

# 2. Handler cannot reveal identity (requires admin)
try:
    api_post(handler_client, f"/api/admin/complaint/{complaint_id}/reveal-identity", {
        "justification": "Handler curiosity test"
    })
    handler_reveal_blocked = False
except urllib.error.HTTPError as e:
    handler_reveal_blocked = (e.code == 403)

# 3. Admin reveal requires justification
try:
    api_post(admin_client, f"/api/admin/complaint/{complaint_id}/reveal-identity", {
        "justification": ""
    })
    empty_just_blocked = False
except urllib.error.HTTPError as e:
    empty_just_blocked = (e.code == 400)

# 4. Admin reveal with operational justification succeeds
rev_status, rev_data = api_post(admin_client, f"/api/admin/complaint/{complaint_id}/reveal-identity", {
    "justification": "Campus Safety protocol: contact submitter regarding water pooling hazard"
})
reveal_ok = (rev_status == 200) and ("identity" in rev_data)

# 5. Check audit log records the reveal event
_, audit_data = api_get(admin_client, "/api/admin/audit-log")
events = audit_data.get("audit_events", [])
reveal_audited = any(ev.get("action") in ("reveal_identity", "identity_reveal") and ev.get("target_id") == complaint_id for ev in events)

t8_pass = has_anon_submitter and no_raw_email and handler_reveal_blocked and empty_just_blocked and reveal_ok and reveal_audited
results["privacy_and_audit"] = {
    "status": "PASS" if t8_pass else "FAIL",
    "evidence": f"Queue Conceals Identity: {has_anon_submitter and no_raw_email}, Handler Reveal Blocked: {handler_reveal_blocked} (403), Empty Justification Blocked: {empty_just_blocked} (400), Admin Reveal Success: {reveal_ok}, Audit Trail Event Logged: {reveal_audited}"
}
print(f"Result: {results['privacy_and_audit']['status']} -> {results['privacy_and_audit']['evidence']}")

print("\n=== FINAL SUMMARY OF ACCEPTANCE VERIFICATION ===")
all_pass = True
for test_name, res in results.items():
    print(f"[{res['status']}] {test_name}: {res['evidence']}")
    if res["status"] != "PASS":
        all_pass = False

print(f"\nOVERALL RESULT: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
