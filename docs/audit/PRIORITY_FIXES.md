# CampusVoice: Priority Fixes & Action Plan

This document details all technical fixes, configuration updates, and improvements identified during the audit, ranked by operational severity from **P0 (Critical Blockers)** to **P3 (Hygiene)**.

---

## Priority Classification Summary

| Priority | Defect / Task | Component | Impact | Estimated Effort |
| :---: | :--- | :--- | :--- | :---: |
| **P0** | Add Frontend Build to Cloud Deploy | `render.yaml` / Build Command | Stale frontend or missing bundle on cloud deploy | 5 mins |
| **P0** | Configure Persistent Cloud `SECRET_KEY` | Render Environment Variables | Session drops & CSRF token invalidation on container restart | 2 mins |
| **P0** | Configure Production HTTPS Email Key | Render Dashboard (`RESEND_API_KEY`) | Registration verification emails fail on cloud | 5 mins |
| **P1** | Fix Urgent Phrase Regex Substring Ordering | `app/services/priority_rules.py` | Pytest assertion failure (`live wire` vs `exposed live wire`) | 2 mins |
| **P1** | Implement Persistent Cloud Database | `app/config.py` / PostgreSQL | SQLite wiped on cloud spin-down / redeploy | 30 mins |
| **P2** | Disambiguate Acoustic "Feedback" in AV | `app/services/priority_rules.py` | Audio screeching misclassified as Low-priority suggestion | 10 mins |
| **P2** | Distributed Rate Limiter Backend | `app/services/rate_limiter.py` | In-memory limiter not shared across multiple WSGI workers | 25 mins |
| **P3** | Deprecate Unused Legacy Jinja2 Templates | `app/templates/` | Codebase bloat and developer confusion | 15 mins |

---

## P0: Critical Blockers (Production & Deployment)

### 1. Add Frontend Compilation to Cloud Build Command
- **Impact**: On clean git checkouts or cloud environments that rebuild without committed `dist/` artifacts, Render will not compile Vite assets. Browsers will receive 404s for bundle files.
- **Root Cause**: `render.yaml` only executes `pip install` and `warmup-model`.
- **Exact Fix**:
  Update `render.yaml` line 6:
  ```diff
  - buildCommand: pip install -r requirements.txt && python -m flask campus_cli warmup-model
  + buildCommand: npm install --prefix frontend && npm run build --prefix frontend && pip install -r requirements.txt && python -m flask campus_cli warmup-model
  ```
  *(Note: Render Python environments include Node.js. If building on Render dashboard, enter the same command under **Build Command**).*

---

### 2. Configure Persistent `SECRET_KEY` in Cloud Environment
- **Impact**: Without this variable, Render generates a random key on each container wake-up or deployment. All logged-in users are forcefully logged out, and submitted forms fail with `CSRF token missing or invalid`.
- **Root Cause**: The `.secret_key` fallback file is written to ephemeral container disk, which is wiped on redeploy.
- **Exact Fix**:
  In Render Dashboard -> `campusvoice` -> **Environment**:
  Add key:
  ```env
  SECRET_KEY=c4a98d3f7e1b5a20984c3e6d123456789abcdef0123456789abcdef012345678
  ```
  *(Generate a secure 64-character random string via `python -c "import secrets; print(secrets.token_hex(32))"`).*

---

### 3. Provide Valid `RESEND_API_KEY` for Email Verification
- **Impact**: Outbound SMTP port 587 is blocked on Render free instances. New student registrations cannot receive verification links unless an HTTPS mail provider is connected.
- **Root Cause**: `render.yaml` sets `EMAIL_PROVIDER: resend`, but `RESEND_API_KEY` is empty (`sync: false`).
- **Exact Fix**:
  In Render Dashboard -> **Environment**:
  ```env
  EMAIL_PROVIDER=resend
  RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
  MAIL_DEFAULT_SENDER=onboarding@resend.dev
  ```

---

## P1: High Priority (Test Integrity & Persistence)

### 4. Urgent Phrase Ordering in `priority_rules.py`
- **Impact**: Fails automated unit test `tests/test_semantic_and_rules.py::test_priority_rules_urgent_detection`.
- **Root Cause**: In `app/services/priority_rules.py`, shorter pattern `"live wire"` appears before `"exposed live wire"`. Python regex matches the first matching item in the list.
- **Exact Proposed Diff**:
  [`app/services/priority_rules.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/priority_rules.py#L22):
  ```diff
   URGENT_PHRASES = [
  +    r"exposed live wire",
       r"live wire",
  -    r"exposed live wire",
       r"sparking wire",
  ```
- **Verification**: Run `pytest tests/test_semantic_and_rules.py` to confirm 100% test pass rate.

---

### 5. Persistent Cloud Database (PostgreSQL Migration)
- **Impact**: All complaints submitted on the live Render app disappear when the container sleeps after 15 minutes of inactivity.
- **Root Cause**: SQLite file `campusvoice.db` is saved on local container disk.
- **Exact Fix**:
  1. Create a free managed PostgreSQL instance on Render, Neon, or Supabase.
  2. Set `DATABASE_URL` in Render environment:
     ```env
     DATABASE_URL=postgresql://user:password@host/dbname
     ```
  3. Ensure `psycopg2-binary` is installed (already supported by SQLAlchemy).

---

## P2: Medium Priority (Edge Cases & Scaling)

### 6. Acoustic Feedback Disambiguation in Audio Equipment
- **Impact**: A complaint reporting *"Microphone feedback screeching in auditorium"* is assigned priority `Low` instead of `Normal` or `High`.
- **Root Cause**: `priority_rules.py` matches the word `"feedback"` as an institutional suggestion keyword.
- **Proposed Diff**:
  [`app/services/priority_rules.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/priority_rules.py):
  Add negative lookbehind/lookahead or exclude acoustic terms:
  ```python
  # Match 'feedback' only when not preceded by 'audio', 'sound', 'mic', or 'microphone'
  r"(?<!audio\s)(?<!sound\s)(?<!mic\s)(?<!microphone\s)\bfeedback\b"
  ```

---

### 7. Centralized Redis Rate Limiter for Multi-Worker Environments
- **Impact**: When deploying with multiple Gunicorn/Waitress worker processes, each worker maintains an independent rate-limit dictionary in memory. A user could make 2x or 4x the rate limit before being throttled.
- **Fix**: Update [`app/services/rate_limiter.py`](file:///c:/Users/Rohit/Digital_campus/Digital_campus/app/services/rate_limiter.py) to check for `REDIS_URL`. If present, use Redis key expiration (`INCR` + `EXPIRE`); otherwise, gracefully fall back to the existing in-memory dictionary.

---

## P3: Low Priority (Code Hygiene)

### 8. Deprecate Legacy Server-Rendered Jinja2 Templates
- **Impact**: `app/templates/` contains 18 Jinja2 HTML files (e.g., `admin/dashboard.html`, `complaints/new.html`) that are superseded by the React SPA. They increase maintenance overhead and can confuse new developers.
- **Recommendation**: Mark `app/templates/` as legacy or archive them under `app/templates_legacy/`, keeping only minimal error fallback pages (`404.html`, `500.html`).

