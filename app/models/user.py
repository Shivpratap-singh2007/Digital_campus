from datetime import datetime, timezone
import hashlib
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    """User account model."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # 'user', 'handler', 'admin'
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    complaints = db.relationship("Complaint", backref="submitter", lazy="dynamic", foreign_keys="Complaint.user_id")
    verification_tokens = db.relationship("VerificationToken", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    feedbacks = db.relationship("ResolutionFeedback", backref="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def has_role(self, *roles: str) -> bool:
        return self.role in roles

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_handler(self) -> bool:
        return self.role in ("handler", "admin")

    def __repr__(self) -> str:
        return f"<User {self.id} role={self.role}>"


class VerificationToken(db.Model):
    """Stores hashed email verification tokens."""
    __tablename__ = "verification_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()

    def is_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        # Handle naive datetime from sqlite
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now > exp

    def is_valid(self) -> bool:
        return self.used_at is None and not self.is_expired()
