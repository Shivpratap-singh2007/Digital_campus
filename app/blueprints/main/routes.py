import os
from flask import render_template, current_app, send_from_directory
from app.blueprints.main import main_bp
from app.models.issue import Issue
from app.models.complaint import Complaint


@main_bp.route("/")
def index():
    frontend_dist = os.path.abspath(os.path.join(current_app.root_path, "..", "frontend", "dist"))
    if os.path.exists(frontend_dist):
        return send_from_directory(frontend_dist, "index.html")

    public_issues = (
        Issue.query.order_by(Issue.created_at.desc())
        .limit(10)
        .all()
    )
    total_submissions = Complaint.query.count()
    distinct_issues = Issue.query.count()
    resolved_issues = Issue.query.filter_by(status="resolved").count()

    return render_template(
        "main/index.html",
        public_issues=public_issues,
        total_submissions=total_submissions,
        distinct_issues=distinct_issues,
        resolved_issues=resolved_issues,
    )


@main_bp.route("/public-issues")
def public_issues():
    frontend_dist = os.path.abspath(os.path.join(current_app.root_path, "..", "frontend", "dist"))
    if os.path.exists(frontend_dist):
        return send_from_directory(frontend_dist, "index.html")

    issues = Issue.query.order_by(Issue.created_at.desc()).all()
    return render_template("main/public_issues.html", issues=issues)
