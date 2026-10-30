import os
from flask import Flask, render_template, abort, send_from_directory, request, jsonify, redirect, url_for
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

    @login_manager.unauthorized_handler
    def unauthorized_callback():
        if request.path.startswith("/api/"):
            return jsonify({"error": "Authentication required."}), 401
        return redirect(url_for("auth.login"))

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

    # Static assets and SPA routes for built React frontend
    frontend_dist = os.path.abspath(os.path.join(app.root_path, "..", "frontend", "dist"))
    if os.path.exists(frontend_dist):
        @app.route("/assets/<path:path>")
        def serve_react_assets(path):
            assets_dir = os.path.join(frontend_dist, "assets")
            return send_from_directory(assets_dir, path)

        @app.route("/login")
        @app.route("/register")
        @app.route("/verify-email")
        @app.route("/my-complaints")
        @app.route("/new-complaint")
        @app.route("/complaints/<int:complaint_id>")
        @app.route("/admin/queue")
        @app.route("/admin/create-issue")
        @app.route("/admin/issues/<int:issue_id>")
        @app.route("/admin/dashboard")
        @app.route("/admin/audit-log")
        def serve_react_pages(**kwargs):
            return send_from_directory(frontend_dist, "index.html")

    # Security response headers (OWASP standard recommendations)
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Context processors
    @app.context_processor
    def inject_global_vars():
        return {
            "app_title": "CampusVoice",
            "safety_notice": "Notice: This portal is not an emergency-response service. For active physical or medical emergencies, contact campus emergency services directly.",
            "privacy_notice": "Identity-restricted reporting: Submitter identities are concealed from ordinary handling screens and can only be disclosed with audited justification.",
        }

    # Error handlers (Dual-mode: JSON for API, HTML for web)
    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": getattr(e, "description", "Bad Request")}), 400
        return render_template("errors/404.html"), 400

    @app.errorhandler(401)
    def unauthorized(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Authentication required."}), 401
        return render_template("errors/403.html"), 401

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": getattr(e, "description", "Access Denied: Insufficient permissions.")}), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Resource not found."}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
        return "Rate limit exceeded.", 429

    @app.errorhandler(500)
    def internal_server_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "An internal server error occurred."}), 500
        return render_template("errors/500.html"), 500

    return app
