# CampusVoice Acceptance Verification Report

**Audit Date:** October 31, 2026  
**Target Environments:** Local Verification Server (`http://127.0.0.1:5000`) & Live Render Deployment (`https://digital-campus-sczg.onrender.com`)  
**Overall Status:** **ALL CRITICAL REQUIREMENTS VERIFIED & PASSING LOCALLY**

---

## 1. Executive Summary

A comprehensive investigation and end-to-end verification of CampusVoice was conducted to resolve the UI refresh bug (where browser refresh on `/admin/dashboard` or other routes rendered a legacy dark-navbar HTML template instead of the unified React application shell) and verify the 5 original hackathon requirements plus security, privacy, and feedback loops.

### Root Cause of the Refresh Defect
When users navigated client-side inside the React application, React Router managed route transitions in-memory (`window.history.pushState`), maintaining the desired modern visual design (Screenshot 1: white top navbar `app-navbar`, clean light theme, and bottom navigation `Home / Tracker / Settings`). However, upon pressing F5 or performing a browser refresh on `/admin/dashboard`, Werkzeug's URL routing map prioritized exact blueprint routes (e.g. `@admin_bp.route("/dashboard")` in `app/blueprints/admin/routes.py`) over the SPA wildcard fallback route `/<path:path>`. This invoked Flask's legacy server-rendered Jinja view `admin/dashboard.html` extending `base.html` (Screenshot 2: dark navbar `<nav class="navbar navbar-dark bg-dark">`).

### Implemented Solution
1. **Centralized SPA Interceptor in `app/__init__.py`:** Implemented a targeted `@app.before_request` hook (`intercept_react_spa`) that intercepts all incoming `GET` and `HEAD` requests for frontend views and returns the production React `index.html` before blueprint routing rules can trigger legacy Jinja templates.
2. **Strict Boundary Exclusions:** Preserved all `/api/*` endpoints (returning JSON 404 for unknown endpoints), static assets (`/assets/*`), health checks (`/healthz`, `/api/health`), authorized private image attachments (`/complaints/attachment/*`), and token verification endpoints.
3. **Blueprint Defense-in-Depth:** Updated legacy GET handlers in `admin`, `complaints`, `issues`, and `auth` blueprints to safely return the React bundle `index.html` whenever the build directory exists, with graceful fallback to Jinja templates if no build exists.
4. **React Route Aliases:** Configured route aliases in `frontend/src/App.tsx` (e.g. `/complaints/my-complaints`, `/issues/:id`, `/auth/login`) ensuring direct entries and bookmarks render within the modern React shell.
5. **Fresh Bundle Compilation:** Rebuilt the frontend bundle with `npm run build --prefix frontend` (Vite v5.4.21), emitting `dist/index.html` and assets.

---

## 2. Requirements Verification Matrix

| # | Requirement | Status | Evidence & Test Data |
|---|-------------|:------:|----------------------|
| **1** | **Availability & Direct Route Refresh** | **PASS** | Root `/` (HTTP 200, React root div detected); static JS asset `/assets/index-pFovCmW5.js` (HTTP 200); direct refresh on `/admin/dashboard` returns React SPA (HTTP 200, legacy `bg-dark` absent); `/dashboard`, `/tracker`, `/settings`, `/my-complaints` all return React SPA (HTTP 200); health endpoint `/api/health` returns `{"status":"healthy","service":"campusvoice"}` (HTTP 200); unknown route `/api/unknown-nonexistent` strictly returns JSON 404. |
| **2** | **Verified Access & Role Gates** | **PASS** | Regular student (`student.aarav@campus.edu`) blocked from handler operations queue `/api/admin/queue` (HTTP 403); unverified student (`student.unverified@campus.edu`) blocked from submitting complaints (HTTP 403: "Access Denied: Verified college email required"); authorized handler (`handler@campus.edu`) successfully accesses `/api/admin/queue` (HTTP 200); session logout terminates authentication: `/api/auth/me` returns `authenticated: false`, and protected calls to `/api/complaints` return HTTP 401. |
| **3** | **Complaint Submission & Persistence** | **PASS** | Verified student submitted complaint #29 `[QA TEST] Leaking water cooler in Library 2nd Floor` (HTTP 201). Duplicate submission test with identical idempotency token returned existing complaint #29 without duplicate record creation. Direct API fetch `GET /api/complaints/29` confirmed exact persistence of title, description, and building metadata. |
| **4** | **Intelligent Classification & Semantic AI** | **PASS** | Semantic model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` loaded successfully into memory. Evaluated complaint #29 with semantic cosine similarity score of `0.5936` matching category `Sanitation` (`Drinking water cooler contaminated or foul smelling`). State marked `completed`. Real PyTorch embeddings evaluated; keyword fallback was not used. |
| **5** | **Duplicate Grouping & Reversible Unlinking** | **PASS** | Submitted paraphrase 1 (complaint #30: `Sparking wall socket in Lab 301`) and paraphrase 2 (complaint #31: `Electrical sparks and smoke from socket in Lab 301`) at Science Block Lab 301. Handler created Master Issue #11 and grouped complaint #31. Semantic engine returned high cosine similarity and grouped both complaints. Reversibility verified: Handler unlinked complaint #31 (HTTP 200) and subsequently relinked it (HTTP 200) with zero data loss. Similar report at Library #32 remained distinct. |
| **6** | **Priority Detection (Active vs Historical)** | **PASS** | Active electrical hazard report (complaint #33: `Live sparking wire hanging near stairwell - danger of shock`) matched `sparking wire` and evaluated to **`Urgent review`** (`Immediate electrical hazard with fire risk`). Historical/negated report (complaint #34: `Sparking wire was repaired last week and is no longer sparking`) triggered negation/historical detection rule, evaluating to **`Normal`** with `is_ambiguous=True`. |
| **7** | **Admin Dashboard & Resolution Feedback** | **PASS** | Handler advanced Issue #11 to `in_progress` with operational note, then to `resolved` (HTTP 200), opening Resolution Round #1. Submitter Aarav submitted verified resolution feedback voting `not_fixed` (HTTP 200). Resolution round transitioned to **`disputed`**. Live dashboard metrics strictly reflected SQLite state: Total Submissions: 34, Distinct Issues: 11 (Submissions > Distinct Issues holds true), Disputed Resolutions: 4. Submissions and synthesized issues maintained separate counts. |
| **8** | **Privacy Architecture & Audited Reveal** | **PASS** | Queue response `/api/admin/queue` conceals submitter identity, returning `anonymous_submitter: Anonymous Submitter #X` and omitting email addresses. Handler role attempting identity reveal rejected (HTTP 403). Admin reveal with empty justification rejected (HTTP 400). Admin reveal with operational justification succeeded (HTTP 200), disclosing submitter details and committing an immutable `AuditEvent` (`action="reveal_identity"`, `target_id=29`). |

---

## 3. Local vs. Live Environment Details

### Local Verification Environment
- **URL:** `http://127.0.0.1:5000`
- **Application Server:** Waitress WSGI production server running on port 5000.
- **Database:** Local SQLite database (`campusvoice.db`) containing persistent records and seeded fixtures.
- **Frontend Assets:** Fresh Vite production build (`frontend/dist/assets/index-pFovCmW5.js`, `index-IGBFD_3v.css`).
- **Semantic Model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` cached in `.cache/huggingface/hub/` and executing inference on CPU.

### Live Render Deployment Status
- **URL:** `https://digital-campus-sczg.onrender.com`
- **Current Live State:** The live instance currently runs the previous deployment without the new SPA interceptor and without the HTTPS email configuration.
- **Unblocking Changes Ready for Deployment:**
  1. `app/__init__.py`: Added `intercept_react_spa` before_request hook.
  2. `app/blueprints/admin/routes.py`, `app/blueprints/complaints/routes.py`, `app/blueprints/issues/routes.py`, `app/blueprints/auth/routes.py`: Added SPA build detection and graceful fallbacks.
  3. `frontend/src/App.tsx`: Added legacy route aliases.
  4. `app/services/priority_rules.py`: Added `sparking wire`, `sparking outlet`, and `live wire` to urgent hazard phrases.
  5. `app/services/email.py`: HTTPS adapters for Resend and SendGrid.
  6. `frontend/dist`: Pre-compiled production bundle ready for serving.

---

## 4. CSRF & Session Security Verification

### Diagnosis of Live Error `The CSRF session token is missing.`
The live error occurred due to three compound factors in session and CSRF handling:
1. **Unstable `SECRET_KEY` on Deployed Instances:** If `SECRET_KEY` was not configured in Render environment variables, `app/config.py` generated an ephemeral random hex secret at module load (`secrets.token_hex(32)`). In multi-worker processes or on container restart, tokens and cookies signed by one worker could not be validated by another worker, causing Flask to discard the session cookie as invalid signature and present an empty session `{}`. When the incoming request submitted `X-CSRFToken`, Flask-WTF raised `CSRFError("The CSRF session token is missing.")`.
2. **Missing `Cache-Control: no-store` on CSRF Endpoint:** The `/api/auth/csrf-token` endpoint lacked explicit anti-caching headers. If the browser or a shared proxy served a cached response, the frontend received a token string without establishing the required `session` cookie.
3. **Frontend Token Timing & Invalidation:** The frontend lacked proactive CSRF bootstrapping on login/register page load and did not clear tokens on logout/auth state transitions.

### Implemented Fixes
1. **Stable Secret Key:** Added `_resolve_secret_key()` in [`app/config.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/config.py) that reads `SECRET_KEY` from the environment, falling back to a persistent local `.secret_key` file so all workers share the exact same key.
2. **Dynamic Cookie Security:** Updated `SESSION_COOKIE_SECURE` to automatically enable on Render/HTTPS while allowing local HTTP development.
3. **Dedicated CSRF Endpoints:** Registered `/api/auth/csrf` (and alias `/api/auth/csrf-token`) in [`app/blueprints/api/auth.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/auth.py), explicitly marking `session.modified = True` to guarantee `Set-Cookie` generation, and setting `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`.
4. **Structured Error Handler:** Added `@app.errorhandler(CSRFError)` in [`app/__init__.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/__init__.py) returning clean JSON (`code: "CSRF_ERROR"`).
5. **Centralized Frontend Client:** Updated [`frontend/src/api/client.ts`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/frontend/src/api/client.ts) to manage in-memory tokens, deduplicate concurrent bootstrap requests, omit `Content-Type` for `FormData`, invalidate tokens on logout, and retry at most once when explicitly rejected by CSRF middleware. Proactively bootstraps CSRF on login/register view mounts.

### CSRF Verification Matrix (Active Protection Enabled)

| # | CSRF Acceptance Test | Status | Evidence & Test Data |
|---|----------------------|:------:|----------------------|
| **C1** | **Fresh session -> fetch CSRF -> valid login** | **PASS** | `GET /api/auth/csrf` returns `Cache-Control: no-store...`, stores session cookie in cookiejar. `POST /api/auth/login` with token + cookie succeeds (HTTP 200) and authenticates `admin@campus.edu`. |
| **C2** | **Missing CSRF header is rejected** | **PASS** | `POST /api/auth/login` with session cookie but omitted `X-CSRFToken` header rejected with HTTP 400 (`code: "CSRF_ERROR"`, `message: "The CSRF token is missing."`). |
| **C3** | **Token without matching session is rejected** | **PASS** | `POST /api/auth/login` with token header but omitted/mismatched session cookie rejected with HTTP 400 (`code: "CSRF_ERROR"`, `message: "The CSRF session token is missing."`). |
| **C4** | **Incorrect password returns 401 (not CSRF error)** | **PASS** | Valid CSRF token and session provided with bad password returns HTTP 401 (`"Invalid email address or password."`). CSRF layer passed cleanly; credentials correctly failed. |
| **C5** | **Logout -> fresh CSRF -> login works again** | **PASS** | Session logged out (HTTP 200), verified unauthenticated (`/api/auth/me` returns `false`). Fresh CSRF token requested from `/api/auth/csrf` and re-login succeeds (HTTP 200). |
| **C6** | **Multipart complaint upload with CSRF** | **PASS** | Multipart upload with image attachment and `X-CSRFToken` header succeeds (HTTP 201), storing Complaint #35 with verified image attachment. |
| **C7** | **Role permissions remain strictly enforced** | **PASS** | Student blocked from handler queue (HTTP 403), handler accesses queue (HTTP 200), unverified student blocked from submitting complaints (HTTP 403). |

---

## 5. Verification & Testing Instructions

To reproduce all acceptance checks on the local verification server:

### 1. Run Automated Acceptance Suite
```powershell
.\.venv\Scripts\python.exe scratch\verify_all_requirements.py
```
Expected output:
```
=== FINAL SUMMARY OF ACCEPTANCE VERIFICATION ===
[PASS] availability
[PASS] verified_access
[PASS] complaint_submission
[PASS] intelligent_classification
[PASS] duplicate_grouping
[PASS] priority_detection
[PASS] dashboard_and_feedback
[PASS] privacy_and_audit
OVERALL RESULT: ALL TESTS PASSED
```

### 2. Run CSRF Security Verification Suite
```powershell
.\.venv\Scripts\python.exe scratch\verify_csrf_fix.py
```
Expected output:
```
OVERALL RESULT: ALL 7 CSRF ACCEPTANCE TESTS PASSED
```

### 3. Verify Frontend SPA Refresh in Browser
1. Start server (if not already running):
   ```powershell
   .\.venv\Scripts\python.exe run.py
   ```
2. Open `http://localhost:5000/login` in your browser.
3. Log in with handler credentials:
   - **Email:** `handler@campus.edu`
   - **Password:** `HandlerPass123!`
4. Navigate to `/admin/dashboard` (Home icon) or `/admin/queue` (Tracker icon).
5. Press **F5** or click the browser Refresh button.
6. **Verified Result:** The page stays within the modern white-header layout (`app-navbar`), with cards and bottom navigation bar intact. The unwanted legacy dark navbar (`navbar-dark bg-dark`) never appears.

---

## 6. Deployment Next Steps (Awaiting User Approval)

In accordance with safety directives, **no code changes or git commits have been pushed to Render automatically**. When approved, deploy using the following steps:

1. Commit changes to git:
   ```bash
   git add app/ frontend/ docs/ .gitignore
   git commit -m "Fix CSRF session validation bug, SPA refresh routing, and verify acceptance"
   git push origin main
   ```
2. In the Render Dashboard (`https://dashboard.render.com`):
   - **Root Directory:** `.` (or empty)
   - **Build Command:** `pip install -r requirements.txt && npm install --prefix frontend && npm run build --prefix frontend`
   - **Start Command:** `python run.py` (Waitress production server, bound to `0.0.0.0:$PORT`)
   - **Environment Variables to set in Render Dashboard:**
     - `SECRET_KEY`: *(Set a persistent random 64-character hex string; critical for multi-worker and restart session stability)*
     - `SESSION_COOKIE_SECURE`: `true` (enforces HTTPS cookie flag on Render)
     - `PORT`: `5000` (automatically provided by Render)
     - `DEMO_MODE`: `true`
     - `BOOTSTRAP_DEMO_DATA`: `true` (idempotent startup seed)
     - `EMAIL_PROVIDER`: `resend` (or `sendgrid` / `console`)
     - `RESEND_API_KEY`: *(User-provided secret)*

