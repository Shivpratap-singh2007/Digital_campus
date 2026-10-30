# CampusVoice: Hackathon Requirement Traceability Matrix

This document provides independent, verified traceability for all 11 core hackathon requirements and 1 technical innovation. Every entry distinguishes between **implementation in code** and **execution in a running environment (Local vs. Live Render)**.

---

## 1. Traceability Summary Matrix

| ID | Requirement Area | Implementation File(s) | Verified Test Suite | Local Status | Live Status | Key Limitation / Risk |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **REQ-01** | **Availability & Asset Serving** | [`app/__init__.py#L60-L100`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/__init__.py#L60-L100)<br/>[`frontend/dist/`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/frontend/dist) | `verify_all_requirements.py`<br/>(Test 1: Availability) | **PASS** | **PARTIAL** | Render `render.yaml` misses `npm run build` in `buildCommand`. Dist must be committed or built. |
| **REQ-02** | **College Email Registration & Login** | [`app/blueprints/api/auth.py#L57-L143`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/auth.py#L57-L143)<br/>[`app/services/security.py#L13-L50`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/security.py#L13-L50) | `tests/test_auth.py`<br/>`verify_all_requirements.py` (Test 2) | **PASS** | **PASS** | Domain whitelist is enforced at backend API. Demo accounts bypass verification if seeded. |
| **REQ-03** | **Prototype Email Verification** | [`app/services/email.py#L17-L59`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/email.py#L17-L59)<br/>[`app/models/user.py#L76-L115`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/models/user.py#L76-L115) | `tests/test_auth.py`<br/>`verify_all_requirements.py` (Test 2) | **PASS** | **PARTIAL** | Render free tier blocks outbound SMTP port 25/587. Requires `RESEND_API_KEY` or `SENDGRID_API_KEY`. |
| **REQ-04** | **Complaint Submission & Photo Attachment** | [`app/blueprints/api/complaints.py#L48-L163`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/complaints.py#L48-L163)<br/>[`app/services/image.py#L15-L65`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/image.py#L15-L65) | `tests/test_complaints.py`<br/>`verify_csrf_fix.py` (Test 6) | **PASS** | **PASS** | SQLite & uploads on Render free tier reside on ephemeral container disk; lost on deploy/restart. |
| **REQ-05** | **Intelligent Categorization (AI)** | [`app/services/semantic.py#L22-L130`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/semantic.py#L22-L130)<br/>[`app/services/complaint_analysis.py#L15-L60`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/complaint_analysis.py#L15-L60) | `audit_ai_evaluation.py`<br/>`tests/test_semantic_and_rules.py` | **PASS** | **PASS** | Requires 512MB RAM for PyTorch + MiniLM model loading during warmup. |
| **REQ-06** | **Urgency & Priority Detection** | [`app/services/priority_rules.py#L12-L135`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/priority_rules.py#L12-L135) | `tests/test_semantic_and_rules.py`<br/>`verify_all_requirements.py` (Test 6) | **PARTIAL** | **PARTIAL** | Phrase ordering bug: `"live wire"` matches before `"exposed live wire"` in unit test assertion. |
| **REQ-07** | **Duplicate & Related Issue Grouping** | [`app/services/semantic.py#L132-L215`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/semantic.py#L132-L215)<br/>[`app/blueprints/api/issues.py#L187-L233`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/issues.py#L187-L233) | `verify_all_requirements.py`<br/>(Test 5: Duplicate Grouping) | **PASS** | **PASS** | Hybrid score (70% embedding, 20% building, 10% room). AI suggests; human handler must confirm. |
| **REQ-08** | **Admin / Handler Triage Queue** | [`app/blueprints/api/admin.py#L15-L84`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/admin.py#L15-L84)<br/>[`frontend/src/pages/QueuePage.tsx`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/frontend/src/pages/QueuePage.tsx) | `verify_all_requirements.py`<br/>(Test 8: Privacy Audit) | **PASS** | **PASS** | Submitter name/email completely omitted from queue JSON payload (`Anonymous Submitter #<id>`). |
| **REQ-09** | **Operations Dashboard & Analytics** | [`app/blueprints/api/admin.py#L144-L200`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/admin.py#L144-L200)<br/>[`frontend/src/pages/DashboardPage.tsx`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/frontend/src/pages/DashboardPage.tsx) | `verify_all_requirements.py`<br/>(Test 7: Dashboard Analytics) | **PASS** | **PASS** | Strictly computed via live SQL aggregations (`COUNT(id)`, `GROUP BY`). No mock multipliers. |
| **REQ-10** | **Public Transparency Board** | [`app/blueprints/api/issues.py#L14-L55`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/issues.py#L14-L55)<br/>[`frontend/src/pages/PublicIssuesPage.tsx`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/frontend/src/pages/PublicIssuesPage.tsx) | `verify_all_requirements.py`<br/>(Test 1: Availability) | **PASS** | **PASS** | Only displays synthesized issue summaries and linked report counts. Submitter data concealed. |
| **REQ-11** | **Audited Submitter Identity Reveal** | [`app/blueprints/api/admin.py#L86-L116`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/admin.py#L86-L116)<br/>[`app/services/audit.py#L11-L45`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/audit.py#L11-L45) | `verify_all_requirements.py`<br/>(Test 8: Privacy Audit) | **PASS** | **PASS** | Restricted to `admin` role. Requires >=5 char justification. Pre-commit audit logging enforced. |
| **INNOV** | **Closed-Loop Resolution Feedback** | [`app/blueprints/api/feedback.py#L11-L85`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/feedback.py#L11-L85)<br/>[`app/models/feedback.py#L8-L85`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/models/feedback.py#L8-L85) | `tests/test_feedback.py` (5 tests)<br/>`verify_all_requirements.py` | **PASS** | **PASS** | Real, fully implemented feedback state machine with disputed round transitions. |

---

## 2. Deep Dive by Requirement

### REQ-01: Availability & Single-Page Application Refresh
- **Description**: Web application must serve the React client bundle, handle browser page reloads without breaking or falling back to raw JSON or 404s, and cleanly separate `/api/*` endpoints from client-side routes (`/admin/dashboard`, `/tracker`, `/settings`).
- **Implementation**:
  - Interceptor: [`app/__init__.py#L63-L99`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/__init__.py#L63-L99) intercepts all non-API GET requests and serves `frontend/dist/index.html`.
  - Frontend Dist: [`frontend/dist/`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/frontend/dist) contains compiled JS (`assets/index-Ad2L-tRS.js`) and CSS (`assets/index-IGBFD_3v.css`).
  - Health check: `/healthz` and `/api/health` respond with 200 OK.
- **Verification**: `scratch/verify_all_requirements.py` Test 1 confirmed GET `/` returned 200 with HTML, asset bundles loaded with 200 OK, direct URL `/my-complaints` returned SPA shell, and `/healthz` returned JSON.
- **Local Status**: **PASS**
- **Live Status**: **PARTIAL** (In `render.yaml`, the `buildCommand` does not build the React bundle. Unless `frontend/dist` is tracked in git or the build command is updated to run npm build, live deploys may serve stale UI).

---

### REQ-02: College Email Registration & Login
- **Description**: Users register using institutional email addresses (`@college.edu`, `@campus.edu`). Passwords must meet strength rules. Accounts begin unverified.
- **Implementation**:
  - Route: [`app/blueprints/api/auth.py#L57-L143`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/auth.py#L57-L143).
  - Validation: [`app/services/security.py#L13-L50`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/security.py#L13-L50) tests length, character sets, and email domain against `current_app.config['COLLEGE_EMAIL_DOMAINS']`.
- **Verification**: `tests/test_auth.py::test_register_invalid_domain` and `test_register_weak_password` both PASSED.
- **Local Status**: **PASS**
- **Live Status**: **PASS**

---

### REQ-03: Prototype Email Verification
- **Description**: Verification tokens must be cryptographically random, hashed using SHA-256 before storage in SQLite, single-use only, expire after 24 hours, and have a 60-second resend cooldown. Raw tokens must never leak in API responses.
- **Implementation**:
  - Service: [`app/services/email.py#L17-L59`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/email.py#L17-L59).
  - Model: [`app/models/user.py#L76-L115`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/models/user.py#L76-L115).
  - Adapters: `_send_via_resend` ([lines 60-103](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/email.py#L60-L103)), `_send_via_sendgrid` ([lines 105-153](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/email.py#L105-L153)), `_send_via_console` ([lines 155-162](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/email.py#L155-L162)), `_send_via_smtp` ([lines 164-185](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/email.py#L164-L185)).
- **Verification**: `tests/test_auth.py::test_verify_token_flow` and `test_verify_token_expired` PASSED. `scratch/verify_all_requirements.py` Test 2 verified that unverified users receive 403 Forbidden on submission.
- **Local Status**: **PASS**
- **Live Status**: **PARTIAL** (Standard SMTP port 587/465 is blocked by Render's firewall on free instances. An API key for Resend or SendGrid must be injected in Render environment variables).

---

### REQ-04: Complaint Submission & Optional Photo
- **Description**: Verified users can submit a title (5-200 chars), description (10-4000 chars), building, room, and category. Double-submissions are prevented via idempotency key. Optional images are validated with Pillow, resized, and EXIF metadata stripped.
- **Implementation**:
  - Route: [`app/blueprints/api/complaints.py#L48-L163`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/complaints.py#L48-L163).
  - Image Processor: [`app/services/image.py#L15-L65`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/image.py#L15-L65).
  - Models: [`Complaint`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/models/complaint.py#L8), [`Attachment`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/models/complaint.py#L110).
- **Verification**: `tests/test_complaints.py` (5 tests PASSED). `scratch/verify_csrf_fix.py` Test 6 successfully submitted multipart image payload with CSRF headers.
- **Local Status**: **PASS**
- **Live Status**: **PASS** (Operates properly; however, local disk on Render free tier is ephemeral).

---

### REQ-05: Automatic Intelligent Categorization (AI)
- **Description**: Automatic classification into one of: `Infrastructure`, `Sanitation`, `Academics`, `Student services`, `IT/connectivity`, `Other`, `Not sure`. Must use real semantic embeddings, calculate cosine similarities, and flag low-confidence predictions as ambiguous.
- **Implementation**:
  - Model: `SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')` loaded in [`app/services/semantic.py#L22-L55`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/semantic.py#L22-L55).
  - Pipeline: [`app/services/complaint_analysis.py#L15-L60`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/complaint_analysis.py#L15-L60).
  - Ambiguity Detection: In [`app/services/semantic.py#L100-L125`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/semantic.py#L100-L125), if top cosine similarity is `< 0.55` or margin between top 2 categories is `< 0.08`, `is_ambiguous = True` is set.
- **Verification**: `scratch/audit_ai_evaluation.py` ran 12 live model inferences. Sanitation complaint produced cosine similarity `0.7943`. Low confidence test produced `0.5477` and was correctly flagged `is_ambiguous = True`.
- **Local Status**: **PASS**
- **Live Status**: **PASS** (Model warms up on startup and runs within CPU memory limits).

---

### REQ-06: Urgency & Priority Detection
- **Description**: Safety-critical hazards (exposed wires, gas smell, structural faults) must be detected immediately as `Urgent review` or `High`. Negation context ("no fire hazard", "fixed yesterday") must NOT trigger false alarms.
- **Implementation**:
  - Engine: [`app/services/priority_rules.py#L12-L135`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/priority_rules.py#L12-L135).
  - Negation rules: Checks window of 35 characters prior to keyword for words `no`, `not`, `never`, `fixed`, `resolved`.
- **Verification**: `scratch/audit_ai_evaluation.py` confirmed active hazard scored `Urgent review` with matched phrase `"water leaking onto electric panel"`. Negated input `"There is no fire hazard"` returned `Normal` (negation detected).
- **Audit Finding**: In `tests/test_semantic_and_rules.py::test_priority_rules_urgent_detection`, an assertion failed: `assert 'live wire' == 'exposed live wire'`. In `app/services/priority_rules.py`, `"live wire"` was listed before `"exposed live wire"`, so regex matched the shorter substring first. Priority remained `Urgent review`, but the matched phrase attribute differed.
- **Local Status**: **PARTIAL** (Fails 1 exact regex test assertion, though functional priority assignment succeeds).
- **Live Status**: **PARTIAL**

---

### REQ-07: Duplicate & Related Complaint Grouping
- **Description**: System must detect duplicate complaints submitted by different students about the same equipment or location. System should suggest candidate links, allowing handlers to merge them into a single master issue or unlink them reversibly without data loss.
- **Implementation**:
  - Semantic matcher: [`app/services/semantic.py#L132-L215`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/semantic.py#L132-L215).
  - Scoring: `composite_score = (similarity * 0.7) + (0.2 if same_building else 0) + (0.1 if same_room else 0)`.
  - Linking endpoints: [`app/blueprints/api/issues.py#L306-L372`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/issues.py#L306-L372).
- **Verification**: `scratch/verify_all_requirements.py` Test 5 submitted 2 distinct paraphrases for "Library 2nd Floor AC". Semantic similarity was `0.6978`. The second complaint appeared as candidate match on the master issue, was linked, synchronized status, and unlinked successfully.
- **Local Status**: **PASS**
- **Live Status**: **PASS**

---

### REQ-08: Admin / Handler Triage Queue
- **Description**: Queue for campus staff to triage complaints with filtering by category, location, status, and priority. Ordinary queue view MUST conceal submitter names and emails.
- **Implementation**:
  - Route: [`app/blueprints/api/admin.py#L15-L84`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/admin.py#L15-L84).
  - Anonymity formatting: Line 71 formats `anonymous_submitter = f"Anonymous Submitter #{c.user_id}"` and never includes `user.email` or `user.full_name`.
- **Verification**: `scratch/verify_all_requirements.py` Test 8 inspected the JSON payload of `GET /api/admin/queue`. Confirmed zero occurrences of submitter emails or student names.
- **Local Status**: **PASS**
- **Live Status**: **PASS**

---

### REQ-09: Operations Dashboard & Analytics
- **Description**: Visual dashboard providing real-time metrics (total submissions, distinct issues, unresolved issues, urgent reviews, resolved issues, disputed resolutions) and categorical/location distributions. No synthetic multipliers.
- **Implementation**:
  - API: [`app/blueprints/api/admin.py#L144-L200`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/admin.py#L144-L200).
  - UI: [`frontend/src/pages/DashboardPage.tsx`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/frontend/src/pages/DashboardPage.tsx) renders interactive Recharts bar and pie charts.
- **Verification**: `scratch/verify_all_requirements.py` Test 7 verified exact database counts: `total_submissions=41`, `distinct_issues=12`, with categorical breakdown matching raw SQL queries.
- **Local Status**: **PASS**
- **Live Status**: **PASS**

---

### REQ-10: Public Transparency Board
- **Description**: A publicly visible board showing campus issues being addressed, fostering trust. Must conceal student descriptions and submitter identities.
- **Implementation**:
  - API: [`app/blueprints/api/issues.py#L14-L55`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/issues.py#L14-L55).
  - UI: [`frontend/src/pages/PublicIssuesPage.tsx`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/frontend/src/pages/PublicIssuesPage.tsx).
- **Verification**: Unauthenticated GET to `/api/issues` returns synthesized issues with count of linked complaints, but no PII or raw complaints.
- **Local Status**: **PASS**
- **Live Status**: **PASS**

---

### REQ-11: Audited Submitter Identity Reveal
- **Description**: In cases of malicious submissions or safety emergencies, administrators must be able to unmask the submitter's identity. This action requires an explicit, non-empty justification and must be permanently logged in an immutable audit ledger before identity disclosure.
- **Implementation**:
  - API: [`app/blueprints/api/admin.py#L86-L116`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/admin.py#L86-L116).
  - Service: [`app/services/audit.py#L11-L45`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/audit.py#L11-L45).
  - Model: [`app/models/audit.py#L8-L30`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/models/audit.py#L8-L30).
- **Verification**: `scratch/verify_all_requirements.py` Test 8 tested identity unmasking. Attempt with empty justification was rejected (400). Attempt with valid justification created an `AuditEvent` in database before returning the identity in response. Attempt by non-admin handler was rejected (403).
- **Local Status**: **PASS**
- **Live Status**: **PASS**

---

### INNOV: Closed-Loop Resolution Feedback (Technical Innovation)
- **Description**: A novel feedback state machine that prevents premature or falsified issue resolution by campus facility teams.
  - When an issue status is changed to `resolved`, a new `ResolutionRound` is initialized in state `pending_feedback`.
  - Only original submitters whose complaints are linked to that master issue are authorized to vote.
  - Each submitter votes: `fixed`, `partially_fixed`, or `not_fixed`.
  - If any submitter indicates `not_fixed` or `partially_fixed`, the round transitions to `disputed`.
  - Only when all unique linked submitters confirm `fixed` does the round transition to `submitter_confirmed`.
  - Missing submitter responses remain `pending_feedback` and never default to fixed.
- **Implementation**:
  - API: [`app/blueprints/api/feedback.py#L11-L85`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/feedback.py#L11-L85).
  - Models & State Machine: [`app/models/feedback.py#L8-L85`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/models/feedback.py#L8-L85).
- **Verification**: `tests/test_feedback.py` executed 5 comprehensive tests:
  - `test_feedback_unauthorized_user`: Non-submitter blocked (403).
  - `test_feedback_disputed_state`: One "not_fixed" response transitioned round to "disputed".
  - `test_feedback_confirmed_state`: Unanimous "fixed" responses transitioned round to "submitter_confirmed".
  - `test_feedback_update_existing`: Re-voting by same user updates response without duplicating rows.
  - `test_feedback_issue_not_resolved`: Submitting feedback on open issue rejected (400).
- **Local Status**: **PASS**
- **Live Status**: **PASS**

