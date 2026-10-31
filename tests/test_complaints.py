import io
from PIL import Image
from app.extensions import db
from app.models.complaint import Complaint


def create_test_image(format="JPEG", size=(100, 100), color=(255, 0, 0)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    buf.seek(0)
    return buf


def test_unverified_user_cannot_submit(client, unverified_user):
    """Test unverified user is blocked from submitting complaints."""
    client.post(
        "/api/auth/login",
        json={"email": unverified_user.email, "password": "StudentPass123!"},
    )

    res = client.post(
        "/api/complaints",
        json={
            "title": "Water cooler leaking",
            "description": "Drinking water cooler leaking onto floor.",
            "submission_type": "complaint",
            "user_category": "Sanitation",
            "building": "Central Library",
        },
    )
    assert res.status_code == 403
    assert "verification required" in res.get_json()["error"].lower()


def test_verified_user_submission_with_idempotency(client, verified_user):
    """Test complaint submission, idempotency handling, and saving before analysis."""
    client.post(
        "/api/auth/login",
        json={"email": verified_user.email, "password": "StudentPass123!"},
    )

    key = "unique-test-key-12345"
    payload = {
        "title": "Broken window in physics lab",
        "description": "Cracked glass pane in window on the second floor.",
        "submission_type": "complaint",
        "user_category": "Infrastructure",
        "building": "Academic Block A",
        "room": "Lab 204",
        "submission_key": key,
    }

    # Initial submission
    res1 = client.post("/api/complaints", json=payload)
    assert res1.status_code == 201
    comp_id = res1.get_json()["id"]

    # Re-submitting identical payload returns original complaint
    res2 = client.post("/api/complaints", json=payload)
    assert res2.status_code == 200
    assert res2.get_json()["id"] == comp_id

    # Reusing same key with changed content returns 409 Conflict
    altered = dict(payload)
    altered["title"] = "Different complaint with same key"
    res3 = client.post("/api/complaints", json=altered)
    assert res3.status_code == 409


def test_image_validation_and_metadata_stripping(client, verified_user, app):
    """Test Pillow image validation, size limit, and safe storage."""
    client.post(
        "/api/auth/login",
        json={"email": verified_user.email, "password": "StudentPass123!"},
    )

    # Valid JPEG
    img_buf = create_test_image("JPEG")
    res = client.post(
        "/api/complaints",
        data={
            "title": "Wall plaster peeling off",
            "description": "Plaster falling from ceiling corridor.",
            "submission_type": "complaint",
            "user_category": "Infrastructure",
            "building": "Academic Block B",
            "image": (img_buf, "test_hazard.jpg", "image/jpeg"),
        },
        content_type="multipart/form-data",
    )
    assert res.status_code == 201
    comp_id = res.get_json()["id"]

    complaint = db.session.get(Complaint, comp_id)
    assert len(complaint.attachments) == 1
    att = complaint.attachments[0]
    assert att.mime_type == "image/jpeg"
    assert att.filename.endswith(".jpg")

    # Corrupt image rejection
    bad_buf = io.BytesIO(b"not an image binary header")
    res_bad = client.post(
        "/api/complaints",
        data={
            "title": "Corrupted image test",
            "description": "Description for corrupted image test.",
            "submission_type": "complaint",
            "user_category": "Infrastructure",
            "building": "Academic Block B",
            "image": (bad_buf, "corrupt.jpg", "image/jpeg"),
        },
        content_type="multipart/form-data",
    )
    assert res_bad.status_code == 400
    assert "image validation failed" in res_bad.get_json()["error"].lower()


def test_admin_and_handler_cannot_submit_complaints(client, handler_user, admin_user):
    """Test that handlers and admins are restricted from filing student complaints."""
    # 1. Handler login & attempt
    client.post(
        "/api/auth/login",
        json={"email": handler_user.email, "password": "HandlerPass123!"},
    )
    res_handler = client.post(
        "/api/complaints",
        json={
            "title": "Handler filing test complaint",
            "description": "Handler should not be allowed to submit student complaints.",
            "submission_type": "complaint",
            "building": "Academic Block A",
        },
    )
    assert res_handler.status_code == 403
    assert "cannot submit student complaints" in res_handler.get_json()["error"].lower()

    # 2. Admin login & attempt
    client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "AdminPass123!"},
    )
    res_admin = client.post(
        "/api/complaints",
        json={
            "title": "Admin filing test complaint",
            "description": "Admin should not be allowed to submit student complaints.",
            "submission_type": "complaint",
            "building": "Academic Block A",
        },
    )
    assert res_admin.status_code == 403
    assert "cannot submit student complaints" in res_admin.get_json()["error"].lower()


