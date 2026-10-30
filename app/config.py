import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_secret_key(base_dir: Path) -> str:
    """
    Ensures SECRET_KEY is stable across process restarts and multi-worker setups.
    Prioritizes explicit environment configuration, falling back to a persisted
    local key file before generating an ephemeral secret.
    """
    env_secret = os.environ.get("SECRET_KEY")
    if env_secret and env_secret.strip():
        return env_secret.strip()

    key_file = base_dir / ".secret_key"
    try:
        if key_file.exists():
            key = key_file.read_text(encoding="utf-8").strip()
            if key:
                return key
        new_key = secrets.token_hex(32)
        key_file.write_text(new_key, encoding="utf-8")
        return new_key
    except Exception:
        return secrets.token_hex(32)


class Config:
    """Base application configuration."""
    # Cryptographically strong secret key (stable across workers & restarts)
    SECRET_KEY = _resolve_secret_key(BASE_DIR)
    WTF_CSRF_SECRET_KEY = os.environ.get("WTF_CSRF_SECRET_KEY") or SECRET_KEY
    WTF_CSRF_TIME_LIMIT = 3600 * 4  # 4-hour CSRF token validity

    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Auto-enable Secure cookies in production/Render (HTTPS), while permitting local HTTP development
    _is_render = bool(os.environ.get("RENDER"))
    _public_url = os.environ.get("PUBLIC_BASE_URL", "").lower()
    _is_https = _public_url.startswith("https://") or _is_render
    _env_secure = os.environ.get("SESSION_COOKIE_SECURE")
    if _env_secure is not None:
        SESSION_COOKIE_SECURE = _env_secure.lower() in ("true", "1", "yes")
    else:
        SESSION_COOKIE_SECURE = _is_https

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    # Database Configuration (supports explicit SQLITE_PATH or DATABASE_URL)
    sqlite_path_env = os.environ.get("SQLITE_PATH")
    db_env = os.environ.get("DATABASE_URL")
    if sqlite_path_env:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{sqlite_path_env}"
    elif db_env:
        if db_env.startswith("postgres://"):
            db_env = db_env.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = db_env
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'campusvoice.db'}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Public base URL (e.g. https://campusvoice.up.railway.app) for links in verification emails
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

    # Allowed email domains (exact domain match, not substring)
    COLLEGE_EMAIL_DOMAINS = [
        d.strip().lower()
        for d in os.environ.get(
            "COLLEGE_EMAIL_DOMAINS", "campus.edu,university.ac.in,student.college.edu"
        ).split(",")
        if d.strip()
    ]

    # File uploads - stored securely OUTSIDE static/
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max form payload
    MAX_IMAGE_FILE_SIZE = 5 * 1024 * 1024   # 5 MB max image file size
    MAX_IMAGE_PIXELS = 16_000_000           # 16 MP max decoded image pixels (e.g. 4000x4000)

    # Email Dispatcher Configuration
    EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "smtp").lower()  # 'smtp', 'resend', 'sendgrid', 'console'
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")

    # SMTP Configuration (compatible with Mailpit or configured SMTP server)
    SMTP_SERVER = os.environ.get("SMTP_SERVER", "localhost")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 1025))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "false").lower() in ("true", "1", "yes")
    SMTP_DEFAULT_SENDER = os.environ.get("SMTP_DEFAULT_SENDER", "CampusVoice Portal <noreply@campus.edu>")

    # Fixtures & Demo Mode
    DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() in ("true", "1", "yes")
    BOOTSTRAP_DEMO_DATA = os.environ.get("BOOTSTRAP_DEMO_DATA", "false").lower() in ("true", "1", "yes")

    # Verification token validity & rate limits
    TOKEN_EXPIRATION_HOURS = int(os.environ.get("TOKEN_EXPIRATION_HOURS", 24))
    RESEND_COOLDOWN_SECONDS = int(os.environ.get("RESEND_COOLDOWN_SECONDS", 60))
    MAX_VERIFICATION_ATTEMPTS = int(os.environ.get("MAX_VERIFICATION_ATTEMPTS", 5))

    # Rate limiting thresholds
    AUTH_RATE_LIMIT = int(os.environ.get("AUTH_RATE_LIMIT", 10))
    SUBMISSION_RATE_LIMIT = int(os.environ.get("SUBMISSION_RATE_LIMIT", 15))

    # Semantic analysis & HuggingFace Model Cache
    HF_HOME = os.environ.get("HF_HOME", str(BASE_DIR / ".cache" / "huggingface"))
    ALLOW_MODEL_DOWNLOAD = os.environ.get("ALLOW_MODEL_DOWNLOAD", "true").lower() in ("true", "1", "yes")
    MODEL_NAME = os.environ.get(
        "MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    ANALYSIS_VERSION = "1.0.0"
    SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", 0.55))
    AMBIGUITY_MARGIN = float(os.environ.get("AMBIGUITY_MARGIN", 0.08))

    # Predefined campus locations
    CAMPUS_LOCATIONS = [
        "Academic Block A",
        "Academic Block B",
        "Central Library",
        "Computer Center / IT Labs",
        "Boys Hostel 1",
        "Boys Hostel 2",
        "Girls Hostel 1",
        "Girls Hostel 2",
        "Main Cafeteria & Food Court",
        "Sports Complex & Gymnasium",
        "Administrative Block",
        "Health Center",
        "Campus Grounds & Walkways",
        "Other / Outdoor",
    ]


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    UPLOAD_FOLDER = str(BASE_DIR / "test_uploads")
    RESEND_COOLDOWN_SECONDS = 0
