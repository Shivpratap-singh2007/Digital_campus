from datetime import datetime, timezone
from app.extensions import db


class Complaint(db.Model):
    """Complaint or Suggestion submission."""
    __tablename__ = "complaints"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    submission_type = db.Column(db.String(20), nullable=False, default="complaint")  # 'complaint' or 'suggestion'
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_category = db.Column(db.String(50), nullable=False)
    building = db.Column(db.String(100), nullable=False, index=True)
    room = db.Column(db.String(100), nullable=True)
    
    # Idempotency token to prevent double-click / repeat submits
    idempotency_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    
    # Analysis fields
    analysis_state = db.Column(
        db.String(30), nullable=False, default="pending"
    )  # 'pending', 'completed', 'needs_review', 'failed'
    suggested_category = db.Column(db.String(50), nullable=True)
    final_category = db.Column(db.String(50), nullable=True)
    suggested_priority = db.Column(db.String(30), nullable=True)  # 'Urgent review', 'High', 'Normal', 'Low'
    final_priority = db.Column(db.String(30), nullable=True)
    
    # Operational status
    status = db.Column(
        db.String(30), nullable=False, default="submitted", index=True
    )  # 'submitted', 'under_review', 'in_progress', 'resolved'

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    attachments = db.relationship("Attachment", backref="complaint", cascade="all, delete-orphan", lazy="joined")
    analysis_result = db.relationship("AnalysisResult", backref="complaint", uselist=False, cascade="all, delete-orphan")
    issue_link = db.relationship("IssueComplaintLink", backref="complaint", uselist=False)

    @property
    def display_category(self) -> str:
        return self.final_category or self.suggested_category or self.user_category

    @property
    def display_priority(self) -> str:
        return self.final_priority or self.suggested_priority or "Normal"

    def __repr__(self) -> str:
        return f"<Complaint {self.id} title='{self.title[:20]}' status={self.status}>"


class Attachment(db.Model):
    """File attachment stored outside static/."""
    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Attachment {self.id} file={self.filename}>"


class AnalysisResult(db.Model):
    """Persisted semantic and rule-based analysis metadata."""
    __tablename__ = "analysis_results"

    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(
        db.Integer, db.ForeignKey("complaints.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    model_identifier = db.Column(db.String(120), nullable=False)
    analysis_version = db.Column(db.String(20), nullable=False)
    
    # Category suggestions
    suggested_category = db.Column(db.String(50), nullable=True)
    category_similarity = db.Column(db.Float, nullable=True)  # Cosine similarity score
    category_reason = db.Column(db.Text, nullable=True)
    
    # Priority suggestions
    suggested_priority = db.Column(db.String(30), nullable=True)
    priority_reason = db.Column(db.Text, nullable=True)
    matched_phrase = db.Column(db.String(200), nullable=True)
    
    # Diagnostic flags
    is_ambiguous = db.Column(db.Boolean, nullable=False, default=False)
    is_semantic_available = db.Column(db.Boolean, nullable=False, default=True)
    
    # Serialized text embedding vector (JSON list of floats) for fast pairwise comparisons
    embedding_json = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<AnalysisResult complaint_id={self.complaint_id} cat={self.suggested_category} prio={self.suggested_priority}>"
