from datetime import datetime, timezone
from app.extensions import db


class ResolutionRound(db.Model):
    """Tracks each resolution cycle for an issue."""
    __tablename__ = "resolution_rounds"

    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    round_number = db.Column(db.Integer, nullable=False, default=1)
    resolution_note = db.Column(db.Text, nullable=False)
    resolved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    # State: 'pending_feedback', 'submitter_confirmed', 'disputed', 'no_response'
    status = db.Column(db.String(30), nullable=False, default="pending_feedback", index=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    closed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    feedbacks = db.relationship("ResolutionFeedback", backref="round", cascade="all, delete-orphan", lazy="joined")
    resolved_by = db.relationship("User", foreign_keys=[resolved_by_user_id])

    def evaluate_status(self, unique_submitter_user_ids: set) -> str:
        """
        Evaluate resolution round status based on strict rules:
        - Only original submitters linked to the issue can respond.
        - Any 'partially_fixed' or 'not_fixed' flags review -> 'disputed'.
        - ALL linked unique submitters must respond 'fixed' before labeling 'submitter_confirmed'.
        - Missing responses must never count as fixed.
        - If no responses yet -> 'pending_feedback'.
        """
        if not unique_submitter_user_ids:
            return "no_response"

        # Query all feedback records directly to avoid stale relationship cache
        feedbacks = ResolutionFeedback.query.filter_by(round_id=self.id).all()
        feedback_map = {f.user_id: f.response for f in feedbacks if f.user_id in unique_submitter_user_ids}
        
        # Check if any response is disputed
        for resp in feedback_map.values():
            if resp in ("partially_fixed", "not_fixed"):
                return "disputed"

        # Check if ALL linked submitters have responded 'fixed'
        responded_users = set(feedback_map.keys())
        all_fixed = (
            responded_users == unique_submitter_user_ids
            and all(resp == "fixed" for resp in feedback_map.values())
        )
        if all_fixed:
            return "submitter_confirmed"

        if len(responded_users) == 0:
            return "pending_feedback"

        # Some responded fixed, but others haven't responded yet
        return "pending_feedback"

    def __repr__(self) -> str:
        return f"<ResolutionRound issue={self.issue_id} round={self.round_number} status={self.status}>"


class ResolutionFeedback(db.Model):
    """Feedback submitted by original submitters on a resolution round."""
    __tablename__ = "resolution_feedbacks"
    __table_args__ = (
        db.UniqueConstraint("round_id", "user_id", name="uq_round_user_feedback"),
    )

    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(
        db.Integer, db.ForeignKey("resolution_rounds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.id"), nullable=False, index=True)
    response = db.Column(
        db.String(30), nullable=False
    )  # 'fixed', 'partially_fixed', 'not_fixed'
    comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    complaint = db.relationship("Complaint", foreign_keys=[complaint_id])

    def __repr__(self) -> str:
        return f"<ResolutionFeedback round={self.round_id} user={self.user_id} resp={self.response}>"
