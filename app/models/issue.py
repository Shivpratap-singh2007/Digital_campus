from datetime import datetime, timezone
from app.extensions import db


class Issue(db.Model):
    """An issue aggregates multiple related complaints into a single operational item."""
    __tablename__ = "issues"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    building = db.Column(db.String(100), nullable=False, index=True)
    room = db.Column(db.String(100), nullable=True)
    status = db.Column(
        db.String(30), nullable=False, default="submitted", index=True
    )  # 'submitted', 'under_review', 'in_progress', 'resolved'
    priority = db.Column(db.String(30), nullable=False, default="Normal")

    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    complaint_links = db.relationship(
        "IssueComplaintLink", backref="issue", cascade="all, delete-orphan", lazy="joined"
    )
    resolution_rounds = db.relationship(
        "ResolutionRound", backref="issue", cascade="all, delete-orphan", order_by="ResolutionRound.round_number"
    )

    @property
    def current_resolution_round(self):
        if self.resolution_rounds:
            return self.resolution_rounds[-1]
        return None

    def __repr__(self) -> str:
        return f"<Issue {self.id} title='{self.title[:20]}' status={self.status}>"


class IssueComplaintLink(db.Model):
    """Links complaints to issues. Preserves original submissions."""
    __tablename__ = "issue_complaint_links"

    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    complaint_id = db.Column(
        db.Integer, db.ForeignKey("complaints.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    relationship_type = db.Column(
        db.String(30), nullable=False, default="same_incident"
    )  # 'same_incident', 'related_only'
    linked_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<IssueComplaintLink issue={self.issue_id} complaint={self.complaint_id} rel={self.relationship_type}>"


class StatusEvent(db.Model):
    """Audit log for complaint and issue status transitions."""
    __tablename__ = "status_events"

    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(20), nullable=False, index=True)  # 'complaint' or 'issue'
    target_id = db.Column(db.Integer, nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    old_status = db.Column(db.String(30), nullable=False)
    new_status = db.Column(db.String(30), nullable=False)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    actor = db.relationship("User", foreign_keys=[actor_id])

    def __repr__(self) -> str:
        return f"<StatusEvent {self.target_type}:{self.target_id} {self.old_status}->{self.new_status}>"
