# CampusVoice: Deployment Runbook & Operational Guide

## 1. Build and Start Commands

### Local Development / Standard Production

```bash
# 1. Install Python Dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

# 2. Build Frontend Production Assets
cd frontend
npm ci
npm run build
cd ..

# 3. Database Initialization & Migration
flask db-upgrade  # Or: python -m app.cli db-init

# 4. Optional: Provision Synthetic Demo Fixtures
# Safe provisioning requires explicit passwords via env vars or interactive prompt
export FIXTURE_ADMIN_PASSWORD="YourSecureAdminPassword123!"
export FIXTURE_HANDLER_PASSWORD="YourSecureHandlerPassword123!"
export FIXTURE_STUDENT_PASSWORD="YourSecureStudentPassword123!"
flask seed-fixtures

# 5. Start Production Server (Waitress / Gunicorn)
# Windows:
python run.py
# Linux / Container:
gunicorn -w 4 -b 0.0.0.0:5000 "run:app"
```

### Render Deployment Configuration (`render.yaml`)

```yaml
services:
  - type: web
    name: campusvoice
    env: python
    buildCommand: "pip install -r requirements.txt && npm install --prefix frontend && npm run build --prefix frontend"
    startCommand: "gunicorn -w 2 -b 0.0.0.0:$PORT run:app"
```

---

## 2. Environment Variable Inventory

| Environment Variable | Purpose & Description | Default / Fallback | Secret Handling & Risk |
|---|---|---|---|
| `SECRET_KEY` | Flask session cookie encryption & CSRF signing. | Ephemeral random key | **CRITICAL SECRET.** Must be set in production to prevent session invalidation on restart. |
| `DATABASE_URL` | SQLAlchemy database connection URI. | `sqlite:///instance/campusvoice.db` | **PERSISTENCE RULE.** On ephemeral platforms (e.g. Render Free), SQLite is wiped on dyno restart. Supply PostgreSQL URL (`postgresql://...`) for persistence. |
| `ALLOWED_ORIGINS` | CORS & CSRF trusted origin domains. | `http://localhost:5000,http://127.0.0.1:5000` | In production, set to your canonical domain (e.g. `https://campusvoice.onrender.com`). |
| `MODEL_NAME` | Hugging Face model repository or local directory. | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Cached locally in `.cache/huggingface/hub/`. Set to pre-downloaded local folder in air-gapped environments. |
| `UPLOAD_FOLDER` | Persistent disk directory for submitted image attachments. | `instance/uploads` | Configure persistent disk mount (or S3/Cloud Storage) if container restarts are frequent. |
| `MAX_CONTENT_LENGTH` | Maximum allowed HTTP request body size. | `16777216` (16 MB) | Protects server against Denial of Service via large uploads. |
| `SIMILARITY_THRESHOLD`| Cosine similarity threshold for automatic category acceptance. | `0.55` | Submissions scoring below this are flagged for human handler review (`is_ambiguous=True`). |
| `AMBIGUITY_MARGIN` | Minimum difference between top two category scores. | `0.08` | Prevents arbitrary tie-breaking between competing categories. |
| `RESEND_API_KEY` | API key for Resend transactional email delivery. | None (console logging fallback) | Non-critical in dev/demo; console prints verification URLs. Required for real email delivery in production. |
| `FIXTURE_ADMIN_PASSWORD` | Password for synthetic `admin@campus.edu`. | Required if provisioning | Never hardcoded in repository code. |
| `FIXTURE_HANDLER_PASSWORD`| Password for synthetic `handler@campus.edu`. | Required if provisioning | Never hardcoded in repository code. |
| `FIXTURE_STUDENT_PASSWORD`| Password for synthetic students (`student.aarav@campus.edu`, etc.). | Required if provisioning | Never hardcoded in repository code. |

---

## 3. Database Persistence & Migrations

1. **Local & Persistent VM:** Default SQLite database resides at `instance/campusvoice.db`. The `instance/` folder must be included in backup snapshots.
2. **Ephemeral Containers (Render / Heroku):** Ephemeral disks are reset on deploy and container sleep. Set `DATABASE_URL=postgresql://user:pass@host:port/dbname` to enable managed PostgreSQL storage.
3. **Idempotent Fixture Provisioning:** `flask seed-fixtures` uses deterministic record lookups (`filter_by(email=...)`, `filter_by(title=...)`). It will **never** overwrite an existing user's password or duplicate complaints upon redeploy.

---

## 4. File Upload Storage

- Attached files are validated via magic-bytes (Pillow `Image.verify()`), stripped of all EXIF metadata, and assigned a random UUID filename.
- Files are saved strictly in `UPLOAD_FOLDER` outside of public static directories.
- Downloads are served exclusively through the authenticated handler route `/api/complaints/<id>/attachment` with strict access control checks.

---

## 5. Embedding Model Provisioning

- The model `paraphrase-multilingual-MiniLM-L12-v2` requires ~470 MB of disk space.
- The model weights are automatically cached in `~/.cache/huggingface/hub/` on first startup or pre-packaged into the build container.
- **Fail-safe fallback:** If PyTorch native DLLs or model files cannot be loaded, the backend automatically transitions to fallback mode:
  - Health check flags `ai_model_loaded: false`.
  - Priority rules continue running (100% pure Python keyword and regex evaluation).
  - Categorization flags `is_ambiguous = True` so human handlers can manually assign the category without application crashes.

---

## 6. Email Service Configuration

- Verification tokens use cryptographic single-use SHA-256 tokens stored with expiry timestamps.
- When `RESEND_API_KEY` is omitted, the application logs the token and full verification link directly to the application stdout/console:
  ```
  [EMAIL SERVICE] Verification link for student@campus.edu: http://localhost:5000/verify-email?token=...
  ```
- This allows zero-dependency local and staging testing without configuring third-party SMTP servers.

