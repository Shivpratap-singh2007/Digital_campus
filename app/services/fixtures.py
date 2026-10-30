import os
import uuid
import logging
from datetime import datetime, timezone
from flask import current_app
from app.extensions import db
from app.models.user import User
from app.models.complaint import Complaint
from app.models.issue import Issue, IssueComplaintLink, StatusEvent
from app.models.feedback import ResolutionRound, ResolutionFeedback
from app.services.complaint_analysis import run_complaint_analysis
from app.services.security import validate_password_strength

logger = logging.getLogger(__name__)


def provision_synthetic_fixtures(
    app=None,
    admin_password: str = None,
    handler_password: str = None,
    student_password: str = None,
) -> dict:
    """
    Provisions synthetic test fixture accounts and baseline records:
    1. Synthetic Student A (verified)
    2. Synthetic Student B (verified)
    3. Synthetic Handler (verified operational desk)
    4. Synthetic Administrator (verified security director)
    5. Synthetic Unverified Student (unverified)

    Safety & Integrity Guarantees:
    - Marked with is_synthetic_fixture=True.
    - Credentials loaded strictly from environment variables or explicit parameters (no hardcoded defaults).
    - Idempotent: If account exists with the correct role, leaves password unchanged (does not overwrite on restart).
    - Fail-safe conflict handling: If existing user has a conflicting role, refuses to silently promote.
    - Idempotent fixture issues: Only provisions baseline issues/complaints if not already present.
    """
    ctx_needed = app is not None and not current_app
    ctx = app.app_context() if ctx_needed else None
    if ctx:
        ctx.push()

    try:
        # Check that is_synthetic_fixture column exists in SQLite schema
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE users ADD COLUMN is_synthetic_fixture BOOLEAN DEFAULT 0"))
                conn.commit()
        except Exception:
            pass  # Column already exists or table freshly created

        results = {
            "created": [],
            "preserved": [],
            "conflicts": [],
            "skipped": [],
        }

        resolved_admin_pw = (
            admin_password
            or os.environ.get("FIXTURE_ADMIN_PASSWORD")
            or os.environ.get("ADMIN_PASSWORD")
            or ""
        ).strip()
        resolved_handler_pw = (
            handler_password
            or os.environ.get("FIXTURE_HANDLER_PASSWORD")
            or os.environ.get("HANDLER_PASSWORD")
            or ""
        ).strip()
        resolved_student_pw = (
            student_password
            or os.environ.get("FIXTURE_STUDENT_PASSWORD")
            or os.environ.get("STUDENT_PASSWORD")
            or os.environ.get("FIXTURE_STUDENT_A_PASSWORD")
            or ""
        ).strip()

        # 1. Fixture Account Definitions
        fixture_configs = [
            {
                "key": "admin",
                "email": os.environ.get("FIXTURE_ADMIN_EMAIL", "admin@campus.edu").strip().lower(),
                "password": resolved_admin_pw,
                "full_name": os.environ.get("FIXTURE_ADMIN_NAME", "Campus Facilities Director"),
                "role": "admin",
                "is_verified": True,
            },
            {
                "key": "handler",
                "email": os.environ.get("FIXTURE_HANDLER_EMAIL", "handler@campus.edu").strip().lower(),
                "password": resolved_handler_pw,
                "full_name": os.environ.get("FIXTURE_HANDLER_NAME", "Campus Maintenance Desk"),
                "role": "handler",
                "is_verified": True,
            },
            {
                "key": "student_a",
                "email": os.environ.get("FIXTURE_STUDENT_A_EMAIL", "student.aarav@campus.edu").strip().lower(),
                "password": resolved_student_pw,
                "full_name": os.environ.get("FIXTURE_STUDENT_A_NAME", "Aarav Sharma"),
                "role": "user",
                "is_verified": True,
            },
            {
                "key": "student_b",
                "email": os.environ.get("FIXTURE_STUDENT_B_EMAIL", "student.priya@campus.edu").strip().lower(),
                "password": resolved_student_pw,
                "full_name": os.environ.get("FIXTURE_STUDENT_B_NAME", "Priya Patel"),
                "role": "user",
                "is_verified": True,
            },
            {
                "key": "unverified",
                "email": os.environ.get("FIXTURE_UNVERIFIED_EMAIL", "student.unverified@campus.edu").strip().lower(),
                "password": resolved_student_pw,
                "full_name": os.environ.get("FIXTURE_UNVERIFIED_NAME", "Unverified Student"),
                "role": "user",
                "is_verified": False,
            },
        ]

        users_by_key = {}

        for cfg in fixture_configs:
            email = cfg["email"]
            existing = User.query.filter_by(email=email).first()

            if existing:
                # Role conflict check: Never promote or alter role silently
                if existing.role != cfg["role"]:
                    msg = (
                        f"Account '{email}' exists with role '{existing.role}' "
                        f"which conflicts with requested fixture role '{cfg['role']}'. "
                        "Refusing to alter role silently."
                    )
                    logger.warning(f"[FIXTURE CONFLICT] {msg}")
                    results["conflicts"].append({"email": email, "reason": msg})
                else:
                    logger.info(f"[FIXTURE] Preserving existing '{cfg['key']}' account ({email}) without resetting password.")
                    results["preserved"].append({"key": cfg["key"], "email": email, "role": existing.role})
                users_by_key[cfg["key"]] = existing
            else:
                if not cfg["password"]:
                    msg = (
                        f"Password for '{cfg['key']}' ({email}) not provided via environment "
                        f"(FIXTURE_{cfg['key'].upper()}_PASSWORD) or parameters. Skipping creation."
                    )
                    logger.warning(f"[FIXTURE SKIPPED] {msg}")
                    results["skipped"].append({"key": cfg["key"], "email": email, "reason": msg})
                    continue

                valid_pw, pw_err = validate_password_strength(cfg["password"])
                if not valid_pw:
                    msg = f"Password for '{cfg['key']}' ({email}) does not meet requirements: {pw_err}"
                    logger.warning(f"[FIXTURE CONFLICT] {msg}")
                    results["conflicts"].append({"email": email, "reason": msg})
                    continue

                user = User(
                    email=email,
                    full_name=cfg["full_name"],
                    role=cfg["role"],
                    is_verified=cfg["is_verified"],
                    is_synthetic_fixture=True,
                )
                user.set_password(cfg["password"])
                db.session.add(user)
                db.session.commit()
                logger.info(f"[FIXTURE] Provisioned new synthetic '{cfg['key']}' account ({email}) with role '{cfg['role']}'.")
                results["created"].append({"key": cfg["key"], "email": email, "role": cfg["role"]})
                users_by_key[cfg["key"]] = user

        # 2. Provision baseline demo issues/complaints if empty
        student_a = users_by_key.get("student_a")
        student_b = users_by_key.get("student_b")
        handler = users_by_key.get("handler")

        if student_a and student_b and handler and handler.is_handler:
            _provision_baseline_complaints_and_issues(student_a, student_b, handler)

        return results

    finally:
        if ctx:
            ctx.pop()


def _provision_baseline_complaints_and_issues(student_a: User, student_b: User, handler: User):
    """Provisions baseline synthetic complaints and issues idempotently."""
    sample_complaints = [
        {
            "user": student_a,
            "type": "complaint",
            "title": "[QA TEST] Sparking socket in computer lab 102",
            "description": "The wall socket near computer bench 14 is actively sparking and emitting a burning smell. Immediate fire hazard.",
            "category": "Infrastructure",
            "building": "Computer Center / IT Labs",
            "room": "Lab 102",
        },
        {
            "user": student_b,
            "type": "complaint",
            "title": "[QA TEST] Exposed conduit live wire near bench 12",
            "description": "Exposed live wires hanging from the computer lab wall conduit near bench 12. Shock hazard.",
            "category": "Infrastructure",
            "building": "Computer Center / IT Labs",
            "room": "Lab 102",
        },
        {
            "user": student_a,
            "type": "complaint",
            "title": "[QA TEST] Water leakage in 3rd floor washroom",
            "description": "Continuous water leakage from pipe elbow flooding corridor in Academic Block A.",
            "category": "Sanitation",
            "building": "Academic Block A",
            "room": "Restroom 3B",
        },
    ]

    persisted_comps = []
    for data in sample_complaints:
        comp = Complaint.query.filter_by(title=data["title"]).first()
        if not comp:
            comp = Complaint(
                user_id=data["user"].id,
                submission_type=data["type"],
                title=data["title"],
                description=data["description"],
                user_category=data["category"],
                building=data["building"],
                room=data["room"],
                idempotency_token=uuid.uuid4().hex,
                analysis_state="pending",
                status="submitted",
            )
            db.session.add(comp)
            db.session.flush()

            status_ev = StatusEvent(
                target_type="complaint",
                target_id=comp.id,
                actor_id=data["user"].id,
                old_status="none",
                new_status="submitted",
                note="Baseline synthetic submission.",
            )
            db.session.add(status_ev)
            db.session.commit()

            # Execute rules and analysis
            run_complaint_analysis(comp)
        persisted_comps.append(comp)

    # Baseline Issue 1: Electrical hazard linking comp 1 and comp 2
    if len(persisted_comps) >= 2:
        c1, c2 = persisted_comps[0], persisted_comps[1]
        issue1 = Issue.query.filter_by(title="[QA TEST] Computer Lab 102 Electrical Hazard Group").first()
        if not issue1:
            issue1 = Issue(
                title="[QA TEST] Computer Lab 102 Electrical Hazard Group",
                description="Synthesized operational task combining lab 102 sparking socket and conduit exposed wiring.",
                category="Infrastructure",
                building="Computer Center / IT Labs",
                room="Lab 102",
                status="under_review",
                priority="Urgent review",
                created_by_user_id=handler.id,
            )
            db.session.add(issue1)
            db.session.flush()

            db.session.add(IssueComplaintLink(issue_id=issue1.id, complaint_id=c1.id, relationship_type="same_incident", linked_by_user_id=handler.id))
            db.session.add(IssueComplaintLink(issue_id=issue1.id, complaint_id=c2.id, relationship_type="same_incident", linked_by_user_id=handler.id))
            c1.status = "under_review"
            c2.status = "under_review"
            db.session.commit()

