import os
from flask import Flask, render_template, abort, send_from_directory, request, jsonify, redirect, url_for
from flask_wtf.csrf import CSRFError
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
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized_callback():
        if request.path.startswith("/api/"):
            return jsonify({"error": "Authentication required."}), 401
        return redirect("/login")

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

    # Safe schema auto-initialization for production & ephemeral deployments
    with app.app_context():
        try:
            db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
            if db_uri.startswith("sqlite:///"):
                sqlite_file = db_uri.replace("sqlite:///", "")
                if sqlite_file and not sqlite_file.startswith(":memory:"):
                    db_dir = os.path.dirname(os.path.abspath(sqlite_file))
                    if db_dir:
                        os.makedirs(db_dir, exist_ok=True)
            db.create_all()
        except Exception as e:
            app.logger.warning(f"Database schema initialization notice: {e}")

    # Safe auto-initialization for fresh ephemeral deployments when explicitly enabled
    bootstrap_enabled = os.environ.get("BOOTSTRAP_DEMO_DATA", "").lower() in ("true", "1", "yes") or \
                        os.environ.get("DEMO_MODE", "").lower() in ("true", "1", "yes")
    if bootstrap_enabled:
        with app.app_context():
            from app.services.fixtures import provision_synthetic_fixtures
            provision_synthetic_fixtures(app)

    # Health check endpoints for Railway / container orchestrators
    @app.route("/api/health", methods=["GET"])
    def api_health():
        return jsonify({"status": "healthy", "service": "campusvoice"}), 200

    @app.route("/healthz", methods=["GET"])
    def healthz():
        return jsonify({"status": "healthy", "service": "campusvoice"}), 200

    # Static assets and SPA routes for built React frontend
    frontend_dist = os.path.abspath(os.path.join(app.root_path, "..", "frontend", "dist"))
    if os.path.exists(frontend_dist):
        @app.before_request
        def intercept_react_spa():
            # Only intercept GET and HEAD requests
            if request.method not in ("GET", "HEAD"):
                return None

            # Never intercept API endpoints (preserve JSON API routes and unknown /api 404s)
            if request.path.startswith("/api/") or request.path == "/api":
                return None

            # Never intercept static bundle assets
            if request.path.startswith("/assets/"):
                return None

            # Never intercept health checks
            if request.path in ("/healthz", "/api/health"):
                return None

            # Never intercept authorized file attachments
            if request.path.startswith("/complaints/attachment/"):
                return None

            # Never intercept email verification link validation route
            if request.path.startswith("/auth/verify/"):
                return None

            # Serve static files if they exist directly in dist root (favicon, robots.txt, etc.)
            clean_path = request.path.lstrip("/")
            if clean_path:
                target_file = os.path.join(frontend_dist, clean_path)
                if os.path.isfile(target_file):
                    return send_from_directory(frontend_dist, clean_path)

            # Route all other frontend URLs (including /admin/dashboard, /admin/queue, etc.)
            # to index.html so React Router renders the intended modern view
            return send_from_directory(frontend_dist, "index.html")

        @app.route("/assets/<path:path>")
        def serve_react_assets(path):
            assets_dir = os.path.join(frontend_dist, "assets")
            return send_from_directory(assets_dir, path)

        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_react_spa(path):
            # Unknown /api routes MUST return 404 JSON, never index.html
            if path.startswith("api/") or path == "api":
                abort(404)
            # Missing assets must return 404, never index.html
            if path.startswith("assets/"):
                abort(404)
            # Directly serve root static files if they exist (e.g. favicon, robots.txt)
            target = os.path.join(frontend_dist, path)
            if path and os.path.isfile(target):
                return send_from_directory(frontend_dist, path)
            # Default to index.html for React Router client routes and refreshes
            return send_from_directory(frontend_dist, "index.html")

    # Support reverse proxy headers (e.g. Railway, Nginx, Envoy)
    try:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    except Exception:
        pass

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
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        reason = getattr(e, "description", "CSRF token validation failed.")
        if request.path.startswith("/api/"):
            return jsonify({
                "error": reason,
                "code": "CSRF_ERROR",
                "message": reason,
            }), 400
        return render_template("errors/404.html"), 400

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
