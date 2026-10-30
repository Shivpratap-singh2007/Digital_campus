# CampusVoice — Campus Complaints with Verified Resolution Feedback

A production-grade, privacy-conscious campus complaint and suggestion platform built for a 24-hour college hackathon.

---

## 1. Executive Summary

Campus facilities and maintenance portals frequently suffer from three major failure modes:
1. **Premature Ticket Closure:** Administrative staff mark a maintenance ticket "resolved" without verifying that the physical repair actually succeeded.
2. **Retaliation Risks & Lack of Trust:** Students hesitate to report dormitory or academic safety hazards when their personal identities are exposed to maintenance workers.
3. **Duplicate & Conflicting Reports:** Dozens of individuals submit reports for the exact same event (e.g. broken pipe or power outage) without operational grouping.

**CampusVoice** solves these issues through:
- **Verified Resolution Feedback:** When an issue is administratively resolved, the original verified submitters are invited to evaluate the repair (**Fixed**, **Partially fixed**, or **Not fixed**). An issue is only labeled **Submitter-Confirmed** if all unique submitters confirm the fix.
- **Identity-Restricted Privacy Architecture:** Ordinary operations screens omit submitter names and emails. Submitter identity can only be accessed through an explicitly audited, administrator-authorized action that commits an immutable `AuditEvent` with mandatory justification *before* disclosing data.
- **Explainable Semantic & Rule-Based Diagnostics:** Reports are analyzed for urgent physical safety hazards using versioned, deterministic rules with negation detection, paired with multilingual semantic clustering.

---

## 2. Technology Stack

- **Frontend:** React 18, Vite, TypeScript, React Router 6, Bootstrap 5, Bootstrap Icons, Recharts (for live dashboard metrics).
- **Backend:** Python 3.11+, Flask with Application Factory & Blueprints (`api`, `auth`, `complaints`, `issues`, `feedback`, `admin`, `main`).
- **Database & ORM:** SQLite with Flask-SQLAlchemy (single-server zero-config hackathon deployment).
- **Session & Security:** Flask-Login for session cookies, Flask-WTF with CSRFProtect (`X-CSRFToken` header validation for JSON & multipart), Werkzeug password hashing.
- **Image Processing:** Pillow (PIL) validating genuine JPEG/PNG binary decoding, 5 MB file size limit, decoded-pixel expansion limit, EXIF/GPS metadata stripping, stored outside public static directories.
- **Semantic Engine:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` with cosine centroid clustering and offline/environment safety fallbacks.
- **Production Serving & Testing:** Waitress WSGI server (multi-threaded single-origin delivery) and `pytest` test suite.

---

## 3. Important File Directory Map

```text
Digital_campus/
├── app/
│   ├── __init__.py            # Application factory `create_app` & single-origin React static serving
│   ├── config.py              # Central configuration (domains, uploads, thresholds)
│   ├── extensions.py          # SQLAlchemy db, LoginManager, CSRFProtect
│   ├── forms.py               # Flask-WTF forms with exact domain validation
│   ├── cli.py                 # CLI commands (create-admin, create-handler, seed-demo, warmup-model)
│   ├── models/                # Relational database schema
│   │   ├── user.py            # User (roles: user/handler/admin), VerificationToken (hashed single-use)
│   │   ├── complaint.py       # Complaint, Attachment (secure storage), AnalysisResult
│   │   ├── issue.py           # Issue (synthesized master task), IssueComplaintLink, StatusEvent
│   │   ├── feedback.py        # ResolutionRound, ResolutionFeedback (verified submitter feedback)
│   │   └── audit.py           # AuditEvent (immutable security log without PII duplication)
│   ├── services/
│   │   ├── email.py           # SMTP mailer, Mailpit compatibility, token hash generator
│   │   ├── image.py           # Pillow image validation, pixel limit, EXIF stripping
│   │   ├── priority_rules.py  # Versioned explainable priority rules with negation handling
│   │   ├── semantic.py        # SentenceTransformer model loader, centroid embeddings, candidate matching
│   │   ├── complaint_analysis.py # Pipeline coordinator (preserves complaint before analysis)
│   │   └── audit.py           # Identity reveal service with mandatory audit persistence
│   └── blueprints/
│       ├── api/               # REST API for React frontend
│       └── [main, auth, complaints, issues, feedback, admin] # Full-featured server templates
├── frontend/                  # React + Vite + TypeScript Single Page Application
│   ├── src/
│   │   ├── api/client.ts      # Centralized fetch client with automatic CSRF & credentials
│   │   ├── context/AuthContext.tsx # User session provider
│   │   ├── components/        # Navbar, StatusBadge, ResolutionFeedback
│   │   └── pages/             # HomePage, QueuePage, DashboardPage, IssueDetailPage, etc.
│   └── vite.config.ts         # Vite proxy configuration (/api -> http://127.0.0.1:5000)
├── uploads/                   # Secure storage for images (OUTSIDE public static folders)
├── tests/                     # 16-test comprehensive pytest suite
├── run.py                     # Production Waitress demo server entrypoint
└── requirements.txt           # Python backend dependencies
```

---

## 4. Key Workflows & Principles

### A. Authentication & Domain Enforcement
1. **Exact Parsed Domain Matching:** Registration parses the email string after `@` and checks against allowlisted college domains (`campus.edu`, `university.ac.in`). It rejects tricky subdomains such as `campus.edu.attacker.com`.
2. **Hashed Single-Use Tokens:** Verification tokens are generated using `secrets.token_urlsafe(32)`. Only the SHA-256 hash is persisted in the database.
3. **Mailpit Compatibility:** Works out-of-the-box with local Mailpit test inboxes (`localhost:1025` SMTP, `http://localhost:8025` web UI).
4. **No Self-Assigned Privileges:** Administrative and handler accounts can only be provisioned via the secure CLI system command (`flask create-admin`).

### B. Idempotency & Safe Image Uploads
1. **Submission Nonce / Idempotency Key:** Submitting a report attaches a unique `submission_key`. Double-clicking or retrying returns the existing complaint ID without creating duplicates. Reusing a key with altered content returns a `409 Conflict`.
2. **Pillow Binary Validation:** Images are decoded in memory using Pillow to verify genuine JPEG or PNG headers. Files exceeding 5 MB or 16 megapixels (decompression bomb protection) are rejected. EXIF/GPS metadata is stripped before saving to the isolated `uploads/` folder.

### C. Explainable Diagnostics & Uncertainty
1. **Deterministic Priority Rules:** Rules detect physical hazards (e.g. `sparking socket` -> Urgent: immediate electrical hazard with fire risk).
2. **Negation & Historical Detection:** Phrases such as `"no exposed wire"` or `"fixed yesterday"` prevent false urgency and flag the report as ambiguous for human review.
3. **Semantic Centroids:** Sentence-transformers embeddings compare complaint descriptions against representative category clusters. If scores are close or weak, the system flags `needs_review` and displays: *"Similarity is not a calibrated confidence percentage."*

### D. Verified Resolution Feedback
1. **Original Submitters Only:** Only verified users who originally submitted a complaint linked to the resolved issue can vote.
2. **Resolution State Rules:**
   - **Submitter-Confirmed:** Every unique linked submitter must respond `Fixed`.
   - **Disputed:** Any `Partially fixed` or `Not fixed` response flags the issue for administrative review.
   - **Missing Responses:** Unanswered feedback invitations never count as fixed.

---

## 5. How to Run the Application

### 1. Environment Setup
```powershell
# Activate Python 3.11 virtual environment
.\.venv\Scripts\activate

# Install backend dependencies (if needed)
pip install -r requirements.txt
```

### 2. Populate Demo Data
```powershell
# Populate database with realistic synthetic demo users, issues, and complaints
python -m flask --app run.py campus_cli seed-demo
```
This generates default accounts:
- **Administrator:** `admin@campus.edu` / `AdminPass123!`
- **Handler:** `handler@campus.edu` / `HandlerPass123!`
- **Student 1:** `student.aarav@campus.edu` / `StudentPass123!`
- **Student 2:** `student.priya@campus.edu` / `StudentPass123!`
- **Student 3:** `student.rohan@campus.edu` / `StudentPass123!`

### 3. Run Backend Test Suite
```powershell
python -m pytest tests -v
```
All 16 unit and integration tests run in sandbox mode with in-memory SQLite and isolated upload directories.

### 4. Build React Frontend & Launch Waitress Server
```powershell
# Build Vite production bundle
cd frontend
npm run build
cd ..

# Start single-origin production server with Waitress
python run.py
```
Open your browser at **`http://127.0.0.1:5000`**.

---

## 6. Live Hackathon Demo Walkthrough (5 Minutes)

1. **Public Board (`/`):** View live metrics strictly derived from the SQLite database and examine public issue summaries.
2. **Log In as Student (`student.aarav@campus.edu`):**
   - Visit `/new-complaint`. Submit a new report (e.g. *"Water cooler leaking in Library"*).
   - View instant diagnostic output showing deterministic priority rules and status events.
3. **Log In as Handler (`handler@campus.edu`):**
   - Open `/admin/queue`. Notice that all submitters are masked as `Anonymous Submitter #<id>`.
   - Open an issue (`/admin/issues/1`). Review suggested related reports surfaced by semantic similarity.
   - Update operational status to **Resolved**, providing a required resolution note.
4. **Submitter Resolution Feedback:**
   - Log back in as the student whose report was resolved.
   - Navigate to `/complaints/<id>`. The interactive **Verified Resolution Feedback** form is now unlocked.
   - Submit a rating of **Fixed** or **Partially fixed** and observe the issue feedback round re-evaluating in real-time.
5. **Audited Identity Reveal (Admin Only):**
   - Log in as `admin@campus.edu`.
   - On `/admin/queue`, click the shield lock icon next to a report.
   - Enter a required operational justification (e.g., *"Contacting submitter for lab key access"*).
   - The submitter identity is disclosed, and an immutable entry is logged in the **Restricted Audit Log** (`/admin/audit-log`).
