from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

from app.blueprints.api import auth, complaints, issues, feedback, admin  # noqa: E402, F401

