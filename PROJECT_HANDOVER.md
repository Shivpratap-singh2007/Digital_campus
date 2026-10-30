# CampusVoice: Evidence-Based Project Handover & Technical Audit

---

## 1. Project Purpose

### Problem Statement & Scope
Campus facility management and maintenance in universities frequently suffer from three structural breakdowns:
1. **Scattered & Unstructured Reporting**: Students, faculty, and staff submit complaints through fragmented channels (informal WhatsApp groups, hallway verbal mentions, disparate emails) that lack categorization, location tracking, or status history.
2. **Premature Administrative Ticket Closure**: Facility teams mark tickets "resolved" without independent verification from submitters, leading to recurrent breakdowns and lack of trust.
3. **Retaliation Risk & Duplication**: Students hesitate to report dormitory or academic safety hazards when their names and contact details are publicly visible or shared with operational maintenance workers. Furthermore, identical issues generate duplicate work tickets without grouping.

*(Note: The original hackathon problem statement prompt requires a centralized web platform for verified university members to submit complaints/suggestions, automatically categorize them, detect duplicates and urgent issues, provide an administrative dashboard, and track resolution).*

### User Personas & Target Audience
- **Students & Faculty (`role = "user"`)**: Authenticated members from allowlisted college domains (`@campus.edu`, `@university.ac.in`) who submit complaints/suggestions with optional photos, track status changes, and verify whether repairs were actually fixed.
- **Operations Handlers (`role = "handler"`)**: Campus maintenance and facility managers who triage anonymous queues, review AI category and priority suggestions, group related reports into master operational issues, update repair status, and issue resolution notes.
- **Identity-Authorized Administrators (`role = "admin"`)**: Campus safety and administrative leadership with executive dashboard visibility, access to audit ledgers, and restricted authority to unmask submitter identities for documented emergency/disciplinary reasons.
- **Public Campus Community**: Unauthenticated users viewing approved, synthesized issue summaries on the transparency board without submitter details.

### Requirement Scope vs. Additional Contributions
- **Baseline Requirements**: College-email verification, complaint submission with image upload, automated category classification, urgency detection, duplicate grouping into master issues, handler triage queue, public issue board, and dashboard metrics.
- **Architectural Contributions (Beyond Baseline)**:
  - **Closed-Loop Submitter Resolution Feedback**: Multi-round verification state machine where issues cannot reach `submitter_confirmed` status without unanimous submitter approval; a single `not_fixed` response triggers a `disputed` state.
  - **Identity-Restricted Privacy with Pre-Commit Audit Ledger**: Ordinary queues display submitters as `Anonymous Submitter #<id>`. Administrators must commit a non-empty justification to an immutable `AuditEvent` table before unmasking.
  - **Explainable Ambiguity Handling**: Semantic similarity below `0.55` is explicitly flagged `is_ambiguous = True` rather than forcing false confidence.

---

## 2. Actual Tech Stack

### Technology Inventory
All versions verified from package manifests ([`frontend/package.json`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/frontend/package.json), [`requirements.txt`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/requirements.txt)) and the active environment runtime:

| Layer | Component | Version | Specification / Details |
| :--- | :--- | :---: | :--- |
| **Frontend Framework** | React | `18.3.1` | Single Page Application (SPA) with TypeScript |
| **Frontend Runtime** | React DOM | `18.3.1` | Concurrent root DOM mounting |
| **Client Routing** | React Router DOM | `6.23.1` | Declarative client-side routing with role-based guards |
| **UI Components** | Bootstrap | `5.3.3` | Responsive layout, grid system, and utility classes |
| **UI Icons** | Bootstrap Icons | `1.11.3` | Vector icon font bundled locally in build |
| **Data Visualization** | Recharts | `2.12.7` | SVG-based bar and pie charts for dashboard analytics |
| **Frontend Build** | Vite & TypeScript | `5.4.21` / `5.4.5` | Bundles production assets into `frontend/dist/` |
| **Backend Framework** | Flask | `3.1.3` | Python WSGI application factory & Blueprints |
| **ORM & Database** | Flask-SQLAlchemy / SQLAlchemy | `3.1.1` / `2.1.6` | Relational ORM supporting SQLite and PostgreSQL |
| **Database Engine** | SQLite (default) | `3.x` | File-based `campusvoice.db` (ephemeral on free hosting) |
| **Authentication** | Flask-Login | `0.6.3` | Session-based authentication with user loader |
| **CSRF Defense** | Flask-WTF | `1.3.0` | Session-bound cryptographic CSRF protection |
| **WSGI Server** | Waitress | `3.0.2` | Production multi-threaded WSGI server (`threads=4`) |
| **Image Processing** | Pillow (PIL) | `13.0.0` | Binary header inspection, EXIF stripping, resizing |
| **AI / NLP Model** | `sentence-transformers` | `6.2.0` | Dense vector text embeddings (`dim=384`) |
| **Deep Learning** | PyTorch (CPU) | `2.15.0` | CPU tensor operations for cosine similarity calculation |
| **Numerical Engine** | NumPy | `2.4.6` | Vector array math for centroid representations |
| **Test Framework** | Pytest | `9.2.0` | Automated test suite (25 test cases) |

### AI Model Loading & Storage Path
- **Model Name**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Model Size**: ~479 MB total weights on disk.
- **Cache Location**: Local filesystem under `.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2/` or configured via `HF_HOME`.
- **Loading Behavior**: [`app/services/semantic.py#L123-L149`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/semantic.py#L123-L149) attempts local loading first (`local_files_only=True`). If unavailable, checks network reachability before attempting download. Skips downloading during unit tests (`TESTING=True`).

### Hosting, Email & Storage
- **Hosting Target**: Render Web Service (Free Tier, Linux x86_64 container).
- **Email Service**: Configurable transport adapter supporting HTTPS REST APIs (**Resend** or **SendGrid**), console output logging, or standard SMTP fallback.
- **Upload Storage**: Local filesystem directory `uploads/` (or `instance/uploads/`), located outside public static assets.

---

## 3. Repository Map

```
Digital_campus/
│
├── app/                                 # Flask Application Core
│   ├── __init__.py                      # Application factory (create_app), extensions, SPA fallback
│   ├── config.py                        # Environment & database configuration (Config, TestingConfig)
│   ├── extensions.py                    # Initialized db, login_manager, csrf instances
│   ├── cli.py                           # CLI commands (create-admin, create-handler, seed-fixtures)
│   ├── forms.py                         # Legacy WTForms declarations
│   │
│   ├── blueprints/                      # Modular Architecture Routes
│   │   ├── api/                         # Active JSON REST API tier (/api prefix)
│   │   │   ├── __init__.py              # API blueprint initialization
│   │   │   ├── admin.py                 # Queue, dashboard metrics, reveal-identity, audit-log
│   │   │   ├── auth.py                  # CSRF bootstrap, login, register, verify, logout, me
│   │   │   ├── complaints.py            # Submissions, analysis trigger, details, attachment serve
│   │   │   ├── feedback.py              # Resolution feedback submission & round re-evaluation
│   │   │   └── issues.py                # Public issue list, handler master issue, link/unlink, status
│   │   ├── admin/                       # Legacy server-rendered admin views
│   │   ├── auth/                        # Legacy server-rendered auth forms
│   │   ├── complaints/                  # Legacy server-rendered complaint templates
│   │   ├── feedback/                    # Legacy server-rendered feedback routes
│   │   ├── issues/                      # Legacy server-rendered issue templates
│   │   └── main/                        # SPA root and static asset fallback routes
│   │
│   ├── models/                          # SQLAlchemy Relational Models (11 Tables)
│   │   ├── user.py                      # User, VerificationToken
│   │   ├── complaint.py                 # Complaint, Attachment, AnalysisResult
│   │   ├── issue.py                     # Issue, IssueComplaintLink, StatusEvent
│   │   ├── feedback.py                  # ResolutionRound, ResolutionFeedback
│   │   └── audit.py                     # AuditEvent (immutable admin access ledger)
│   │
│   ├── services/                        # Business Logic & Algorithms
│   │   ├── audit.py                     # Audited identity reveal business logic
│   │   ├── complaint_analysis.py        # Coordinating pipeline between NLP & rule engines
│   │   ├── email.py                     # Resend/SendGrid HTTPS mailer & SHA-256 token hashing
│   │   ├── fixtures.py                  # Idempotent synthetic demo data provisioning
│   │   ├── image.py                     # Pillow binary validation, EXIF stripping, resizing
│   │   ├── priority_rules.py            # Versioned regex hazard matching with negation handling
│   │   ├── rate_limiter.py              # Sliding-window IP/user rate limiter
│   │   ├── security.py                  # Text sanitization, password complexity, RBAC decorators
│   │   └── semantic.py                  # SentenceTransformer loader & cosine centroid matcher
│   │
│   └── templates/                       # Legacy Jinja2 server templates (kept for fallback)
│
├── frontend/                            # React 18 Single Page Application
│   ├── dist/                            # Compiled production bundle served by Flask
│   │   ├── index.html                   # HTML entrypoint
│   │   └── assets/                      # Bundled JS and CSS files
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts                # Axios instance with CSRF interceptor & credentials
│   │   ├── components/                  # Navbar.tsx, BottomNav.tsx, StatusBadge.tsx
│   │   ├── context/
│   │   │   └── AuthContext.tsx          # Global authentication state & session bootstrap
│   │   ├── pages/                       # 13 Application views:
│   │   │   ├── HomePage.tsx             # Concise hero, stats widget, feature cards, public board
│   │   │   ├── LoginPage.tsx            # Login form with authorized access notice
│   │   │   ├── RegisterPage.tsx         # Domain-restricted registration form
│   │   │   ├── VerifyEmailPage.tsx      # Email verification token entry & resend interface
│   │   │   ├── MyComplaintsPage.tsx     # Student complaint tracker
│   │   │   ├── NewComplaintPage.tsx     # Complaint submission with photo upload
│   │   │   ├── ComplaintDetailPage.tsx  # Detailed complaint status & resolution feedback
│   │   │   ├── QueuePage.tsx            # Anonymous handler triage queue with reveal modal
│   │   │   ├── CreateIssuePage.tsx      # Master operational issue creator
│   │   │   ├── IssueDetailPage.tsx      # Issue management with candidate linking & unlinking
│   │   │   ├── DashboardPage.tsx        # Recharts analytics dashboard
│   │   │   ├── AuditLogPage.tsx         # Immutable administrator audit history viewer
│   │   │   ├── PublicIssuesPage.tsx     # Public synthesized issues board
│   │   │   └── SettingsPage.tsx         # User profile and session settings
│   │   ├── App.tsx                      # Route declarations & ProtectedRoute guards
│   │   ├── index.css                    # Design tokens and custom UI styling
│   │   └── main.tsx                     # DOM mounting
│   ├── package.json                     # NPM dependencies and scripts
│   └── vite.config.ts                   # Vite bundler configuration
│
├── tests/                               # Automated Test Suite (25 Tests)
│   ├── conftest.py                      # Isolated SQLite in-memory test fixtures
│   ├── test_auth.py                     # Auth, domain checks, token hashing
│   ├── test_complaints.py               # Submission, idempotency, attachments
│   ├── test_issues_and_feedback.py      # Issue linking, status sync, feedback states
│   ├── test_privacy_and_audit.py        # Queue anonymity, audited unmasking
│   ├── test_security.py                 # IDOR checks, rate limiting, sanitization
│   └── test_semantic_and_rules.py       # Embeddings, centroids, priority rules
│
├── docs/                                # Technical Documentation & Audit Reports
│   └── audit/                           # Formal matrices, test results, and architecture guides
│
├── requirements.txt                     # Backend Python dependencies
├── run.py                               # Production Waitress startup entrypoint
├── render.yaml                          # Render cloud deployment blueprint
└── Procfile                             # Process runner declaration (`web: python run.py`)
```

---

## 4. User Roles and Permissions

### Role Definitions & Hierarchy
User roles are persisted as an enumerated string in `users.role`:

| Role Name | Scope / Target User | Identification Flag in Code | Default Source |
| :--- | :--- | :--- | :--- |
| **`"user"`** | Students, Faculty, Staff | `current_user.is_authenticated` | Set automatically on self-registration |
| **`"handler"`** | Maintenance Staff, Facilities | `current_user.is_handler` (True for handler & admin) | CLI `create-handler` or synthetic fixture |
| **`"admin"`** | Safety Directors, Operations Admin | `current_user.is_admin` | CLI `create-admin` or synthetic fixture |

### Access Control Matrix

| Capability / Action | Endpoint / Service | User (`user`) | Handler (`handler`) | Admin (`admin`) | Unauthenticated |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **View Homepage & Public Board** | `GET /api/issues` | Allowed | Allowed | Allowed | Allowed |
| **Self-Registration** | `POST /api/auth/register` | Allowed | Allowed | Allowed | Allowed (College domain only) |
| **Submit Complaint / Suggestion** | `POST /api/complaints` | Allowed (Verified only) | Allowed | Allowed | Blocked (`401`) |
| **Upload Photo Attachment** | `POST /api/complaints` | Allowed (Verified only) | Allowed | Allowed | Blocked (`401`) |
| **View Own Complaints** | `GET /api/complaints` | Allowed (Self only) | Allowed (Self only) | Allowed (Self only) | Blocked (`401`) |
| **Download Attachment** | `GET /api/complaints/attachment/<f>` | Allowed (Owner only) | Allowed | Allowed | Blocked (`401/403`) |
| **Submit Resolution Feedback** | `POST /api/feedback/issue/<id>` | Allowed (Original submitter only) | Allowed (If submitter) | Allowed (If submitter) | Blocked (`401/403`) |
| **Access Triage Queue** | `GET /api/admin/queue` | Blocked (`403`) | Allowed (Anonymous view) | Allowed (Anonymous view) | Blocked (`401`) |
| **Create Master Issue** | `POST /api/issues` | Blocked (`403`) | Allowed | Allowed | Blocked (`401`) |
| **Link / Unlink Complaints** | `POST /api/issues/<id>/link` | Blocked (`403`) | Allowed | Allowed | Blocked (`401`) |
| **Update Issue Status** | `POST /api/issues/<id>/status` | Blocked (`403`) | Allowed (Requires note >=5 chars) | Allowed | Blocked (`401`) |
| **View Operations Dashboard** | `GET /api/admin/dashboard` | Blocked (`403`) | Allowed | Allowed | Blocked (`401`) |
| **Unmask Submitter Identity** | `POST /api/admin/complaint/<id>/reveal-identity` | Blocked (`403`) | Blocked (`403`) | Allowed (Mandatory reason) | Blocked (`401`) |
| **View Audit Log** | `GET /api/admin/audit-log` | Blocked (`403`) | Blocked (`403`) | Allowed | Blocked (`401`) |

### Identity Reveal & Audit Implementation
- **Strict Authorization**: Only accounts with `role == "admin"` pass `@admin_required`. Handlers attempting to reveal identity receive `HTTP 403 Forbidden`.
- **Mandatory Justification**: Requires a non-empty string of at least 5 characters explaining the operational necessity.
- **Pre-Commit Enforcement**: In [`app/services/audit.py#L30-L45`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/audit.py#L30-L45), an `AuditEvent` record is written and committed to the database **before** the submitter's identity is retrieved and returned. If the audit insert transaction fails, the request is aborted immediately without exposing user details.
- **Audit Data Integrity**: The audit log stores `actor_id`, `target_id`, `justification`, `ip_address`, and `created_at`, but intentionally avoids redundant copies of submitter PII.

---

## 5. Feature Status Table

| Feature | Implementing Files & Functions | Database Entities | Test / Evidence | Status | Remaining Gap / Limitation |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Registration & Verification** | [`app/blueprints/api/auth.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/auth.py)<br/>[`app/services/email.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/email.py) | `User`<br/>`VerificationToken` | `tests/test_auth.py` (5 tests passed)<br/>`scratch/verify_auth_isolated.py` | **VERIFIED WORKING** | SMTP ports blocked on Render free tier; requires HTTPS mailer secret (`RESEND_API_KEY`). |
| **Login / Logout & CSRF** | [`app/blueprints/api/auth.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/auth.py)<br/>[`frontend/src/api/client.ts`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/frontend/src/api/client.ts) | `User` | `scratch/verify_csrf_fix.py` (7 tests passed)<br/>`scratch/verify_auth_isolated.py` | **VERIFIED WORKING** | Ephemeral container restarts reset secret unless `SECRET_KEY` is set in dashboard. |
| **Complaint & Suggestion Submission** | [`app/blueprints/api/complaints.py#create_complaint`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/complaints.py) | `Complaint`<br/>`StatusEvent` | `tests/test_complaints.py` (3 tests passed)<br/>`scratch/verify_all_requirements.py` | **VERIFIED WORKING** | None. Enforces verified email, idempotency token, and length constraints. |
| **Image Upload & Access** | [`app/services/image.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/image.py)<br/>[`app/blueprints/api/complaints.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/complaints.py) | `Attachment` | `tests/test_complaints.py::test_image_validation...`<br/>`scratch/verify_csrf_fix.py` (Test 6) | **VERIFIED WORKING** | Local disk on Render free tier is ephemeral; uploaded images lost on redeploy. |
| **Category Classification (AI)** | [`app/services/semantic.py#suggest_category`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/semantic.py)<br/>[`app/services/complaint_analysis.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/complaint_analysis.py) | `AnalysisResult` | `scratch/audit_ai_evaluation.py` (12 live inferences evaluated) | **VERIFIED WORKING** | Requires 512MB RAM for PyTorch model in memory. Fallback handles offline state. |
| **Similar-Report Retrieval** | [`app/services/semantic.py#find_related_complaints`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/semantic.py) | `AnalysisResult`<br/>`Complaint` | `scratch/verify_all_requirements.py` (Test 5: AC Paraphrases scored `0.6978`) | **VERIFIED WORKING** | Ranks top 5 candidates. Human handler must confirm link. |
| **Grouping & Ungrouping** | [`app/blueprints/api/issues.py#link_complaint`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/issues.py)<br/>[`#unlink_complaint`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/issues.py) | `IssueComplaintLink`<br/>`StatusEvent` | `tests/test_issues_and_feedback.py::test_issue_creation...` | **VERIFIED WORKING** | Reversible; unlinking restores complaint status to `under_review` without data loss. |
| **Priority & Urgency Detection** | [`app/services/priority_rules.py#evaluate_priority`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/priority_rules.py) | `AnalysisResult`<br/>`Complaint` | `tests/test_semantic_and_rules.py` (4 tests passed) | **VERIFIED WORKING** | Deterministic regex rules with negation checking (e.g. "no fire hazard"). |
| **Status History & Resolution** | [`app/blueprints/api/issues.py#update_status`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/issues.py) | `StatusEvent`<br/>`Issue` | `tests/test_issues_and_feedback.py` (Passed) | **VERIFIED WORKING** | Status changes require non-empty operational note (>=5 chars) logged to history. |
| **Submitter Resolution Feedback** | [`app/blueprints/api/feedback.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/feedback.py)<br/>[`app/models/feedback.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/models/feedback.py) | `ResolutionRound`<br/>`ResolutionFeedback` | `tests/test_issues_and_feedback.py::test_verified_resolution...` (5 assertions passed) | **VERIFIED WORKING** | Real multi-round state machine. Single `not_fixed` marks round `disputed`. |
| **Identity Protection & Audit** | [`app/services/audit.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/audit.py)<br/>[`app/blueprints/api/admin.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/admin.py) | `AuditEvent` | `tests/test_privacy_and_audit.py` (2 tests passed)<br/>`scratch/verify_auth_isolated.py` | **VERIFIED WORKING** | Ordinary queue replaces submitter with `Anonymous Submitter #<id>`. Reveal requires reason. |
| **Dashboard Counts & Trends** | [`app/blueprints/api/admin.py#admin_dashboard`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/blueprints/api/admin.py) | `Complaint`<br/>`Issue`<br/>`ResolutionRound` | `scratch/verify_all_requirements.py` (Test 7 verified against raw SQL) | **VERIFIED WORKING** | Strictly calculated from live SQLite database records (`COUNT`, `GROUP BY`). No mock multipliers. |
| **Recurrence Linking** | [`app/services/semantic.py#L182-L210`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/semantic.py#L182-L210)<br/>[`frontend/src/pages/IssueDetailPage.tsx`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/frontend/src/pages/IssueDetailPage.tsx) | `Issue`<br/>`AnalysisResult` | Evaluated in candidate matcher; renders badge when matched issue was resolved | **VERIFIED WORKING** | Flags candidates as possible recurrence if previous linked issue was `resolved`. |
| **AI Complaint Interviewer** | None | None | None | **MISSING** | Conceptual feature not implemented in codebase. |
| **Admin Evidence Copilot** | None | None | None | **MISSING** | Conceptual feature not implemented in codebase. |

---

## 6. AI Reality Check

### What Actually Uses an AI Model?
- **Category Suggestion**: [`app/services/semantic.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/semantic.py) uses `SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')` to convert complaint text (`title + " " + description`) into a 384-dimensional dense vector embedding. It computes cosine similarities against precomputed centroid vectors representing each category (`Infrastructure`, `Sanitation`, `Academics`, `Student services`, `IT/connectivity`, `Other`).
- **Candidate Duplicate Matching**: Computes cosine similarity between complaint embeddings to score similar complaints (`composite_score = sim * 0.7 + location_boost`).

### What Is Strictly Rule-Based?
- **Priority & Urgency Detection**: Handled exclusively by deterministic regex keyword and phrase lists in [`app/services/priority_rules.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/priority_rules.py). It detects hazards (e.g. `exposed live wire`, `gas leak`, `sparking socket`).
- **Negation & History Parsing**: Simple regex pattern window check (preceding 35 characters) for negation terms (`no`, `not`, `never`, `fixed`, `was already`). If detected, prevents `Urgent review` classification and flags `is_ambiguous = True`.

### Configured vs. Available Model
- **Configured**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- **Availability**: Weights are present locally on disk in `.cache/huggingface/hub/`. In offline environments or test mode, the system catches import/download exceptions and falls back gracefully with `is_available = False`, logging the error without crashing.

### Language Capabilities & Testing Reality
- **Multilingual Support**: The underlying MiniLM-L12-v2 model supports 50+ languages natively.
- **Evidence Reality**: There are **zero test cases in the test suite evaluating Hindi, Hinglish, or regional dialects**. English is the only evaluated language in automated tests.

### Score Calibration
- **No Probability Claims**: The system explicitly does not claim similarity is a probability. In [`app/services/semantic.py#L250`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/semantic.py#L250), the output explanation explicitly injects:
  > *"Note: Similarity is not a calibrated confidence percentage."*
- **Ambiguity Boundary**: An embedding similarity score `< 0.55` or margin between top two categories `< 0.08` automatically marks the prediction `is_ambiguous = True` for human handler confirmation.

---

## 7. Database and Deployment

### Persistence Architecture
- **Configured Engine**: SQLite by default (`campusvoice.db`), resolved identically by web and CLI:
  ```python
  SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'campusvoice.db'}"
  ```
- **Configuration Parity**: Both web runtime ([`app/config.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/config.py)) and CLI commands ([`app/cli.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/cli.py)) import the exact same `Config` class and application factory.
- **Cloud Persistence Reality**: On the Render Free Tier, the container filesystem is **ephemeral**. Any container restart, spin-down due to inactivity (after 15 minutes), or commit redeployment wipes `campusvoice.db` and the `uploads/` directory. Persistent storage requires attaching a persistent volume or configuring an external PostgreSQL database via `DATABASE_URL`.

### Migration & Provisioning Strategy
- **Schema Initialization**: `db.create_all()` is executed safely on startup in `run.py` and `create_app()`. It creates missing tables without dropping or altering existing records.
- **Fixture Provisioning**: Idempotent headless bootstrap triggers on startup only when `BOOTSTRAP_DEMO_DATA=true` or `DEMO_MODE=true` is set. If accounts already exist, passwords and roles are left untouched.
- **Role Conflicts**: The provisioning service refuses to alter roles silently if an existing account conflicts with the requested fixture role.

### Required Environment Variable Names (Secrets Omitted)
- `SECRET_KEY` (Flask session and CSRF signing key)
- `DATABASE_URL` (Optional PostgreSQL connection string for persistence)
- `SQLITE_PATH` (Optional custom SQLite file path)
- `BOOTSTRAP_DEMO_DATA` (`true` to enable idempotent fixture creation on boot)
- `FIXTURE_ADMIN_EMAIL` / `FIXTURE_ADMIN_PASSWORD` (Synthetic administrator credentials)
- `FIXTURE_HANDLER_PASSWORD` (Synthetic operations desk credential)
- `FIXTURE_STUDENT_PASSWORD` (Synthetic student accounts credential)
- `EMAIL_PROVIDER` (`resend`, `sendgrid`, `console`, or `smtp`)
- `RESEND_API_KEY` / `SENDGRID_API_KEY` (HTTPS mail provider secret)
- `PUBLIC_BASE_URL` (Base URL for email verification links)

---

## 8. Test and Bug Report

### Local Test Execution & Results

#### 1. Pytest Test Suite
Executed command:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```
- **Result**: `25 passed, 13 warnings in 73.41s` (100% pass rate).
- **Coverage**: Authentication lifecycle, token hashing, image decoding, IDOR ownership, issue linking, reversible grouping, resolution feedback states, priority rules, and negation handling.

#### 2. Isolated Authentication & Provisioning Test Suite
Executed script:
```powershell
.\.venv\Scripts\python.exe scratch\verify_auth_isolated.py
```
- **Target**: Fresh, isolated temporary SQLite database.
- **Result**: `10 / 10 tests PASSED`. Verified fixture provisioning, CSRF enforcement, bad password rejection (`HTTP 401`), successful admin login (`HTTP 200`), role identity check (`/api/auth/me`), student access revocation (`HTTP 403`), session logout, and restart idempotency without password overwrite.

#### 3. CSRF & Session Security Acceptance Test Suite
Executed script:
```powershell
.\.venv\Scripts\python.exe scratch\verify_csrf_fix.py
```
- **Target**: Running local Waitress production server (`http://127.0.0.1:5000`).
- **Result**: `7 / 7 tests PASSED`. Verified cache-control `no-store` headers on `/api/auth/csrf`, rejection of missing/forged tokens, bad credentials rejection, logout session rotation, and multipart form-data image upload with CSRF headers.

### Live Environment Testing Status
- **Live Deployment URL**: `https://digital-campus-sczg.onrender.com`
- **Current Observation**: Live site is reachable (`HTTP 200` on `/healthz` and `/api/auth/csrf`).
- **Live Authentication Status**: **NOT TESTED / AWAITING DASHBOARD SECRETS**. Because the live Render container has ephemeral storage and the administrator account was not provisioned in the live database, live admin login returns `401`. Provisioning requires setting `BOOTSTRAP_DEMO_DATA=true` and `FIXTURE_ADMIN_PASSWORD` in the Render dashboard.

---

## 9. Next Three Actions

### Action 1 (P0 - Security & Data Integrity): Configure Persistent Secret & Database on Render
- **Evidence**: On Render's free tier, restarting the container resets the ephemeral filesystem, wiping `campusvoice.db` and regenerating an ephemeral secret key that invalidates all user sessions.
- **Minimal Change**:
  1. In the Render Dashboard, add `SECRET_KEY=<secure-hex-string>`.
  2. Add `DATABASE_URL=postgresql://...` pointing to a free managed PostgreSQL database (e.g. Neon, Supabase, or Render Postgres).
- **How to Test Success**:
  1. Log in on the live site, deploy a commit or trigger a restart, refresh the browser, and confirm the user session remains authenticated.
- **Dependencies & Risks**: Requires setting up an external database; SQLite remains functional for single-node prototypes if data loss on container sleep is acceptable.

---

### Action 2 (P1 - Deployment Build): Add Frontend Build to Cloud Deploy Blueprint
- **Evidence**: In [`render.yaml#L6`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/render.yaml#L6), `buildCommand` only runs `pip install -r requirements.txt && python -m flask campus_cli warmup-model`, omitting the Vite frontend compilation (`npm run build --prefix frontend`). If `frontend/dist/` is omitted from git, Render cannot serve the frontend.
- **Minimal Change**:
  Update `render.yaml` line 6:
  ```yaml
  buildCommand: npm install --prefix frontend && npm run build --prefix frontend && pip install -r requirements.txt && python -m flask campus_cli warmup-model
  ```
- **How to Test Success**:
  1. Trigger a clean build in Render without committed `dist/` artifacts and verify that `dist/index.html` is generated and served at `https://digital-campus-sczg.onrender.com`.
- **Dependencies & Risks**: Increases Render build time by ~45 seconds due to `npm install`.

---

### Action 3 (P2 - AI Evaluation): Add Benchmark Test Suite for Hindi / Hinglish Inputs
- **Evidence**: While `paraphrase-multilingual-MiniLM-L12-v2` supports multilingual embeddings, the repository currently has zero test cases or evaluation evidence for Hindi (`बिजली का तार खुला है`) or Hinglish (`hostel ka wifi band hai`) inputs.
- **Minimal Change**:
  Add a dedicated test module `tests/test_multilingual_evaluation.py` containing representative Hindi and Hinglish test sentences evaluated against category centroids and priority safety phrases.
- **How to Test Success**:
  Execute `pytest tests/test_multilingual_evaluation.py` and confirm that cosine similarity matches expected categories with similarity `> 0.60`.
- **Dependencies & Risks**: Model evaluation is CPU-bound; tests should run in ~3 seconds with cached weights.

