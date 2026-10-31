# Automated Test Results & Verification Report

**Date of Execution:** 2026-10-31  
**Test Runner:** `pytest 9.2.0` (Python 3.11.17, Windows 64-bit)  
**Total Tests:** 27  
**Passed:** 27  
**Failed:** 0  
**Warnings:** 0 (All legacy deprecation warnings resolved)  
**Execution Duration:** 18.94 seconds  

---

## 1. Pytest Warning Inspection & Resolution

Earlier test runs logged 10 to 13 `LegacyAPIWarning` notices from SQLAlchemy:
```
LegacyAPIWarning: The Query.get() method is considered legacy as of the 1.x series of SQLAlchemy and becomes a legacy construct in 2.0. The method is now available as Session.get()
```

### Cause Analysis:
- In SQLAlchemy 2.0 and Flask-SQLAlchemy 3.x, `Model.query.get(ident)` and `Model.query.get_or_404(ident)` invoke legacy SQLAlchemy 1.x `Query.get()` semantics.
- While backward-compatible in 1.4/2.0 compatibility mode, calling `.query.get()` generates deprecation warnings and will fail in pure SQLAlchemy 2.1+.

### Resolution (Zero Suppression):
- Replaced all occurrences of `Model.query.get(ident)` across application routes, services, and tests with `db.session.get(Model, ident)`.
- Replaced all occurrences of `Model.query.get_or_404(ident)` with `db.get_or_404(Model, ident)`.
- **Result:** Warning count reduced to **0**. No warnings are suppressed via filter configuration.

---

## 2. Test Suite Summary Table

| Test Module | Coverage Area | Tests Run | Result | Key Invariants Verified |
|---|---|:---:|:---:|---|
| [`tests/test_auth.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/tests/test_auth.py) | Authentication, Registration, Domain Enforcement, Tokens, Fixture Seeding | 6 | **PASS** | College domain validation (`@campus.edu`), subdomain attack rejection, single-use SHA-256 tokens, login/logout session handling, synthetic fixture provisioning with academic clash and disputed lifecycle (R1, R9). |
| [`tests/test_complaints.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/tests/test_complaints.py) | Complaint Ingestion, Idempotency, File Uploads | 3 | **PASS** | Unverified user blocking, idempotency replay prevention, MIME type detection via magic numbers, EXIF metadata stripping (R1, R2). |
| [`tests/test_issues_and_feedback.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/tests/test_issues_and_feedback.py) | Reversible Grouping, Feedback Lifecycle | 2 | **PASS** | Master issue grouping without losing raw reports, reversible unlinking, original submitter feedback validation, unanimous vs disputed consensus (R4, R7). |
| [`tests/test_privacy_and_audit.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/tests/test_privacy_and_audit.py) | Submitter Anonymity, Identity Reveal, Admin Dashboard Metrics | 3 | **PASS** | Handler queue anonymity, admin audit logging before identity reveal, no PII leakage in justification, 14-day submission trends, Multi-report issues queries (R6, R8). |
| [`tests/test_security.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/tests/test_security.py) | CSRF, IDOR, Rate Limiting, Session Fixation, Content Sanitization | 9 | **PASS** | CSRF double-submit token enforcement, IDOR complaint access checks, role authorization, Bleach HTML sanitization, rate limiting on auth endpoints (R1, R8). |
| [`tests/test_semantic_and_rules.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/tests/test_semantic_and_rules.py) | Priority Detection, Negation, Semantic Engine | 4 | **PASS** | Hazard phrase detection (`Urgent review`), negation handling ("no exposed wire" -> not urgent), historical past-tense handling, fallback when weights missing (R3, R5). |

---

## 3. Multi-report Issues Definition & Query

- **Metric Title:** Multi-report Issues (Aggregated Incident Groups)
- **Definition:** Master issues aggregating 2 or more distinct user complaints that report co-occurring symptoms or damage in the same campus area.
- **SQL Query:**
  ```python
  db.session.query(
      Issue.id, Issue.title, Issue.category, Issue.building, Issue.status, Issue.priority,
      func.count(IssueComplaintLink.id).label("report_count"),
      func.max(Complaint.created_at).label("last_reported_at")
  )
  .join(IssueComplaintLink, IssueComplaintLink.issue_id == Issue.id)
  .join(Complaint, IssueComplaintLink.complaint_id == Complaint.id)
  .group_by(Issue.id)
  .having(func.count(IssueComplaintLink.id) > 1)
  ```
- **Distinction from Recurrence:** This metric tracks simultaneous or grouped reports. It does not measure recurrence after resolution, preventing misleading operational reporting.

---

## 2. Mocking vs. Real Component Boundaries

| Component | Test Environment Mode | Production Mode | Justification & Verification |
|---|---|---|---|
| **Database** | Isolated temporary SQLite instance per fixture | Persistent SQLite or PostgreSQL (`DATABASE_URL`) | Tests exercise 100% real SQLAlchemy ORM models, relations, queries, foreign keys, cascades, and constraints. |
| **CSRF Protection** | Real Flask-WTF CSRF with session cookies | Real Flask-WTF CSRF with session cookies | Tests submit real tokens via `X-CSRFToken` and verify rejection when omitted or invalid. |
| **Authentication & RBAC** | Real Flask-Login sessions with bcrypt password hashing | Real Flask-Login sessions with bcrypt password hashing | Real password validation, role checks, and session lifecycle are executed. |
| **Email Service** | In-memory token generation (SHA-256 hashed in DB) | Resend API / SMTP email delivery | Avoids external network calls during automated test suites while verifying token hashing and single-use expiry. |
| **Semantic AI Engine** | Fallback/Mock mode enabled during fast unit tests (`TESTING=True`) | Real HuggingFace multilingual MiniLM model (`sentence-transformers`) | Fast test execution (<20s). Full real model weights are tested separately in `scratch/run_comprehensive_ai_eval.py` without skipping. |
| **Image Processing** | Real Pillow (`PIL`) image generation and EXIF stripping | Real Pillow (`PIL`) image generation and EXIF stripping | Real image headers and dimensions are parsed and saved to test upload directory. |

---

## 3. Frontend Build Verification

```
> campusvoice-frontend@1.0.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 855 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                               0.92 kB │ gzip:   0.59 kB
dist/assets/bootstrap-icons-DJdhg9lH.woff2  134.01 kB
dist/assets/bootstrap-icons-BHUGvtHM.woff   180.29 kB
dist/assets/index-IGBFD_3v.css              315.62 kB │ gzip:  46.88 kB
dist/assets/index-B_uA6jzm.js               768.55 kB │ gzip: 211.16 kB
✓ built in 3.66s with 0 errors
```

