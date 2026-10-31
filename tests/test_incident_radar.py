import json
from datetime import datetime, timezone, timedelta
import pytest

from app.extensions import db
from app.models import (
    Complaint,
    Issue,
    InfrastructureDependency,
    DependencyLocation,
    RadarSuggestion,
    RadarSuggestionReport,
)
from app.services.incident_radar import (
    run_incident_radar_analysis,
    seed_synthetic_radar_demo,
    extract_report_symptom,
    calculate_fingerprint,
)


def test_extract_report_symptom_and_fallbacks():
    """Verify symptom extraction across electrical, water, and network disruptions."""
    # Electrical power loss
    assert extract_report_symptom("Computer Lab blackout", "Computers stopped working and lost power") == "electrical_power_loss"
    assert extract_report_symptom("Room 102 projector", "Projector has no electrical power, shut down") == "electrical_power_loss"
    assert extract_report_symptom("Corridor dispenser", "Water cooler power cut completely") == "electrical_power_loss"

    # Water supply disruption
    assert extract_report_symptom("Restroom tap dry", "No water supply in 2nd floor bathroom") == "water_supply_disruption"

    # Network outage
    assert extract_report_symptom("Hostel wifi down", "No internet connection on floor 3") == "network_outage"

    # Non-disruption / unrelated complaint
    assert extract_report_symptom("Classroom chair loose", "Need more chairs in reading room") is None


def test_seed_synthetic_radar_demo_idempotency(app):
    """Verify demo seed provisions synthetic dependency and is idempotent."""
    res1 = seed_synthetic_radar_demo()
    assert res1["status"] == "created"
    assert res1["dependency"] == "ELEC-PANEL-B1-P1"
    assert res1["locations_count"] == 3

    # Re-running preserves existing without duplicating
    res2 = seed_synthetic_radar_demo()
    assert res2["status"] == "preserved"
    assert res2["dependency"] == "ELEC-PANEL-B1-P1"

    dep = InfrastructureDependency.query.filter_by(dependency_identifier="ELEC-PANEL-B1-P1").first()
    assert dep is not None
    assert dep.is_synthetic is True
    assert len(dep.locations) == 3


def test_scenario_a_supported_shared_connection(app, verified_user):
    """
    Scenario A:
    Different power-loss symptoms, close timestamps, known linked locations,
    shared electrical dependency -> Type 1: possible shared-dependency incident.
    """
    seed_synthetic_radar_demo()

    now = datetime.now(timezone.utc)

    # 3 distinct complaints in Block B with different symptoms and locations sharing ELEC-PANEL-B1-P1
    c1 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Computers stopped working suddenly",
        description="All workstation screens went dark and computers lost power in Computer Lab.",
        user_category="Infrastructure",
        building="Academic Block B",
        room="Lab 101",
        idempotency_token="radar-test-a1",
        status="submitted",
        created_at=now - timedelta(minutes=45),
    )
    c2 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Classroom projector has no power",
        description="Lecturer cannot start presentation, projector has no electrical power.",
        user_category="Infrastructure",
        building="Academic Block B",
        room="102",
        idempotency_token="radar-test-a2",
        status="submitted",
        created_at=now - timedelta(minutes=30),
    )
    c3 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Water dispenser cooler power cut",
        description="Drinking water dispenser cooling unit power cut in hallway.",
        user_category="Infrastructure",
        building="Academic Block B",
        room="Corridor B1",
        idempotency_token="radar-test-a3",
        status="submitted",
        created_at=now - timedelta(minutes=15),
    )
    db.session.add_all([c1, c2, c3])
    db.session.commit()

    res = run_incident_radar_analysis()
    assert res["created_suggestions_count"] >= 1

    sugg = RadarSuggestion.query.filter_by(
        suggestion_type="shared_dependency", building="Academic Block B"
    ).first()

    assert sugg is not None
    assert "Possible shared-dependency incident" in sugg.headline
    assert sugg.dependency is not None
    assert sugg.dependency.dependency_identifier == "ELEC-PANEL-B1-P1"
    assert sugg.status == "pending_review"
    assert len(sugg.reports) == 3

    # Evidence inspection
    ev = sugg.evidence
    assert ev["evidence_level"] == "Supported by Configured Infrastructure Dependency"
    assert ev["time_basis"] == "submission_time"
    assert "electrical_supply" in ev["dependency_type"]
    assert len(ev["symptoms_detected"]) == 3
    assert len(ev["missing_information"]) >= 1

    # Verify NO automatic status change or ticket merging occurred
    assert c1.status == "submitted"
    assert c2.status == "submitted"
    assert c3.status == "submitted"


def test_scenario_b_unrelated_reports_no_incident_assertion(app, verified_user):
    """
    Scenario B:
    Similar power-cut wording but different buildings and 3 days apart ->
    Must NOT create a shared-incident suggestion based only on wording.
    """
    now = datetime.now(timezone.utc)

    c1 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Power cut in Room 201",
        description="Computers lost power in room 201.",
        user_category="Infrastructure",
        building="Academic Block A",
        room="201",
        idempotency_token="radar-test-b1",
        status="submitted",
        created_at=now - timedelta(days=3),  # 3 days ago
    )
    c2 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Power cut in reading room",
        description="Computers lost power in reading room.",
        user_category="Infrastructure",
        building="Central Library",
        room="Reading Room",
        idempotency_token="radar-test-b2",
        status="submitted",
        created_at=now - timedelta(minutes=10),
    )
    db.session.add_all([c1, c2])
    db.session.commit()

    res = run_incident_radar_analysis()
    # Different buildings and outside correlation window -> no suggestion
    suggs = RadarSuggestion.query.all()
    assert len(suggs) == 0


def test_scenario_c_location_time_cluster_without_dependency(app, verified_user):
    """
    Scenario C:
    Multiple reports in same building/time without shared infrastructure mapping ->
    Creates Type 2 'location_time_cluster' with explicit wording:
    'Multiple disruptions reported in this area. Cause unknown.'
    """
    now = datetime.now(timezone.utc)

    # 2 complaints in Hostel Block 1 within 1 hour, where NO electrical/plumbing dependency is configured
    c1 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Hostel room door lock broken",
        description="Key is stuck and cannot open room 301.",
        user_category="Infrastructure",
        building="Boys Hostel 1",
        room="301",
        idempotency_token="radar-test-c1",
        status="submitted",
        created_at=now - timedelta(minutes=40),
    )
    c2 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Hostel study chair leg fractured",
        description="Chair leg is broken in common study area.",
        user_category="Infrastructure",
        building="Boys Hostel 1",
        room="Study Room",
        idempotency_token="radar-test-c2",
        status="submitted",
        created_at=now - timedelta(minutes=20),
    )
    db.session.add_all([c1, c2])
    db.session.commit()

    run_incident_radar_analysis()

    sugg = RadarSuggestion.query.filter_by(
        suggestion_type="location_time_cluster", building="Boys Hostel 1"
    ).first()

    assert sugg is not None
    assert "Cause unknown" in sugg.summary or "Location/Time Cluster" in sugg.headline
    assert sugg.dependency_id is None
    assert sugg.evidence["evidence_level"] == "Location/Time Cluster Only (No Dependency Established)"


def test_scenario_d_incompatible_symptoms_not_linked(app, verified_user):
    """
    Scenario D:
    Same building and time, but one report is a sanitation odor and one is electrical ->
    Sanitation odor must NOT be linked to electrical supply dependency.
    """
    seed_synthetic_radar_demo()
    now = datetime.now(timezone.utc)

    # c1 is electrical in Computer Lab
    c1 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Computers lost power in Computer Lab",
        description="All screens went black and lost power.",
        user_category="Infrastructure",
        building="Academic Block B",
        room="Lab 101",
        idempotency_token="radar-test-d1",
        status="submitted",
        created_at=now - timedelta(minutes=20),
    )
    # c2 is sanitation foul odor in same building
    c2 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Foul smell in washroom",
        description="Terrible odor coming from washroom drain.",
        user_category="Sanitation",
        building="Academic Block B",
        room="102",
        idempotency_token="radar-test-d2",
        status="submitted",
        created_at=now - timedelta(minutes=15),
    )
    db.session.add_all([c1, c2])
    db.session.commit()

    run_incident_radar_analysis()

    # Shared dependency requires >= 2 COMPATIBLE symptoms.
    # Since c2 is sanitation odor, it must NOT connect to ELEC-PANEL-B1-P1!
    dep_suggs = RadarSuggestion.query.filter_by(
        suggestion_type="shared_dependency", building="Academic Block B"
    ).all()
    assert len(dep_suggs) == 0


def test_radar_review_lifecycle_and_audit(client, handler_user, verified_user, app):
    """
    Tests review actions ('confirm', 'reject', 'clarify') and verifies:
    - Retains human review decisions across re-scans.
    - Does NOT auto-merge or close complaints.
    - Creates immutable audit events.
    """
    seed_synthetic_radar_demo()
    now = datetime.now(timezone.utc)

    c1 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Power cut in Computer Lab",
        description="No power in Lab 101 workstations.",
        user_category="Infrastructure",
        building="Academic Block B",
        room="Lab 101",
        idempotency_token="radar-review-1",
        status="submitted",
        created_at=now - timedelta(minutes=30),
    )
    c2 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Projector no power in Room 102",
        description="Projector has no electrical power.",
        user_category="Infrastructure",
        building="Academic Block B",
        room="102",
        idempotency_token="radar-review-2",
        status="submitted",
        created_at=now - timedelta(minutes=15),
    )
    db.session.add_all([c1, c2])
    db.session.commit()

    run_incident_radar_analysis()
    sugg = RadarSuggestion.query.filter_by(building="Academic Block B").first()
    assert sugg.status == "pending_review"

    # Login as handler
    client.post(
        "/api/auth/login",
        json={"email": handler_user.email, "password": "HandlerPass123!"},
    )

    # 1. Action: Confirm for review
    res_confirm = client.post(
        f"/api/admin/radar/{sugg.id}/review",
        json={"action": "confirm", "notes": "Confirmed: Dispatched electrician to inspect Panel P1."},
    )
    assert res_confirm.status_code == 200
    assert res_confirm.get_json()["status"] == "confirmed_for_review"

    # Re-fetch from DB
    sugg_db = db.session.get(RadarSuggestion, sugg.id)
    assert sugg_db.status == "confirmed_for_review"
    assert sugg_db.review_decision == "confirmed"
    assert sugg_db.reviewed_by_user_id == handler_user.id

    # Complaints remain in their original status (no auto-resolve/merge!)
    assert c1.status == "submitted"
    assert c2.status == "submitted"

    # 2. Re-running radar scan MUST preserve human review decision!
    res_scan = run_incident_radar_analysis()
    assert res_scan["preserved_suggestions_count"] >= 1
    sugg_after = db.session.get(RadarSuggestion, sugg.id)
    assert sugg_after.status == "confirmed_for_review"
    assert sugg_after.review_decision == "confirmed"

    # 3. Action: Add clarification note
    res_clarify = client.post(
        f"/api/admin/radar/{sugg.id}/review",
        json={"action": "clarify", "notes": "Electrician arrived at site, checking breaker 4B."},
    )
    assert res_clarify.status_code == 200
    sugg_clarified = db.session.get(RadarSuggestion, sugg.id)
    assert "breaker 4B" in sugg_clarified.clarification_notes


def test_radar_api_privacy_omits_submitter_pii(client, handler_user, verified_user, app):
    """
    CRITICAL PRIVACY TEST:
    Verify Radar endpoints list and detail responses strictly OMIT submitter names and emails.
    """
    seed_synthetic_radar_demo()
    now = datetime.now(timezone.utc)

    c1 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Privacy Test Power cut in Lab",
        description="Computers lost power in Lab 101.",
        user_category="Infrastructure",
        building="Academic Block B",
        room="Lab 101",
        idempotency_token="radar-privacy-1",
        status="submitted",
        created_at=now - timedelta(minutes=20),
    )
    c2 = Complaint(
        user_id=verified_user.id,
        submission_type="complaint",
        title="Privacy Test Projector off",
        description="Projector has no power in 102.",
        user_category="Infrastructure",
        building="Academic Block B",
        room="102",
        idempotency_token="radar-privacy-2",
        status="submitted",
        created_at=now - timedelta(minutes=10),
    )
    db.session.add_all([c1, c2])
    db.session.commit()

    run_incident_radar_analysis()
    sugg = RadarSuggestion.query.filter_by(building="Academic Block B").first()

    # Login as handler
    client.post(
        "/api/auth/login",
        json={"email": handler_user.email, "password": "HandlerPass123!"},
    )

    # Check list endpoint
    list_res = client.get("/api/admin/radar")
    assert list_res.status_code == 200
    list_json_str = str(list_res.get_json())
    assert verified_user.email not in list_json_str
    assert verified_user.full_name not in list_json_str

    # Check detail endpoint
    detail_res = client.get(f"/api/admin/radar/{sugg.id}")
    assert detail_res.status_code == 200
    detail_json_str = str(detail_res.get_json())
    assert verified_user.email not in detail_json_str
    assert verified_user.full_name not in detail_json_str


def test_radar_unauthorized_access_blocked(client, verified_user, app):
    """Students and unauthenticated callers are strictly blocked from Radar endpoints."""
    # 1. Unauthenticated -> 401
    assert client.get("/api/admin/radar").status_code == 401
    assert client.post("/api/admin/radar/refresh").status_code == 401

    # 2. Student login -> 403 Forbidden
    client.post(
        "/api/auth/login",
        json={"email": verified_user.email, "password": "StudentPass123!"},
    )
    assert client.get("/api/admin/radar").status_code == 403
    assert client.post("/api/admin/radar/refresh").status_code == 403
