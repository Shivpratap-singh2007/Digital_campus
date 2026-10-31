import os
import sys
import uuid
import logging
from datetime import datetime, timezone, timedelta

# Ensure workspace root is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.complaint import Complaint, AnalysisResult
from app.models.issue import Issue, IssueComplaintLink, StatusEvent
from app.models.feedback import ResolutionRound
from app.services.ai_pipeline import classify_issue, detect_priority

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_data")


def seed_mock_demonstration_data(app=None) -> dict:
    """
    Populates campusvoice.db with realistic, diverse mock records demonstrating:
    1. Critical / Emergency Issues (P1 priority detection)
    2. Duplicate / Related Issues Pair 1 (Sanitation & Plumbing - Water cooler)
    3. Duplicate / Related Issues Pair 2 (Academics & Classroom - Projector HDMI)
    4. Resolved Issues (Populating analytics charts & resolution rates)
    5. Hinglish Sample (Multi-dialect NLP testing)
    
    Guarantees:
    - Idempotent: checks for existing titles/tokens before inserting.
    - Preserves foreign keys, timestamps, and status events.
    """
    if app is None:
        app = create_app()

    with app.app_context():
        db.create_all()

        # 1. Fetch or create users
        users = {u.email: u for u in User.query.all()}

        def get_or_create_user(email: str, name: str, role: str) -> User:
            if email in users:
                return users[email]
            u = User(
                email=email,
                full_name=name,
                role=role,
                is_verified=True,
            )
            u.set_password("DemoPassword123!")
            db.session.add(u)
            db.session.flush()
            users[email] = u
            return u

        admin = get_or_create_user("admin@campus.edu", "Campus Facilities Director", "admin")
        handler = get_or_create_user("handler@campus.edu", "Campus Maintenance Desk", "handler")
        student_aarav = get_or_create_user("student.aarav@campus.edu", "Aarav Sharma - Roll #21CS04", "user")
        student_priya = get_or_create_user("student.priya@campus.edu", "Priya Patel - Roll #22EE18", "user")
        student_rohan = get_or_create_user("student.rohan@campus.edu", "Rohan Verma - Roll #23ME45", "user")
        student_ananya = get_or_create_user("student.ananya@campus.edu", "Ananya Deshmukh - Roll #21CE12", "user")
        student_vikram = get_or_create_user("student.vikram@campus.edu", "Vikram Singh - Roll #22CS91", "user")
        student_sneha = get_or_create_user("student.sneha@campus.edu", "Sneha Reddy - Roll #23IT08", "user")

        now = datetime.now(timezone.utc)
        created_records = []

        # Helper to ensure complaint exists idempotently
        def ensure_complaint(
            title: str,
            description: str,
            user: User,
            building: str,
            room: str,
            status: str,
            created_at: datetime,
            forced_category: str = None,
            forced_priority: str = None,
            token_prefix: str = "mock",
        ) -> Complaint:
            existing = Complaint.query.filter_by(title=title).first()
            if existing:
                return existing

            ai_cat = forced_category or classify_issue(f"{title}\n{description}")
            ai_prio = forced_priority or detect_priority(f"{title}\n{description}")

            comp = Complaint(
                user_id=user.id,
                submission_type="complaint",
                title=title,
                description=description,
                user_category=ai_cat,
                suggested_category=ai_cat,
                final_category=ai_cat,
                building=building,
                room=room,
                idempotency_token=f"{token_prefix}-{uuid.uuid4().hex[:12]}",
                suggested_priority=ai_prio,
                final_priority=ai_prio,
                analysis_state="completed",
                status=status,
                created_at=created_at,
                updated_at=created_at,
            )
            db.session.add(comp)
            db.session.flush()

            # Add analysis result
            analysis = AnalysisResult(
                complaint_id=comp.id,
                model_identifier="CampusVoice AI Pipeline v1.2",
                analysis_version="1.2.0",
                suggested_category=ai_cat,
                category_similarity=0.94,
                category_reason=f"Categorized into '{ai_cat}' via keyword and semantic analysis.",
                suggested_priority=ai_prio,
                priority_reason=f"Priority evaluated as {ai_prio} based on urgency detection.",
                matched_phrase=title[:30],
                is_ambiguous=False,
                is_semantic_available=True,
                created_at=created_at,
            )
            db.session.add(analysis)

            # Add creation status event
            db.session.add(StatusEvent(
                target_type="complaint",
                target_id=comp.id,
                actor_id=user.id,
                old_status="none",
                new_status="submitted",
                note="Initial verified user submission.",
                created_at=created_at,
            ))
            if status != "submitted":
                db.session.add(StatusEvent(
                    target_type="complaint",
                    target_id=comp.id,
                    actor_id=handler.id,
                    old_status="submitted",
                    new_status=status,
                    note=f"Status transitioned to '{status}' by maintenance desk.",
                    created_at=created_at + timedelta(minutes=15),
                ))

            created_records.append(f"Complaint: #{comp.id} {title}")
            return comp

        # Helper to ensure master issue exists idempotently
        def ensure_master_issue(
            title: str,
            description: str,
            category: str,
            priority: str,
            building: str,
            room: str,
            status: str,
            created_at: datetime,
            seed_complaints: list[Complaint] = None,
            resolution_note: str = None,
        ) -> Issue:
            existing = Issue.query.filter_by(title=title).first()
            if existing:
                return existing

            issue = Issue(
                title=title,
                description=description,
                category=category,
                priority=priority,
                building=building,
                room=room,
                status=status,
                created_by_user_id=handler.id,
                created_at=created_at,
                updated_at=created_at + timedelta(hours=1),
            )
            db.session.add(issue)
            db.session.flush()

            # Add creation event
            db.session.add(StatusEvent(
                target_type="issue",
                target_id=issue.id,
                actor_id=handler.id,
                old_status="none",
                new_status=status,
                note="Master issue synthesized by facilities desk.",
                created_at=created_at,
            ))

            # Link seed complaints
            if seed_complaints:
                for c in seed_complaints:
                    existing_link = IssueComplaintLink.query.filter_by(issue_id=issue.id, complaint_id=c.id).first()
                    if not existing_link:
                        link = IssueComplaintLink(
                            issue_id=issue.id,
                            complaint_id=c.id,
                            relationship_type="same_incident",
                            linked_by_user_id=handler.id,
                            created_at=created_at + timedelta(minutes=10),
                        )
                        db.session.add(link)
                        c.status = status
                        db.session.add(StatusEvent(
                            target_type="complaint",
                            target_id=c.id,
                            actor_id=handler.id,
                            old_status="submitted",
                            new_status=status,
                            note=f"Grouped into Master Issue #{issue.id}.",
                            created_at=created_at + timedelta(minutes=10),
                        ))

            # If resolved, add resolution round
            if status == "resolved":
                round_obj = ResolutionRound(
                    issue_id=issue.id,
                    round_number=1,
                    resolution_note=resolution_note or "Issue resolved and verified by maintenance staff.",
                    resolved_by_user_id=handler.id,
                    status="closed",
                    created_at=created_at + timedelta(hours=4),
                    closed_at=created_at + timedelta(hours=6),
                )
                db.session.add(round_obj)
                db.session.add(StatusEvent(
                    target_type="issue",
                    target_id=issue.id,
                    actor_id=handler.id,
                    old_status="in_progress",
                    new_status="resolved",
                    note=resolution_note or "Resolved and confirmed.",
                    created_at=created_at + timedelta(hours=4),
                ))

            created_records.append(f"Issue: #{issue.id} {title}")
            return issue

        # ======================================================================
        # RECORD 1: Critical / Emergency Issue (P1 - Priority Detection)
        # ======================================================================
        c1 = ensure_complaint(
            title="Switchboard sparking and emitting smoke",
            description="Heavy electric sparking near switchboard in Computer Lab 3. Burning smell present.",
            user=student_aarav,
            building="Computer Center / IT Labs",
            room="Computer Lab 3",
            status="in_progress",
            created_at=now - timedelta(hours=3),
            forced_category="Electrical & Hardware",
            forced_priority="Critical (P1)",
            token_prefix="emergency-p1",
        )
        ensure_master_issue(
            title="Computer Lab 3 Electrical Switchboard Sparking & Smoke Hazard",
            description="Emergency electrical team dispatched. Power feed to Computer Lab 3 isolated; replacing charred main breaker and switchboard socket.",
            category="Electrical & Hardware",
            priority="Critical (P1)",
            building="Computer Center / IT Labs",
            room="Computer Lab 3",
            status="in_progress",
            created_at=now - timedelta(hours=3),
            seed_complaints=[c1],
        )

        # ======================================================================
        # RECORDS 2 & 3: Duplicate Pair 1 (Sanitation & Plumbing - Water cooler)
        # ======================================================================
        c2a = ensure_complaint(
            title="Water cooler on 2nd floor leaking",
            description="Drinking water dispenser outside Room 204 is leaking water all over the corridor.",
            user=student_priya,
            building="Academic Block A",
            room="Corridor near Room 204",
            status="submitted",
            created_at=now - timedelta(hours=6),
            forced_category="Sanitation & Plumbing",
            forced_priority="Medium (P2)",
            token_prefix="dup1-a",
        )
        c2b = ensure_complaint(
            title="Corridor flooded due to drinking water tap",
            description="2nd floor washroom/cooler water tap is loose and water is pooling on the floor.",
            user=student_rohan,
            building="Academic Block A",
            room="2nd Floor Water Station",
            status="submitted",
            created_at=now - timedelta(hours=5),
            forced_category="Sanitation & Plumbing",
            forced_priority="Medium (P2)",
            token_prefix="dup1-b",
        )
        # Grouped together under Master Issue
        ensure_master_issue(
            title="Academic Block A 2nd Floor Water Cooler Leak & Corridor Flooding",
            description="Plumbing work order generated for leaking water dispenser shutoff valve outside Room 204 causing corridor water pooling.",
            category="Sanitation & Plumbing",
            priority="Medium (P2)",
            building="Academic Block A",
            room="Room 204 Corridor",
            status="submitted",
            created_at=now - timedelta(hours=6),
            seed_complaints=[c2a, c2b],
        )

        # ======================================================================
        # RECORDS 4 & 5: Duplicate Pair 2 (Academics & Classroom - Projector HDMI)
        # ======================================================================
        c3a = ensure_complaint(
            title="Projector not displaying HDMI signal in Room 302",
            description="Projector screen flickering red and blue during lectures.",
            user=student_ananya,
            building="Academic Block B",
            room="Room 302",
            status="under_review",
            created_at=now - timedelta(days=1, hours=2),
            forced_category="Academics & Classroom",
            forced_priority="Low (P3)",
            token_prefix="dup2-a",
        )
        c3b = ensure_complaint(
            title="Room 302 display projector cable broken",
            description="Cannot connect laptop to projector in 302 hall, HDMI pin broken.",
            user=student_vikram,
            building="Academic Block B",
            room="Room 302 Hall",
            status="under_review",
            created_at=now - timedelta(hours=22),
            forced_category="Academics & Classroom",
            forced_priority="Low (P3)",
            token_prefix="dup2-b",
        )
        # Grouped together under Master Issue
        ensure_master_issue(
            title="Academic Block B Room 302 Projector Display Signal & Broken HDMI Pin",
            description="Classroom AV technician reviewing damaged HDMI adapter and projector optical sync in Room 302.",
            category="Academics & Classroom",
            priority="Low (P3)",
            building="Academic Block B",
            room="Room 302",
            status="under_review",
            created_at=now - timedelta(days=1, hours=2),
            seed_complaints=[c3a, c3b],
        )

        # ======================================================================
        # RECORDS 6 & 7: Resolved Issues (Analytics Charts & Resolution Rates)
        # ======================================================================
        c4a = ensure_complaint(
            title="Broken wooden bench in Reading Hall",
            description="Damaged bench with sharp edge removed.",
            user=student_sneha,
            building="Central Library",
            room="Reading Hall",
            status="resolved",
            created_at=now - timedelta(days=3),
            forced_category="General Infrastructure",
            forced_priority="Low (P3)",
            token_prefix="res-infra",
        )
        ensure_master_issue(
            title="Central Library Reading Hall Damaged Bench Replacement",
            description="Damaged wooden bench inspected; hazardous sharp splintered armrest removed from public study hall.",
            category="General Infrastructure",
            priority="Low (P3)",
            building="Central Library",
            room="Reading Hall",
            status="resolved",
            created_at=now - timedelta(days=3),
            seed_complaints=[c4a],
            resolution_note="Damaged bench with sharp edge removed and replaced with new ergonomically certified seating.",
        )

        c4b = ensure_complaint(
            title="Ceiling tube light fused in Library Wing B",
            description="Replaced with new LED tube light.",
            user=student_aarav,
            building="Central Library",
            room="Wing B",
            status="resolved",
            created_at=now - timedelta(days=4),
            forced_category="Electrical & Hardware",
            forced_priority="Low (P3)",
            token_prefix="res-elec",
        )
        ensure_master_issue(
            title="Central Library Wing B Fused Tube Light Replacement",
            description="Reported non-functional ceiling tube light in study cubicle area of Wing B.",
            category="Electrical & Hardware",
            priority="Low (P3)",
            building="Central Library",
            room="Wing B",
            status="resolved",
            created_at=now - timedelta(days=4),
            seed_complaints=[c4b],
            resolution_note="Replaced with new 20W LED tube light. Illumination restored.",
        )

        # ======================================================================
        # RECORD 8: Hinglish Sample (Testing Multi-dialect Text)
        # ======================================================================
        c5 = ensure_complaint(
            title="Hostel mess water cooler kharab hai",
            description="Ground floor water cooler se thanda paani nahi aa raha hai.",
            user=student_rohan,
            building="Boys Hostel 1",
            room="Ground Floor Mess",
            status="submitted",
            created_at=now - timedelta(hours=1, minutes=30),
            forced_category="Sanitation & Plumbing",
            forced_priority="Medium (P2)",
            token_prefix="hinglish-cool",
        )
        ensure_master_issue(
            title="Boys Hostel 1 Mess Water Cooler Compressor & Cooling Failure",
            description="Water cooler in mess dispensing warm water due to suspected compressor coolant issue.",
            category="Sanitation & Plumbing",
            priority="Medium (P2)",
            building="Boys Hostel 1",
            room="Ground Floor Mess",
            status="submitted",
            created_at=now - timedelta(hours=1, minutes=30),
            seed_complaints=[c5],
        )

        db.session.commit()
        logger.info(f"Seeding completed successfully: {len(created_records)} records processed.")
        return {
            "success": True,
            "created_records": created_records,
            "total_complaints": Complaint.query.count(),
            "total_issues": Issue.query.count(),
        }


if __name__ == "__main__":
    result = seed_mock_demonstration_data()
    print("=" * 60)
    print(" CampusVoice Demonstration Data Seed Complete")
    print(f" Total Complaints in DB: {result['total_complaints']}")
    print(f" Total Master Issues in DB: {result['total_issues']}")
    print(f" New Records Added in this run: {len(result['created_records'])}")
    for rec in result["created_records"]:
        print(f"  + {rec}")
    print("=" * 60)

