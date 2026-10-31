from app.extensions import db
from app.models import Issue, Complaint, IssueComplaintLink, User
from app.services.ai_pipeline import classify_issue, detect_priority, find_duplicate_issues


def test_classify_issue_multilingual_and_domains():
    """Verify classification across the 4 domains with English and Hinglish phrases."""
    # 1. Sanitation & Plumbing
    assert classify_issue("Hostel washroom me nal se paani beh raha hai aur bathroom ganda hai") == "Sanitation & Plumbing"
    assert classify_issue("Drinking water cooler leaking onto the floor and drain is clogged") == "Sanitation & Plumbing"

    # 2. Electrical & Hardware
    assert classify_issue("Physics lab me bijli chali gayi aur switchboard me spark ho raha hai") == "Electrical & Hardware"
    assert classify_issue("Ceiling fan not working and wire hanging from ceiling in Room 204") == "Electrical & Hardware"

    # 3. Academics & Classroom
    assert classify_issue("Lecture hall 3 me projector nahi chal raha aur mic ki aawaz nahi aa rahi") == "Academics & Classroom"
    assert classify_issue("Timetable schedule clash in classroom and blackboard marker missing") == "Academics & Classroom"

    # 4. General Infrastructure
    assert classify_issue("Classroom door lock broken and window glass pane is cracked") == "General Infrastructure"
    assert classify_issue("Hostel room ka darwaza toota hua hai aur deewar me crack hai") == "General Infrastructure"
    assert classify_issue("") == "General Infrastructure"


def test_detect_priority_levels():
    """Verify priority detection: Critical (P1), Medium (P2), Low (P3)."""
    # P1: Safety hazards
    assert detect_priority("Urgent! Fire and heavy smoke coming out of electrical room") == "Critical (P1)"
    assert detect_priority("Exposed live wire with sparks and danger of electric shock") == "Critical (P1)"
    assert detect_priority("Broken glass pane shattered on staircase, dangerous for students") == "Critical (P1)"
    assert detect_priority("Switchboard me aag lag gayi aur current mar raha hai") == "Critical (P1)"

    # P2: Operational disruptions
    assert detect_priority("Tap is leaking continuously and basin is clogged") == "Medium (P2)"
    assert detect_priority("Elevator stuck between floors, urgent maintenance required") == "Medium (P2)"
    assert detect_priority("Washroom flush kharab hai aur paani beh raha hai") == "Medium (P2)"

    # P3: Baseline routine requests
    assert detect_priority("Please add more study chairs and desks in reading room") == "Low (P3)"
    assert detect_priority("Suggestion for annual sports day schedule") == "Low (P3)"
    assert detect_priority("") == "Low (P3)"


def test_find_duplicate_issues_tfidf_cosine():
    """Verify TF-IDF cosine similarity detects duplicate issues > 0.70."""
    existing_issues = [
        {
            "id": 10,
            "title": "Water cooler leaking in Central Library",
            "description": "Drinking water cooler leaking onto floor near 2nd floor staircase.",
        },
        {
            "id": 11,
            "title": "Projector not working in Lecture Hall B",
            "description": "Projector HDMI display disconnected and power cable loose.",
        },
    ]

    # Duplicate report for Issue #10
    match = find_duplicate_issues(
        new_title="Water cooler leak in Library 2nd floor",
        new_desc="Water cooler is leaking water onto the floor near stairs",
        existing_issues=existing_issues,
        threshold=0.70,
    )
    assert match["is_duplicate"] is True
    assert match["matched_issue_id"] == 10
    assert match["similarity_score"] >= 0.70
    assert len(match["duplicates"]) >= 1

    # Completely different report -> no duplicate
    no_match = find_duplicate_issues(
        new_title="Cafeteria food quality inquiry",
        new_desc="Requesting review of lunch menu in main cafeteria",
        existing_issues=existing_issues,
        threshold=0.70,
    )
    assert no_match["is_duplicate"] is False
    assert no_match["matched_issue_id"] is None


def test_complaint_submission_executes_ai_pipeline(client, verified_user, handler_user, app):
    """Test complaint submission automatically applies AI classification, priority, and duplicate grouping."""
    # 1. Login as handler to seed an active issue
    client.post(
        "/api/auth/login",
        json={"email": handler_user.email, "password": "HandlerPass123!"},
    )
    active_issue = Issue(
        title="Restroom Water Leakage in Science Block",
        description="Water tap leaking continuously and basin drain clogged on 1st floor.",
        category="Sanitation & Plumbing",
        building="Academic Block A",
        status="in_progress",
        created_by_user_id=handler_user.id,
    )
    db.session.add(active_issue)
    db.session.commit()

    # 2. Login as verified student and submit duplicate complaint
    client.post(
        "/api/auth/login",
        json={"email": verified_user.email, "password": "StudentPass123!"},
    )

    payload = {
        "title": "Restroom tap leaking in Science Block",
        "description": "Water tap leaking continuously and washroom basin drain clogged",
        "submission_type": "complaint",
        "user_category": "Not sure",
        "building": "Academic Block A",
        "submission_key": "ai-pipe-test-key-101",
    }

    res = client.post("/api/complaints", json=payload)
    assert res.status_code == 201
    data = res.get_json()

    comp_id = data["id"]
    complaint = db.session.get(Complaint, comp_id)

    # Verify AI pipeline executed before saving
    assert complaint.suggested_category == "Sanitation & Plumbing"
    assert "P2" in complaint.suggested_priority  # 'Medium (P2)'
    assert data["ai_pipeline"]["category"] == "Sanitation & Plumbing"

    # Verify duplicate auto-grouping with active issue #active_issue.id
    assert complaint.issue_link is not None
    assert complaint.issue_link.issue_id == active_issue.id
    assert complaint.status == active_issue.status

    # Verify extended AI pipeline components returned in response
    ai_pipe = data["ai_pipeline"]
    assert "formal_memo" in ai_pipe
    assert "technician_action_sheet" in ai_pipe
    assert "hazard_analysis" in ai_pipe
    assert "repeat_risk" in ai_pipe
    assert ai_pipe["formal_memo"]["subject"].startswith("FACILITY INCIDENT MEMORANDUM")
    assert ai_pipe["technician_action_sheet"]["assigned_unit"] == "Campus Rapid Hydraulics & Plumbing Services"
    assert ai_pipe["technician_action_sheet"]["sla_resolution_hours"] == 12

    # Verify get_complaint endpoint returns analysis metadata with action sheet and memo
    get_res = client.get(f"/api/complaints/{comp_id}")
    assert get_res.status_code == 200
    detail = get_res.get_json()
    assert detail["analysis"] is not None
    assert detail["analysis"]["technician_action_sheet"] is not None
    assert detail["analysis"]["formal_memo"] is not None


def test_generate_formal_memo_and_hinglish_normalization():
    """Verify intelligent text normalization and formal administrative memorandum generation."""
    from app.services.ai_pipeline import generate_formal_memo, normalize_text_to_formal_english

    # Hinglish text normalization
    raw_hinglish = "Physics lab me switchboard me spark ho raha hai aur bijli band hai jaldi karo"
    normalized = normalize_text_to_formal_english(raw_hinglish)
    assert "sparking" in normalized.lower() or "arcing" in normalized.lower()
    assert "outage" in normalized.lower() or "disruption" in normalized.lower()

    # Administrative memorandum generation
    memo = generate_formal_memo(
        title="Hostel washroom me nal se paani beh raha hai",
        description="Washroom me nal kharab hai paani beh raha hai aur bathroom ganda hai",
        building="Tagore Hostel Block B",
        room="204",
    )
    assert memo["memo_id"].startswith("MEMO-")
    assert "Tagore Hostel Block B, Room 204" in memo["location_context"]
    assert "Sanitation" in memo["subject"] or "PLUMBING" in memo["subject"]
    assert len(memo["actionable_scope"]) >= 3
    assert "MEMORANDUM" in memo["full_memo_text"]


def test_generate_technician_action_sheet():
    """Verify technician action sheets across categories and priority SLAs."""
    from app.services.ai_pipeline import generate_technician_action_sheet

    # 1. Critical Electrical
    elec_sheet = generate_technician_action_sheet(
        category="Electrical & Hardware",
        priority="Critical (P1)",
        title="Live wire spark",
        description="Sparks and smoke from distribution box",
    )
    assert elec_sheet["work_order_code"].startswith("WO-")
    assert elec_sheet["assigned_unit"] == "Electrical Grid & Power Systems Maintenance Wing"
    assert elec_sheet["sla_resolution_hours"] == 2
    assert any("LOTO" in s or "Lockout" in s for s in elec_sheet["safety_protocol"])
    assert any("Multimeter" in t for t in elec_sheet["required_tools_and_parts"])

    # 2. Medium Sanitation
    plumb_sheet = generate_technician_action_sheet(
        category="Sanitation & Plumbing",
        priority="Medium (P2)",
        title="Water leak",
        description="Tap leaking",
    )
    assert plumb_sheet["assigned_unit"] == "Campus Rapid Hydraulics & Plumbing Services"
    assert plumb_sheet["sla_resolution_hours"] == 12
    assert any("wrench" in t.lower() or "teflon" in t.lower() for t in plumb_sheet["required_tools_and_parts"])

    # 3. Low Routine Infrastructure
    infra_sheet = generate_technician_action_sheet(
        category="General Infrastructure",
        priority="Low (P3)",
        title="Loose desk hinge",
        description="Table in reading room",
    )
    assert infra_sheet["sla_resolution_hours"] == 48


def test_multi_hazard_visual_ai_analysis():
    """Verify multi-hazard visual context analysis logic."""
    from app.services.ai_pipeline import analyze_image_evidence

    # Without image
    no_img = analyze_image_evidence(image_file=None, title="Test", description="Test")
    assert no_img["has_image"] is False
    assert no_img["hazard_score"] == 0.0

    # With dummy image mock
    class DummyImage:
        filename = "hazard_evidence.jpg"

    hazard_img = analyze_image_evidence(
        image_file=DummyImage(),
        title="Live wire sparked with flames",
        description="Exposed wire on wall with danger of electric shock",
        category="Electrical & Hardware",
    )
    assert hazard_img["has_image"] is True
    assert "Critical" in hazard_img["hazard_rating"]
    assert hazard_img["visual_confidence_score"] >= 0.90
    assert len(hazard_img["detected_features"]) >= 1


def test_predictive_recurrence_and_repeat_failure_risk():
    """Verify chronic failure pattern detection and recurrence risk scoring."""
    from app.services.ai_pipeline import evaluate_repeat_failure_risk

    # 1. No past records -> isolated incident
    isolated = evaluate_repeat_failure_risk(
        building="Ramanujan Hall",
        room="101",
        category="Sanitation & Plumbing",
        historical_complaints=[],
    )
    assert isolated["is_chronic_failure"] is False
    assert isolated["risk_level"] == "Isolated Incident (Baseline)"

    # 2. Chronic recurrence: multiple historical complaints in same building & category
    history = [
        {"building": "Ramanujan Hall", "room": "101", "category": "Sanitation & Plumbing"},
        {"building": "Ramanujan Hall", "room": "102", "category": "Sanitation & Plumbing"},
        {"building": "Ramanujan Hall", "room": "101", "category": "Sanitation & Plumbing"},
    ]
    chronic = evaluate_repeat_failure_risk(
        building="Ramanujan Hall",
        room="101",
        category="Sanitation & Plumbing",
        historical_complaints=history,
    )
    assert chronic["is_chronic_failure"] is True
    assert chronic["repeat_incident_count"] == 3
    assert chronic["recurrence_score"] >= 0.70
    assert "overhaul" in chronic["preventive_advisory"].lower()

