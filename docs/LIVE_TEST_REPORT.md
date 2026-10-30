# CampusVoice QA & Live Deployment Unblocking Report

**Deployment URL:** https://digital-campus-sczg.onrender.com  
**Audit Date:** October 31, 2026  
**Status:** Code changes tested locally and ready for user-approved deployment.

---

## 1. Requirements Status Matrix

| # | Workflow / Requirement | Live Server (Pre-Unblock) | Local Verified (Post-Unblock) | Notes & Observed Results |
|---|------------------------|:-------------------------:|:-----------------------------:|--------------------------|
| **1** | **Availability & Direct Refresh** | **PASS** | **PASS** | Root `/`, static JS/CSS, SPA direct routes (`/dashboard`, `/tracker`, `/settings`), `/api/health`, and unknown `/api` JSON 404 all verified. |
| **2** | **Verified Access & Role Gates** | **FAIL** (SMTP refused) | **PASS** | Email domain allowlist enforced (`@campus.edu`), weak passwords rejected (HTTP 400), unverified users blocked from complaints (HTTP 403), regular users blocked from admin queue (HTTP 403), logout invalidates session (HTTP 401). |
| **3** | **Complaint Submission & Refresh** | **BLOCKED** | **PASS** | Unverified accounts rejected with HTTP 403. Verified synthetic account successfully submitted complaint (HTTP 201). Duplicate submission key returns existing ID (HTTP 200). Refreshed list confirms persistence. |
| **4** | **Classification (Semantic Model)** | **BLOCKED** | **PASS** | Lazy-loaded SentenceTransformer (`paraphrase-multilingual-MiniLM-L12-v2`). Unified `HF_HOME` cache across build and runtime. Never fakes AI output or labels fallback as AI. |
| **5** | **Duplicate & Reversible Grouping** | **BLOCKED** | **PASS** | Handler creates master Issue linking complaint (HTTP 201). Reversible unlinking (`POST /api/issues/<id>/unlink/<cid>`) tested without data loss (HTTP 200), followed by relink (HTTP 200). |
| **6** | **Priority Evaluation** | **BLOCKED** | **PASS** | Active hazard (`sparking socket`) triggers `Urgent review` (`Immediate electrical hazard with fire risk`). Historical/negated phrase (`sparking socket was fixed yesterday and no current sparks`) triggers negation rule, evaluating to `Normal` with `is_ambiguous=True`. |
| **7** | **Status Updates & History** | **BLOCKED** | **PASS** | Handler status transition to `in_progress` with mandatory operational note (HTTP 200). Linked complaint synchronized and immutable `StatusEvent` committed. |
| **8** | **Privacy Architecture & Audited Reveal**| **PARTIAL** | **PASS** | Queue response strips submitter names and emails. Handler cannot reveal identity (HTTP 403). Admin reveal with justification succeeds (HTTP 200), committing immutable `AuditEvent` without duplicate PII storage. |
| **9** | **Resolution Feedback Loop** | **BLOCKED** | **PASS** | Handler marks issue `resolved` (HTTP 200), automatically creating `ResolutionRound` #1. Linked submitter votes `not_fixed` via `POST /api/feedback/issue/<id>` (HTTP 200). Round status updates to `disputed`. |

---

## 2. Phase-by-Phase Technical Diagnosis & Solution

### Phase 1: Email Dispatcher (HTTPS REST Adapters for Render)
- **Root Cause of Live Failure:**
  Render Web Services do not provide a local SMTP daemon on `localhost:1025` (`[Errno 111] Connection refused`). On cloud hosts, outbound SMTP ports (25, 465, 587) are frequently filtered or blocked.
- **Implemented Architecture:**
  In [`app/services/email.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/email.py), implemented an HTTPS-based email adapter with zero additional third-party dependencies (using standard library `urllib.request` over TLS port 443):
  1. **Resend HTTPS REST API:** `POST https://api.resend.com/emails` via `RESEND_API_KEY`.
  2. **SendGrid HTTPS REST API:** `POST https://api.sendgrid.com/v3/mail/send` via `SENDGRID_API_KEY`.
  3. **Console Log Transport:** `EMAIL_PROVIDER=console` captures verification links in container stdout for staging/testing without external secrets.
  4. **SMTP Transport:** Fallback for traditional SMTP / local Mailpit.
- **Security & Privacy Guarantees:**
  - Token hashing with SHA-256 (`VerificationToken.hash_token`) preserved.
  - Expiration (24h), single-use invalidation, attempt limits, and CSRF protection preserved.
  - Raw verification tokens are **never** returned in API responses.
- **Sender-Domain & Recipient Restrictions:**
  - *Resend Free Tier:* By default, the testing sender `onboarding@resend.dev` can only send to the account owner's email address. To send to arbitrary college domains (`@campus.edu`, `@university.ac.in`), you must add and verify your custom domain in Resend's DNS console.
  - *SendGrid:* Requires Single Sender Verification or an authenticated domain in SendGrid's console.

### Phase 2: Synthetic Demo Accounts & Bootstrap Fixtures
- **Implemented Architecture:**
  Created dedicated module [`app/services/fixtures.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/fixtures.py) and CLI command `python -m flask campus_cli seed-fixtures`.
- **Synthetic Accounts Provisioned:**
  - `student.aarav@campus.edu` (Role: `user`, `is_verified=True`, `is_synthetic_fixture=True`)
  - `student.priya@campus.edu` (Role: `user`, `is_verified=True`, `is_synthetic_fixture=True`)
  - `handler@campus.edu` (Role: `handler`, `is_verified=True`, `is_synthetic_fixture=True`)
  - `admin@campus.edu` (Role: `admin`, `is_verified=True`, `is_synthetic_fixture=True`)
  - `student.unverified@campus.edu` (Role: `user`, `is_verified=False`, `is_synthetic_fixture=True`)
- **Safety Safeguards:**
  - **No Silent Promotion:** If an existing account has a conflicting role, the system refuses to alter the role and logs a safeguard conflict.
  - **No Password Reset on Restart:** Existing account passwords are preserved and never overwritten across container restarts.
  - **Startup Bootstrap Flag:** An idempotent bootstrap hook in [`run.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/run.py) triggers only when `BOOTSTRAP_DEMO_DATA=true` or `DEMO_MODE=true` is set.
  - **Disabling Bootstrap:** After the initial deployment, set `BOOTSTRAP_DEMO_DATA=false` in the Render dashboard to deactivate startup seeding.

### Phase 3: Real Semantic Model
- **Diagnosis:**
  Sentence Transformers model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` failed on fresh containers because `local_files_only=True` was hardcoded and model weights were not downloaded during build time.
- **Implemented Solution:**
  1. **Unified Cache Path:** Set `HF_HOME=/opt/render/project/src/.cache/huggingface` in [`render.yaml`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/render.yaml) so the build stage and runtime container share the exact same model weights.
  2. **Build Warmup Command:** Updated Render build command:
     ```bash
     pip install -r requirements.txt && python -m flask campus_cli warmup-model
     ```
  3. **Fast Offline Detection:** [`app/services/semantic.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/semantic.py) checks local cache first; if missing and offline, it fails fast in 1.5 seconds without blocking on retries.
  4. **Strict Integrity:** If model loading fails, `is_available: false` is explicitly returned with the exact load error. The system **never** fabricates similarity scores or labels keyword fallback as AI.

### Phase 4: Storage Persistence Analysis
- **Render Free Tier Storage:**
  Render Web Services on the free plan run on **ephemeral container filesystems**. Any files stored in the local working directory (`campusvoice.db` and `uploads/`) will be lost whenever the container sleeps after 15 minutes of inactivity or redeploys.
- **Persistence Recommendations:**
  1. **PostgreSQL Database:** Render offers free managed PostgreSQL instances. Setting the `DATABASE_URL` environment variable automatically connects Flask-SQLAlchemy to persistent PostgreSQL without SQLite data loss.
  2. **Persistent Disk (Paid):** Attaching a Render Persistent Disk to `/data` and configuring `SQLITE_PATH=/data/campusvoice.db` and `UPLOAD_FOLDER=/data/uploads`.

---

## 3. Exact Files Modified & Added

1. [`app/config.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/config.py):
   - Added `EMAIL_PROVIDER`, `RESEND_API_KEY`, `SENDGRID_API_KEY`.
   - Added `HF_HOME`, `ALLOW_MODEL_DOWNLOAD`.
   - Added `DEMO_MODE`, `BOOTSTRAP_DEMO_DATA`.
2. [`app/models/user.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/models/user.py):
   - Added `is_synthetic_fixture = db.Column(db.Boolean, default=False)`.
3. [`app/services/email.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/email.py):
   - Added HTTPS REST adapters for Resend and SendGrid.
   - Added console log adapter for staging/dev.
   - Added provider routing in `send_verification_email`.
4. [`app/services/fixtures.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/fixtures.py) *(New)*:
   - Implemented idempotent synthetic fixture provisioning for all 5 roles.
   - Added safe role-conflict detection and password preservation.
5. [`app/cli.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/cli.py):
   - Added `seed-fixtures` CLI command.
6. [`app/services/semantic.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/semantic.py):
   - Unified `HF_HOME` cache agreement.
   - Added thread limiting (`torch.set_num_threads(1)`) for CPU containers.
   - Added fast offline connectivity check.
7. [`run.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/run.py):
   - Added backward-compatible SQLite `ALTER TABLE` for `is_synthetic_fixture`.
   - Added conditional startup bootstrap hook when `BOOTSTRAP_DEMO_DATA=true`.
8. [`render.yaml`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/render.yaml):
   - Updated build command to include `warmup-model`.
   - Added environment variable definitions (`HF_HOME`, `EMAIL_PROVIDER`, `RESEND_API_KEY`).

---

## 4. Render Dashboard Configuration Checklist

To apply these fixes to your live Render deployment:

1. **Build & Start Settings:**
   - **Build Command:**
     ```bash
     pip install -r requirements.txt && python -m flask campus_cli warmup-model
     ```
   - **Start Command:**
     ```bash
     python run.py
     ```

2. **Environment Variables to Enter in Render Dashboard:**
   - `BOOTSTRAP_DEMO_DATA`: `true` *(set to `false` after first successful startup)*
   - `EMAIL_PROVIDER`: `resend` *(or `sendgrid` / `console`)*
   - `RESEND_API_KEY`: *(your Resend API key)*
   - `PUBLIC_BASE_URL`: `https://digital-campus-sczg.onrender.com`
   - `HF_HOME`: `/opt/render/project/src/.cache/huggingface`
   - `FIXTURE_ADMIN_PASSWORD`: *(strong admin password)*
   - `FIXTURE_HANDLER_PASSWORD`: *(strong handler password)*
   - `FIXTURE_STUDENT_A_PASSWORD`: *(strong student password)*
   - `FIXTURE_STUDENT_B_PASSWORD`: *(strong student password)*
