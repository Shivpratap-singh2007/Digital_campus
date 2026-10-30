import click
from datetime import datetime, timezone
import uuid
from flask import Blueprint
from app.extensions import db
from app.models import (
    User,
    Complaint,
    Issue,
    IssueComplaintLink,
    StatusEvent,
    ResolutionRound,
    ResolutionFeedback,
    AnalysisResult,
)
from app.services.complaint_analysis import run_complaint_analysis
from app.services.security import validate_password_strength

cli_bp = Blueprint("campus_cli", __name__)


@cli_bp.cli.command("rotate-password")
@click.option("--email", prompt=True, help="Account email address to rotate password for.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    default=lambda: __import__("os").environ.get("NEW_PASSWORD", ""),
    help="New password (accepts hidden prompt or NEW_PASSWORD environment variable).",
)
def rotate_password(email, password):
    """Safely updates a user password via hidden prompt or environment variable without exposing credentials."""
    email_clean = email.strip().lower()
    user = User.query.filter_by(email=email_clean).first()
    if not user:
        click.echo(f"Error: Account '{email_clean}' not found.")
        return

    if not password:
        click.echo("Error: Password cannot be empty.")
        return

    valid, msg = validate_password_strength(password)
    if not valid:
        click.echo(f"Error: Password does not meet security requirements: {msg}")
        return

    user.set_password(password)
    db.session.commit()
    click.echo(f"Password for account '{email_clean}' successfully rotated.")


@cli_bp.cli.command("seed-fixtures")
@click.option("--admin-password", envvar="FIXTURE_ADMIN_PASSWORD", default="", help="Password for synthetic admin account (or env FIXTURE_ADMIN_PASSWORD).")
@click.option("--handler-password", envvar="FIXTURE_HANDLER_PASSWORD", default="", help="Password for synthetic handler account (or env FIXTURE_HANDLER_PASSWORD).")
@click.option("--student-password", envvar="FIXTURE_STUDENT_PASSWORD", default="", help="Password for synthetic student accounts (or env FIXTURE_STUDENT_PASSWORD).")
def seed_fixtures_command(admin_password, handler_password, student_password):
    """Provisions synthetic demo fixtures (Students A/B, Handler, Admin, Unverified)."""
    from app.services.fixtures import provision_synthetic_fixtures
    click.echo("Provisioning synthetic demo fixtures...")
    res = provision_synthetic_fixtures(
        admin_password=admin_password,
        handler_password=handler_password,
        student_password=student_password,
    )
    click.echo(f"Created: {len(res['created'])} account(s)")
    for c in res['created']:
        click.echo(f"  + [{c['role']}] {c['email']}")
    click.echo(f"Preserved existing: {len(res['preserved'])} account(s)")
    for p in res['preserved']:
        click.echo(f"  = [{p['role']}] {p['email']}")
    if res.get('skipped'):
        click.echo(f"Skipped accounts (missing password secret): {len(res['skipped'])}")
        for s in res['skipped']:
            click.echo(f"  ? {s['reason']}")
    if res['conflicts']:
        click.echo(f"Safeguard conflicts detected: {len(res['conflicts'])}")
        for conf in res['conflicts']:
            click.echo(f"  ! {conf['reason']}")
    click.echo("Fixture provisioning complete.")


@cli_bp.cli.command("warmup-model")
def warmup_model():
    """Warms up and verifies the sentence-transformer embedding model."""
    import os
    os.environ.pop("HF_HUB_OFFLINE", None)
    os.environ.pop("TRANSFORMERS_OFFLINE", None)
    click.echo("Warming up semantic embedding model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2...")
    from app.services.semantic import semantic_engine
    # Force reload attempt
    semantic_engine._load_attempted = False
    if semantic_engine.is_available:
        click.echo("Embedding model loaded and ready! Semantic clustering is active.")
    else:
        click.echo(f"Semantic model could not be loaded: {semantic_engine.load_error}")


@cli_bp.cli.command("create-admin")
@click.option("--email", prompt=True, default=lambda: __import__("os").environ.get("ADMIN_EMAIL", "admin@campus.edu"), help="Admin email address.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    default=lambda: __import__("os").environ.get("ADMIN_PASSWORD", ""),
    help="Admin account password (accepts hidden prompt or ADMIN_PASSWORD environment variable).",
)
@click.option("--name", default=lambda: __import__("os").environ.get("ADMIN_NAME", "Campus Security Admin"), help="Admin full name.")
@click.option("--reset-password", is_flag=True, default=False, help="Explicit confirmation flag to reset password if admin already exists.")
def create_admin(email, password, name, reset_password):
    """Creates a trusted administrator account via CLI."""
    email_clean = email.strip().lower()
    if not password:
        click.echo("Error: Password cannot be empty.")
        return

    valid, msg = validate_password_strength(password)
    if not valid:
        click.echo(f"Error: Password does not meet security requirements: {msg}")
        return

    user = User.query.filter_by(email=email_clean).first()
    if user:
        if user.role != "admin":
            click.echo(f"Error: Account '{email_clean}' exists with role '{user.role}'. Silently promoting an existing user is prohibited.")
            return

        if not reset_password:
            if not click.confirm(f"Administrator '{email_clean}' already exists. Do you want to reset their password?", default=False):
                click.echo("Aborted without modifying existing administrator account.")
                return

        user.set_password(password)
        user.is_verified = True
        if name:
            user.full_name = name
        db.session.commit()
        click.echo(f"Password for existing administrator '{email_clean}' updated successfully.")
    else:
        admin_user = User(
            email=email_clean,
            full_name=name or "Campus Security Admin",
            role="admin",
            is_verified=True,
            is_synthetic_fixture=True,
        )
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()
        click.echo(f"Administrator account '{email_clean}' created successfully.")


@cli_bp.cli.command("create-handler")
@click.option("--email", prompt=True, default=lambda: __import__("os").environ.get("HANDLER_EMAIL", "handler@campus.edu"), help="Handler email address.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    default=lambda: __import__("os").environ.get("HANDLER_PASSWORD", ""),
    help="Handler account password (accepts hidden prompt or HANDLER_PASSWORD environment variable).",
)
@click.option("--name", default=lambda: __import__("os").environ.get("HANDLER_NAME", "Facilities Operations Desk"), help="Handler full name.")
@click.option("--reset-password", is_flag=True, default=False, help="Explicit confirmation flag to reset password if handler already exists.")
def create_handler(email, password, name, reset_password):
    """Creates an operations handler account via CLI."""
    email_clean = email.strip().lower()
    if not password:
        click.echo("Error: Password cannot be empty.")
        return

    valid, msg = validate_password_strength(password)
    if not valid:
        click.echo(f"Error: Password does not meet security requirements: {msg}")
        return

    user = User.query.filter_by(email=email_clean).first()
    if user:
        if user.role != "handler":
            click.echo(f"Error: Account '{email_clean}' exists with role '{user.role}'. Silently promoting an existing user is prohibited.")
            return

        if not reset_password:
            if not click.confirm(f"Handler '{email_clean}' already exists. Do you want to reset their password?", default=False):
                click.echo("Aborted without modifying existing handler account.")
                return

        user.set_password(password)
        user.is_verified = True
        if name:
            user.full_name = name
        db.session.commit()
        click.echo(f"Password for existing handler '{email_clean}' updated successfully.")
    else:
        handler_user = User(
            email=email_clean,
            full_name=name or "Facilities Operations Desk",
            role="handler",
            is_verified=True,
            is_synthetic_fixture=True,
        )
        handler_user.set_password(password)
        db.session.add(handler_user)
        db.session.commit()
        click.echo(f"Handler account '{email_clean}' created successfully.")


@cli_bp.cli.command("seed-demo")
@click.option("--admin-password", envvar="FIXTURE_ADMIN_PASSWORD", default="", help="Password for synthetic admin account (or env FIXTURE_ADMIN_PASSWORD).")
@click.option("--handler-password", envvar="FIXTURE_HANDLER_PASSWORD", default="", help="Password for synthetic handler account (or env FIXTURE_HANDLER_PASSWORD).")
@click.option("--student-password", envvar="FIXTURE_STUDENT_PASSWORD", default="", help="Password for synthetic student accounts (or env FIXTURE_STUDENT_PASSWORD).")
def seed_demo(admin_password, handler_password, student_password):
    """Populates database with synthetic demo users, complaints, and resolution feedback."""
    from app.services.fixtures import provision_synthetic_fixtures
    click.echo("Seeding synthetic demo data...")
    res = provision_synthetic_fixtures(
        admin_password=admin_password,
        handler_password=handler_password,
        student_password=student_password,
    )
    click.echo(f"Created: {len(res['created'])} account(s)")
    for c in res['created']:
        click.echo(f"  + [{c['role']}] {c['email']}")
    click.echo(f"Preserved existing: {len(res['preserved'])} account(s)")
    for p in res['preserved']:
        click.echo(f"  = [{p['role']}] {p['email']}")
    if res.get('skipped'):
        click.echo(f"Skipped accounts (missing password secret): {len(res['skipped'])}")
        for s in res['skipped']:
            click.echo(f"  ? {s['reason']}")
    if res['conflicts']:
        click.echo(f"Safeguard conflicts detected: {len(res['conflicts'])}")
        for conf in res['conflicts']:
            click.echo(f"  ! {conf['reason']}")
    click.echo("Synthetic demo data provisioning complete.")
