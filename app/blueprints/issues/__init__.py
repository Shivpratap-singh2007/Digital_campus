from flask import Blueprint

issues_bp = Blueprint("issues", __name__, url_prefix="/issues")

from app.blueprints.issues import routes  # noqa: E402, F401
