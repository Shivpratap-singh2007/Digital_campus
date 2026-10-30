import os
from flask import Flask, render_template, abort, send_from_directory
from app.config import Config
from app.extensions import db, login_manager, csrf
from app.models.user import User


def create_app(config_class=Config):
    """Application factory for CampusVoice."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    from app.blueprints.main import main_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.complaints import complaints_bp
    from app.blueprints.issues import issues_bp
    from app.blueprints.feedback import feedback_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.api import api_bp
    from app.cli import cli_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(issues_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(cli_bp)

    # Single-origin production/demo serving for built React SPA
    frontend_dist = os.path.join(app.root_path, "..", "frontend", "dist")
    if os.path.exists(frontend_dist):
        from flask import send_from_directory

        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_react_spa(path):
            if path.startswith("api/") or path.startswith("auth/") or path.startswith("complaints/") or path.startswith("issues/") or path.startswith("admin/"):
                return abort(404)
            file_path = os.path.join(frontend_dist, path)
            if path and os.path.exists(file_path):
                return send_from_directory(frontend_dist, path)
            return send_from_directory(frontend_dist, "index.html")

    # Context processors
    @app.context_processor
    def inject_global_vars():
        return {
            "app_title": "CampusVoice",
            "safety_notice": "Notice: This portal is not an emergency-response service. For active physical or medical emergencies, contact campus emergency services directly.",
            "privacy_notice": "Identity-restricted reporting: Submitter identities are concealed from ordinary handling screens and can only be disclosed with audited justification.",
        }

    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html"), 500

    return app
