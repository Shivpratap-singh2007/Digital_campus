import re
import html
from functools import wraps
from flask import jsonify, abort, request, current_app
from flask_login import current_user

COMMON_WEAK_PASSWORDS = {
    "password", "password123", "admin123", "12345678", "123456789",
    "qwerty123", "campus123", "student123", "welcome123", "letmein123"
}


def sanitize_text(value: str | None) -> str:
    """
    Sanitizes user input to prevent Cross-Site Scripting (XSS).
    Strips dangerous control characters and escapes HTML entities.
    """
    if value is None:
        return ""
    # Strip null bytes and control characters
    cleaned = "".join(ch for ch in str(value) if ch >= " " or ch in "\n\r\t")
    # HTML escape dangerous characters (<, >, &, ", ')
    return html.escape(cleaned.strip())


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validates password complexity:
    - Min length 8
    - Contains at least 1 uppercase letter
    - Contains at least 1 lowercase letter
    - Contains at least 1 digit or symbol
    - Not in known weak passwords
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if len(password) > 128:
        return False, "Password must not exceed 128 characters."

    if password.lower() in COMMON_WEAK_PASSWORDS:
        return False, "This password is too common and easily guessed. Please choose a stronger password."

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit_or_symbol = any(c.isdigit() or not c.isalnum() for c in password)

    if not (has_upper and has_lower and has_digit_or_symbol):
        return False, "Password must contain uppercase letters, lowercase letters, and at least one number or symbol."

    return True, ""


def admin_required(fn):
    """Decorator ensuring current user is an authenticated administrator."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required."}), 401
            abort(401)
        if not current_user.is_admin:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Access Denied: Administrator role required."}), 403
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def handler_required(fn):
    """Decorator ensuring current user is an authenticated handler or administrator."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required."}), 401
            abort(401)
        if not current_user.is_handler:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Access Denied: Operational handler permissions required."}), 403
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def verified_user_required(fn):
    """Decorator ensuring user has verified college email before performing sensitive actions."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required."}), 401
            abort(401)
        if not current_user.is_verified and current_user.role == "user":
            if request.path.startswith("/api/"):
                return jsonify({"error": "Email verification required. Please verify your college email address."}), 403
            abort(403)
        return fn(*args, **kwargs)
    return wrapper
