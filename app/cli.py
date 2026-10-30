import click
from datetime import datetime, timezone
import uuid
from flask import Blueprint
from app.extensions import db
from app.models import (
    User,
    Complaint,
    Issue,
    IssueComplaintLink,
    StatusEvent,
    ResolutionRound,
    ResolutionFeedback,
    AnalysisResult,
)
from app.services.complaint_analysis import run_complaint_analysis

cli_bp = Blueprint("campus_cli", __name__)


@cli_bp.cli.command("warmup-model")
def warmup_model():
    """Warms up and verifies the sentence-transformer embedding model."""
    import os
    os.environ.pop("HF_HUB_OFFLINE", None)
    os.environ.pop("TRANSFORMERS_OFFLINE", None)
    click.echo("Warming up semantic embedding model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2...")
    from app.services.semantic import semantic_engine
    # Force reload attempt
    semantic_engine._load_attempted = False
    if semantic_engine.is_available:
        click.echo("Embedding model loaded and ready! Semantic clustering is active.")
    else:
        click.echo(f"Semantic model could not be loaded: {semantic_engine.load_error}")


@cli_bp.cli.command("create-admin")
@click.option("--email", default="admin@campus.edu", help="Admin email address.")
@click.option("--password", default="AdminSecure2026!", help="Admin account password.")
@click.option("--name", default="Campus Security Admin", help="Admin full name.")
def create_admin(email, password, name):
    """Creates a trusted administrator account via CLI."""
    email_clean = email.strip().lower()
    user = User.query.filter_by(email=email_clean).first()
    if user:
        user.role = "admin"
        user.is_verified = True
        user.full_name = name
        user.set_password(password)
        db.session.commit()
        click.echo(f"Existing user '{email_clean}' updated to Administrator role.")
    else:
        admin_user = User(
            email=email_clean,
            full_name=name,
            role="admin",
            is_verified=True,
        )
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()
        click.echo(f"Administrator account '{email_clean}' created successfully.")


@cli_bp.cli.command("create-handler")
@click.option("--email", default="handler@campus.edu", help="Handler email address.")
@click.option("--password", default="HandlerPass2026!", help="Handler account password.")
@click.option("--name", default="Facilities Operations Desk", help="Handler full name.")
def create_handler(email, password, name):
    """Creates an operations handler account via CLI."""
    email_clean = email.strip().lower()
    user = User.query.filter_by(email=email_clean).first()
    if user:
        user.role = "handler"
        user.is_verified = True
        user.full_name = name
        user.set_password(password)
        db.session.commit()
        click.echo(f"Existing user '{email_clean}' updated to Handler role.")
    else:
        handler_user = User(
            email=email_clean,
            full_name=name,
            role="handler",
            is_verified=True,
        )
        handler_user.set_password(password)
        db.session.add(handler_user)
        db.session.commit()
        click.echo(f"Handler account '{email_clean}' created successfully.")


@cli_bp.cli.command("seed-demo")
def seed_demo():
    """Populates database with synthetic demo users, complaints, and resolution feedback."""
    click.echo("Seeding synthetic demo data...")

    # 1. Ensure Admin and Handler exist
    admin = User.query.filter_by(email="admin@campus.edu").first()
    if not admin:
        admin = User(email="admin@campus.edu", full_name="Campus Facilities Director", role="admin", is_verified=True)
        admin.set_password("AdminPass123!")
        db.session.add(admin)

    handler = User.query.filter_by(email="handler@campus.edu").first()
    if not handler:
        handler = User(email="handler@campus.edu", full_name="Campus Maintenance Desk", role="handler", is_verified=True)
        handler.set_password("HandlerPass123!")
        db.session.add(handler)

    # 2. Synthetic Students
    student1 = User.query.filter_by(email="student.aarav@campus.edu").first()
    if not student1:
        student1 = User(email="student.aarav@campus.edu", full_name="Aarav Sharma", role="user", is_verified=True)
        student1.set_password("StudentPass123!")
        db.session.add(student1)

    student2 = User.query.filter_by(email="student.priya@campus.edu").first()
    if not student2:
        student2 = User(email="student.priya@campus.edu", full_name="Priya Patel", role="user", is_verified=True)
        student2.set_password("StudentPass123!")
        db.session.add(student2)

    student3 = User.query.filter_by(email="student.rohan@campus.edu").first()
    if not student3:
        student3 = User(email="student.rohan@campus.edu", full_name="Rohan Verma", role="user", is_verified=True)
        student3.set_password("StudentPass123!")
        db.session.add(student3)

    db.session.commit()

    # 3. Create Synthetic Complaints
    demo_complaints_data = [
        {
            "user": student1,
            "type": "complaint",
            "title": "Sparking socket in computer lab",
            "description": "The electrical wall outlet near workstation 14 has a sparking socket and smells like burnt plastic whenever a charger is plugged in. Potential fire hazard.",
            "category": "Infrastructure",
            "building": "Computer Center / IT Labs",
            "room": "Lab 102",
        },
        {
            "user": student2,
            "type": "complaint",
            "title": "Loose electrical wires exposed near lab power strip",
            "description": "Exposed live wire hanging out of the power conduit adjacent to bench 12 in the computer lab. High risk of shock.",
            "category": "Infrastructure",
            "building": "Computer Center / IT Labs",
            "room": "Lab 102",
        },
        {
            "user": student3,
            "type": "complaint",
            "title": "Water leakage in 3rd floor washroom",
            "description": "Continuous water leakage from washbasin pipe flooding the corridor floor near the physics department.",
            "category": "Sanitation",
            "building": "Academic Block A",
            "room": "Restroom 3B",
        },
        {
            "user": student1,
            "type": "complaint",
            "title": "Hostel Wi-Fi disconnected on 2nd floor",
            "description": "The campus Wi-Fi access point in corridor B has been offline since last night. No internet connectivity for homework.",
            "category": "IT/connectivity",
            "building": "Boys Hostel 1",
            "room": "Floor 2 Wing B",
        },
        {
            "user": student2,
            "type": "suggestion",
            "title": "Add compost bins outside cafeteria",
            "description": "Suggestion to install segregated food waste compost bins next to the main dining hall exits to improve campus sustainability.",
            "category": "Student services",
            "building": "Main Cafeteria & Food Court",
            "room": "Main Entrance",
        },
        {
            "user": student3,
            "type": "complaint",
            "title": "Projector not working in Lecture Hall 4",
            "description": "The ceiling projector flashes blue and turns off during class presentations. Audio speakers also buzzing.",
            "category": "Academics",
            "building": "Academic Block B",
            "room": "LH-4",
        },
    ]

    created_complaints = []
    for data in demo_complaints_data:
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
                note="Initial demo submission.",
            )
            db.session.add(status_ev)
            db.session.commit()

            # Run analysis
            run_complaint_analysis(comp)
            created_complaints.append(comp)
        else:
            created_complaints.append(comp)

    # 4. Synthesize an Issue for Electrical Hazard (combining complaint 1 and complaint 2)
    comp1 = created_complaints[0]
    comp2 = created_complaints[1]

    electrical_issue = Issue.query.filter_by(title="Computer Lab 102 Electrical Socket & Conduit Wiring Hazard").first()
    if not electrical_issue:
        electrical_issue = Issue(
            title="Computer Lab 102 Electrical Socket & Conduit Wiring Hazard",
            description="Multiple reports of sparking wall outlets and exposed live wires in Computer Lab 102 near workstations 12-14. Electrician dispatched to isolate circuit breaker.",
            category="Infrastructure",
            building="Computer Center / IT Labs",
            room="Lab 102",
            status="under_review",
            priority="Urgent review",
            created_by_user_id=handler.id,
        )
        db.session.add(electrical_issue)
        db.session.flush()

        # Link comp1 & comp2
        db.session.add(IssueComplaintLink(issue_id=electrical_issue.id, complaint_id=comp1.id, relationship_type="same_incident", linked_by_user_id=handler.id))
        db.session.add(IssueComplaintLink(issue_id=electrical_issue.id, complaint_id=comp2.id, relationship_type="same_incident", linked_by_user_id=handler.id))
        
        comp1.status = "under_review"
        comp2.status = "under_review"
        db.session.commit()

    # 5. Synthesize a Resolved Issue with Feedback Demonstration (Complaint 3: washroom leak)
    comp3 = created_complaints[2]
    plumbing_issue = Issue.query.filter_by(title="Academic Block A 3rd Floor Washroom Pipe Leak").first()
    if not plumbing_issue:
        plumbing_issue = Issue(
            title="Academic Block A 3rd Floor Washroom Pipe Leak",
            description="Plumbing technician replaced the broken PVC elbow joint and resealed the washbasin inlet on 3rd floor washroom.",
            category="Sanitation",
            building="Academic Block A",
            room="Restroom 3B",
            status="resolved",
            priority="High",
            created_by_user_id=handler.id,
        )
        db.session.add(plumbing_issue)
        db.session.flush()

        db.session.add(IssueComplaintLink(issue_id=plumbing_issue.id, complaint_id=comp3.id, relationship_type="same_incident", linked_by_user_id=handler.id))
        comp3.status = "resolved"

        # Create resolution round
        round1 = ResolutionRound(
            issue_id=plumbing_issue.id,
            round_number=1,
            resolution_note="Replaced ruptured elbow joint and tested water pressure for 30 minutes without leaks.",
            resolved_by_user_id=handler.id,
            status="submitter_confirmed",
        )
        db.session.add(round1)
        db.session.flush()

        # Add submitter feedback from student3 confirming fix
        feedback1 = ResolutionFeedback(
            round_id=round1.id,
            user_id=student3.id,
            complaint_id=comp3.id,
            response="fixed",
            comments="Verified the tap and sink after morning class, no water on the floor anymore.",
        )
        db.session.add(feedback1)
        db.session.commit()

    click.echo("Synthetic demo data successfully populated!")
    click.echo("Demo accounts:")
    click.echo(" - Admin:   admin@campus.edu / AdminPass123!")
    click.echo(" - Handler: handler@campus.edu / HandlerPass123!")
    click.echo(" - Student: student.aarav@campus.edu / StudentPass123!")
    click.echo(" - Student: student.priya@campus.edu / StudentPass123!")
    click.echo(" - Student: student.rohan@campus.edu / StudentPass123!")
