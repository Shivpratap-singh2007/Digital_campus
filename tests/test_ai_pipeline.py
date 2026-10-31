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

