# CampusVoice — Build & Verification Status

## Implementation Checklist

### Phase 1: Architecture & Backend Foundations
- [x] Application Factory & Configuration (`app/config.py`, `app/__init__.py`)
- [x] Database Schema & Models (`User`, `VerificationToken`, `Complaint`, `Attachment`, `AnalysisResult`, `Issue`, `IssueComplaintLink`, `StatusEvent`, `ResolutionRound`, `ResolutionFeedback`, `AuditEvent`)
- [x] SMTP Email Verification with token hashing, expiration, rate limiting, and Mailpit compatibility (`app/services/email.py`)
- [x] Secure Pillow image processing (JPEG/PNG validation, 5MB max, decoded pixel expansion limit, EXIF/GPS metadata stripping, secure storage outside `static/`)
- [x] Versioned explainable priority rules engine with negation & historical context handling (`app/services/priority_rules.py`)
- [x] Semantic analysis engine with sentence-transformers and graceful offline/blocked fallback (`app/services/semantic.py`)
- [x] Identity reveal service with mandatory audit persistence & PII protection (`app/services/audit.py`)

### Phase 2: REST API Endpoints with CSRF & Session Auth
- [x] CSRF & Session Auth Endpoints (`/api/auth/csrf-token`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/register`, `/api/auth/me`, `/api/auth/resend-verification`, `/api/auth/verify/<token>`)
- [x] Complaints API (`/api/complaints`, `/api/complaints/<id>`, `/api/complaints/attachment/<filename>`, `/api/complaints/<id>/retry-analysis`)
- [x] Issues & Reversible Grouping API (`/api/issues`, `/api/issues/<id>`, `/api/issues/<id>/status`, `/api/issues/<id>/link`, `/api/issues/<id>/unlink/<complaint_id>`)
- [x] Verified Resolution Feedback API (`/api/feedback/issue/<id>`)
- [x] Admin & Handler API (`/api/admin/queue` with submitter masking, `/api/admin/complaint/<id>/reveal-identity` with audited justification, `/api/admin/dashboard` live metrics, `/api/admin/audit-log`)

### Phase 3: React + Vite + TypeScript Frontend
- [x] Vite project setup with TypeScript, React Router, Bootstrap 5, and Recharts
- [x] Centralized API Client with credentials ('include') and CSRF token header management (`X-CSRFToken`)
- [x] Navigation bar with role-based links, Emergency Notice, and Privacy Architecture banner
- [x] Authentication pages: Register with college domain validation, Login, Verification guidance & token check
- [x] Complaint submission form with unique submission key and photo upload
- [x] "My Submissions" list and complaint detail with status progression timeline
- [x] Interactive Submitter Resolution Feedback Component (Fixed / Partially fixed / Not fixed)
- [x] Operations Queue for Handlers (masked submitter identities, filter by category/location/priority/status)
- [x] Issue Management & Detail (create issue, link/unlink complaints, semantic suggested matches, status progression, resolution round summary)
- [x] Audited Identity Reveal Dialog (Admin role only, required justification, immutable audit log)
- [x] Metrics Dashboard (Recharts + standalone numerical tables, live DB metrics)
- [x] Public Issues Board (approved summaries only, no raw descriptions or attachments)

### Phase 4: Integration, Tests & Production Demo Serving
- [x] Backend test suite with `pytest` covering auth, complaints, privacy/audit, issues, feedback, and image validation (16/16 tests passing)
- [x] Vite frontend build (`npm run build`) integrated with Flask single-origin serving
- [x] CLI commands for admin creation, handler creation, and synthetic demo data seeding (`flask campus_cli seed-demo`, `create-admin`, `create-handler`, `warmup-model`)
- [x] Waitress production demo runner (`python run.py`)
- [x] Comprehensive documentation in `README.md`
