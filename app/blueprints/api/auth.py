from flask import jsonify, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from flask_wtf.csrf import generate_csrf
from app.extensions import db
from app.blueprints.api import api_bp
from app.models.user import User
from app.services.email import (
    create_verification_token,
    send_verification_email,
    verify_token,
    can_resend_verification,
)


@api_bp.route("/auth/csrf-token", methods=["GET"])
def get_csrf_token():
    """Returns a valid CSRF token for JSON and form requests."""
    token = generate_csrf()
    return jsonify({"csrf_token": token})


@api_bp.route("/auth/me", methods=["GET"])
def get_current_user():
    """Returns authentication state and profile for current user session."""
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False, "user": None})

    return jsonify({
        "authenticated": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "is_verified": current_user.is_verified,
            "is_handler": current_user.is_handler,
            "is_admin": current_user.is_admin,
        },
    })


@api_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not full_name or len(full_name) < 2:
        return jsonify({"error": "Full name must be at least 2 characters."}), 400

    if not email or "@" not in email:
        return jsonify({"error": "A valid college email address is required."}), 400

    parts = email.split("@")
    if len(parts) != 2:
        return jsonify({"error": "Invalid email format."}), 400

    domain = parts[1]
    allowed_domains = current_app.config.get("COLLEGE_EMAIL_DOMAINS", [])
    if domain not in [d.lower() for d in allowed_domains]:
        allowed_list = ", ".join(f"@{d}" for d in allowed_domains)
        return jsonify({
            "error": f"Registration is restricted to authorized college domains only ({allowed_list})."
        }), 400

    if not password or len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters long."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email address is already registered."}), 400

    # Create unverified user (ordinary users NEVER get handler/admin during registration)
    user = User(
        email=email,
        full_name=full_name,
        role="user",
        is_verified=False,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # Generate token & dispatch via SMTP
    # CRITICAL: Never return the raw verification token in the response
    raw_token, _ = create_verification_token(user)
    sent, smtp_msg = send_verification_email(user, raw_token)

    return jsonify({
        "success": True,
        "message": (
            "Registration successful. A single-use verification link has been sent to your college inbox."
            if sent
            else f"Account created, but SMTP dispatch encountered an issue: {smtp_msg}. You can resend verification."
        ),
        "email": user.email,
        "smtp_dispatched": sent,
    }), 201


@api_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email address or password."}), 401

    login_user(user, remember=True)

    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_verified": user.is_verified,
            "is_handler": user.is_handler,
            "is_admin": user.is_admin,
        },
    })


@api_bp.route("/auth/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"success": True, "message": "Successfully logged out."})


@api_bp.route("/auth/verify/<token>", methods=["GET", "POST"])
def verify(token):
    success, message, user = verify_token(token)
    if not success:
        return jsonify({"success": False, "error": message}), 400

    return jsonify({
        "success": True,
        "message": message,
        "user_email": user.email if user else None,
    })


@api_bp.route("/auth/resend-verification", methods=["POST"])
def resend_verification():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        # Avoid user enumeration
        return jsonify({
            "success": True,
            "message": "If an unverified account exists for this email, a verification link has been sent.",
        })

    if user.is_verified:
        return jsonify({"success": True, "message": "Account is already verified. You may log in directly."})

    can_resend, cooldown_msg = can_resend_verification(user)
    if not can_resend:
        return jsonify({"error": cooldown_msg}), 429

    raw_token, _ = create_verification_token(user)
    sent, err = send_verification_email(user, raw_token)

    return jsonify({
        "success": sent,
        "message": "Verification email dispatched." if sent else f"Dispatch failed: {err}",
    })

