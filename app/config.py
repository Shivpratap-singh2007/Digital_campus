import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base application configuration."""
    # Cryptographically strong secret key fallback if not provided in environment
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    WTF_CSRF_SECRET_KEY = os.environ.get("WTF_CSRF_SECRET_KEY") or SECRET_KEY
    WTF_CSRF_TIME_LIMIT = 3600 * 4  # 4-hour CSRF token validity

    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in ("true", "1", "yes")
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'campusvoice.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

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

    # SMTP Configuration (compatible with Mailpit or configured SMTP server)
    SMTP_SERVER = os.environ.get("SMTP_SERVER", "localhost")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 1025))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "false").lower() in ("true", "1", "yes")
    SMTP_DEFAULT_SENDER = os.environ.get("SMTP_DEFAULT_SENDER", "CampusVoice Portal <noreply@campus.edu>")

    # Verification token validity & rate limits
    TOKEN_EXPIRATION_HOURS = int(os.environ.get("TOKEN_EXPIRATION_HOURS", 24))
    RESEND_COOLDOWN_SECONDS = int(os.environ.get("RESEND_COOLDOWN_SECONDS", 60))
    MAX_VERIFICATION_ATTEMPTS = int(os.environ.get("MAX_VERIFICATION_ATTEMPTS", 5))

    # Rate limiting thresholds
    AUTH_RATE_LIMIT = int(os.environ.get("AUTH_RATE_LIMIT", 10))
    SUBMISSION_RATE_LIMIT = int(os.environ.get("SUBMISSION_RATE_LIMIT", 15))

    # Semantic analysis
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
