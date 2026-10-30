from datetime import datetime, timezone
from app.extensions import db


class AuditEvent(db.Model):
    """
    Security and privacy audit log.
    Records who accessed protected information or performed sensitive actions.
    CRITICAL: Does not store disclosed PII (names, emails) redundantly.
    """
    __tablename__ = "audit_events"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False, index=True)  # e.g., 'reveal_identity'
    target_type = db.Column(db.String(50), nullable=False)          # e.g., 'complaint'
    target_id = db.Column(db.Integer, nullable=False)
    justification = db.Column(db.Text, nullable=False)              # Required purpose/justification
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    actor = db.relationship("User", foreign_keys=[actor_id])

    def __repr__(self) -> str:
        return f"<AuditEvent actor={self.actor_id} action={self.action} target={self.target_type}:{self.target_id}>"
