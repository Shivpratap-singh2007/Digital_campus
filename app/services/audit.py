import logging
from flask import request
from app.extensions import db
from app.models.audit import AuditEvent
from app.models.complaint import Complaint
from app.models.user import User

logger = logging.getLogger(__name__)


def reveal_complaint_submitter(
    admin_user: User, complaint_id: int, justification: str
) -> tuple[bool, str, dict | None]:
    """
    Executes identity reveal under strict privacy controls:
    1. Validates admin permission.
    2. Enforces non-empty, meaningful justification.
    3. Commits an AuditEvent record FIRST before retrieving/returning identity.
    4. If audit persistence fails, aborts and DOES NOT reveal identity.
    5. CRITICAL: Never logs disclosed personal data into the audit table.
    """
    if not admin_user or admin_user.role != "admin":
        return False, "Access denied: Only authorized administrators can reveal submitter identity.", None

    if not justification or len(justification.strip()) < 10:
        return False, "A specific operational justification (minimum 10 characters) is required.", None

    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return False, "Complaint not found.", None

    client_ip = request.remote_addr if request else None

    # Step 1: Create and commit AuditEvent
    try:
        audit = AuditEvent(
            actor_id=admin_user.id,
            action="reveal_identity",
            target_type="complaint",
            target_id=complaint.id,
            justification=justification.strip(),
            ip_address=client_ip,
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Audit log commitment failed during identity reveal attempt: {e}")
        return False, "Security audit log failed to persist. Identity cannot be revealed.", None

    # Step 2: Now that audit is committed, return submitter identity
    submitter = complaint.submitter
    if not submitter:
        return False, "Submitter account no longer exists in database.", None

    disclosed_info = {
        "user_id": submitter.id,
        "full_name": submitter.full_name,
        "email": submitter.email,
        "is_verified": submitter.is_verified,
        "audit_id": audit.id,
    }

    logger.info(
        f"Admin #{admin_user.id} revealed identity of Complaint #{complaint.id} under Audit #{audit.id}"
    )
    return True, "Identity revealed and logged to audit trail.", disclosed_info
