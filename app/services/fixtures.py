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
            or "AdminPass123!"
        ).strip()
        resolved_handler_pw = (
            handler_password
            or os.environ.get("FIXTURE_HANDLER_PASSWORD")
            or os.environ.get("HANDLER_PASSWORD")
            or "HandlerPass123!"
        ).strip()
        resolved_student_pw = (
            student_password
            or os.environ.get("FIXTURE_STUDENT_PASSWORD")
            or os.environ.get("STUDENT_PASSWORD")
            or os.environ.get("FIXTURE_STUDENT_A_PASSWORD")
            or "StudentPass123!"
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
    """Provisions comprehensive baseline synthetic complaints and issues covering R1-R9 idempotently."""
    sample_complaints = [
        # 1. Infrastructure (Hazard / High Priority)
        {
            "user": student_a,
            "type": "complaint",
            "title": "[QA TEST] Sparking socket in computer lab 102",
            "description": "The wall socket near computer bench 14 is actively sparking and emitting a burning smell. Immediate fire hazard.",
            "category": "Infrastructure",
            "building": "Computer Center / IT Labs",
            "room": "Lab 102",
        },
        # 2. Infrastructure (Hazard / Related report)
        {
            "user": student_b,
            "type": "complaint",
            "title": "[QA TEST] Exposed conduit live wire near bench 12",
            "description": "Exposed live wires hanging from the computer lab wall conduit near bench 12. Shock hazard.",
            "category": "Infrastructure",
            "building": "Computer Center / IT Labs",
            "room": "Lab 102",
        },
        # 3. Sanitation
        {
            "user": student_a,
            "type": "complaint",
            "title": "[QA TEST] Water leakage in 3rd floor washroom",
            "description": "Continuous water leakage from pipe elbow flooding corridor in Academic Block A.",
            "category": "Sanitation",
            "building": "Academic Block A",
            "room": "Restroom 3B",
        },
        # 4. Academics (Facilities)
        {
            "user": student_b,
            "type": "complaint",
            "title": "[QA TEST] Overhead projector display flickering in Lecture Hall 101",
            "description": "The ceiling projector in LH-101 has severe display flickering and green tint during lectures, making presentation slides unreadable.",
            "category": "Academics",
            "building": "Academic Block A",
            "room": "LH-101",
        },
        # 5. Academics (Core Academic Administration / Course Scheduling Conflict)
        {
            "user": student_a,
            "type": "complaint",
            "title": "[QA TEST] Timetable clash: CS301 Data Structures and MATH204 Discrete Math overlap",
            "description": "Both mandatory third-semester lecture CS301 (Data Structures) and prerequisite MATH204 (Discrete Mathematics) are simultaneously scheduled for Tuesday 10:00 AM - 11:30 AM in the published autumn timetable, preventing sophomore students from attending required lectures.",
            "category": "Academics",
            "building": "Academic Block A",
            "room": "Dean Academic Office / LH-A",
        },
        # 6. Student Services
        {
            "user": student_a,
            "type": "complaint",
            "title": "[QA TEST] Dining hall meal shortage during late dinner hours",
            "description": "Hostel central mess consistently exhausts hot meal portions before 9:00 PM, leaving late-returning students without dinner.",
            "category": "Student services",
            "building": "Hostel Block 1 / Mess",
            "room": "Dining Hall",
        },
        # 7. IT / Connectivity
        {
            "user": student_b,
            "type": "complaint",
            "title": "[QA TEST] Campus WiFi drops connections in Central Library reading hall",
            "description": "The Eduroam / CampusWiFi connection repeatedly disconnects and requires re-authentication every ten minutes in the 2nd floor library.",
            "category": "IT / connectivity",
            "building": "Central Library",
            "room": "Reading Room 2A",
        },
        # 8. Explicit Suggestion (Non-physical enhancement)
        {
            "user": student_a,
            "type": "suggestion",
            "title": "[QA TEST] Suggestion: 24/7 Automated Book Drop Box for Central Library",
            "description": "Proposal to install an automated external RFID return kiosk at the library entrance so students can return borrowed books 24/7 without desk staff presence.",
            "category": "Student services",
            "building": "Central Library",
            "room": "Exterior Entrance",
        },
    ]

    comps = {}
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

            # Execute rules and semantic analysis
            run_complaint_analysis(comp)
        comps[data["title"]] = comp

    # Baseline Issue 1: Multi-report Recurring Hazard Group (Status: under_review, Priority: Urgent review)
    c1 = comps.get("[QA TEST] Sparking socket in computer lab 102")
    c2 = comps.get("[QA TEST] Exposed conduit live wire near bench 12")
    if c1 and c2:
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

    # Baseline Issue 2: Resolved Issue with Confirmed Submitter Feedback (Status: resolved)
    c6 = comps.get("[QA TEST] Campus WiFi drops connections in Central Library reading hall")
    if c6:
        issue2 = Issue.query.filter_by(title="[QA TEST] Central Library 2nd Floor WiFi Access Point").first()
        if not issue2:
            issue2 = Issue(
                title="[QA TEST] Central Library 2nd Floor WiFi Access Point",
                description="Synthesized task: Replace flaky access point PoE injector on Central Library 2nd floor.",
                category="IT / connectivity",
                building="Central Library",
                room="Reading Room 2A",
                status="resolved",
                priority="Normal",
                created_by_user_id=handler.id,
            )
            db.session.add(issue2)
            db.session.flush()

            db.session.add(IssueComplaintLink(issue_id=issue2.id, complaint_id=c6.id, relationship_type="same_incident", linked_by_user_id=handler.id))
            c6.status = "resolved"

            # Add ResolutionRound (submitter_confirmed)
            rr = ResolutionRound(
                issue_id=issue2.id,
                round_number=1,
                resolution_note="Replaced faulty PoE injector and verified WiFi signal throughput across reading hall.",
                resolved_by_user_id=handler.id,
                status="submitter_confirmed",
                closed_at=datetime.now(timezone.utc),
            )
            db.session.add(rr)
            db.session.flush()

            rf = ResolutionFeedback(
                round_id=rr.id,
                user_id=student_b.id,
                complaint_id=c6.id,
                response="fixed",
                comments="Tested connection during afternoon study session; WiFi is now stable and fast.",
            )
            db.session.add(rf)
            db.session.commit()

    # Baseline Issue 3: In-Progress Issue with Full Disputed & Reopened Lifecycle (Status: in_progress)
    c3 = comps.get("[QA TEST] Water leakage in 3rd floor washroom")
    if c3:
        issue3 = Issue.query.filter_by(title="[QA TEST] Academic Block A 3rd Floor Plumbing Leak").first()
        if not issue3:
            issue3 = Issue(
                title="[QA TEST] Academic Block A 3rd Floor Plumbing Leak",
                description="Synthesized task: Fix pipe elbow leak in Restroom 3B corridor.",
                category="Sanitation",
                building="Academic Block A",
                room="Restroom 3B",
                status="submitted",
                priority="Normal",
                created_by_user_id=handler.id,
            )
            db.session.add(issue3)
            db.session.flush()

            # 1. Link complaint to issue
            db.session.add(IssueComplaintLink(
                issue_id=issue3.id,
                complaint_id=c3.id,
                relationship_type="same_incident",
                linked_by_user_id=handler.id,
            ))

            # 2. Transition from submitted -> in_progress (initial maintenance assignment)
            issue3.status = "in_progress"
            c3.status = "in_progress"
            db.session.add(StatusEvent(
                target_type="issue",
                target_id=issue3.id,
                actor_id=handler.id,
                old_status="submitted",
                new_status="in_progress",
                note="Assigned to campus plumbing maintenance crew for on-site inspection.",
            ))
            db.session.add(StatusEvent(
                target_type="complaint",
                target_id=c3.id,
                actor_id=handler.id,
                old_status="submitted",
                new_status="in_progress",
                note="Linked to Master Issue #3 and assigned for inspection.",
            ))

            # 3. Handler completes initial repair attempt -> resolved
            issue3.status = "resolved"
            c3.status = "resolved"
            db.session.add(StatusEvent(
                target_type="issue",
                target_id=issue3.id,
                actor_id=handler.id,
                old_status="in_progress",
                new_status="resolved",
                note="Maintenance marked resolved: Tightened coupling seal on main elbow joint.",
            ))
            db.session.add(StatusEvent(
                target_type="complaint",
                target_id=c3.id,
                actor_id=handler.id,
                old_status="in_progress",
                new_status="resolved",
                note="Maintenance marked issue resolved; opened for submitter verification.",
            ))

            # 4. Add ResolutionRound (disputed)
            rr3 = ResolutionRound(
                issue_id=issue3.id,
                round_number=1,
                resolution_note="Tightened coupling seal on main elbow joint.",
                resolved_by_user_id=handler.id,
                status="disputed",
            )
            db.session.add(rr3)
            db.session.flush()

            # 5. Eligible original submitter submits not_fixed feedback
            rf3 = ResolutionFeedback(
                round_id=rr3.id,
                user_id=student_a.id,
                complaint_id=c3.id,
                response="not_fixed",
                comments="Water is still actively dripping from the rear seal onto floor tiles.",
            )
            db.session.add(rf3)

            # 6. Authorized handler reopens issue back to in_progress following dispute
            issue3.status = "in_progress"
            c3.status = "in_progress"
            db.session.add(StatusEvent(
                target_type="issue",
                target_id=issue3.id,
                actor_id=handler.id,
                old_status="resolved",
                new_status="in_progress",
                note="Reopened by maintenance handler for replacement parts: Submitter verified fix failed (leak persists).",
            ))
            db.session.add(StatusEvent(
                target_type="complaint",
                target_id=c3.id,
                actor_id=handler.id,
                old_status="resolved",
                new_status="in_progress",
                note="Reopened following dispute feedback from submitter.",
            ))
            db.session.commit()

