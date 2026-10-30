from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.blueprints.auth import auth_bp
from app.models.user import User
from app.forms import RegistrationForm, LoginForm, ResendVerificationForm
from app.services.email import (
    create_verification_token,
    send_verification_email,
    verify_token,
    can_resend_verification,
)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("complaints.my_complaints"))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if email is already registered
        existing_user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if existing_user:
            flash("An account with this email address already exists. Please log in or resend verification.", "warning")
            return redirect(url_for("auth.login"))

        # Create user with role='user' (never admin) and is_verified=False
        new_user = User(
            email=form.email.data.strip().lower(),
            full_name=form.full_name.data.strip(),
            role="user",
            is_verified=False,
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()

        # Generate token and dispatch verification email
        raw_token, _ = create_verification_token(new_user)
        sent, msg = send_verification_email(new_user, raw_token)

        if sent:
            flash(
                "Registration successful! A verification link has been sent to your college email. "
                "Please verify your email before submitting complaints.",
                "success",
            )
        else:
            flash(
                f"Registration successful, but email dispatch failed ({msg}). "
                "You can request a new verification link below or check your Mailpit test server.",
                "warning",
            )

        return redirect(url_for("auth.verification_guidance", email=new_user.email))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("complaints.my_complaints"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f"Welcome back, {user.full_name}!", "success")

            if not user.is_verified and user.role == "user":
                flash(
                    "Your email address is not yet verified. You must verify your email before submitting complaints.",
                    "warning",
                )

            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            if user.role in ("handler", "admin"):
                return redirect(url_for("admin.queue"))
            return redirect(url_for("complaints.my_complaints"))
        else:
            flash("Invalid email address or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/verify/<token>")
def verify_email(token):
    """
    Validates token, enforces expiration and single-use,
    and marks user as verified. Never exposes raw token in responses.
    """
    success, message, user = verify_token(token)
    if success:
        flash(message, "success")
        if not current_user.is_authenticated and user:
            login_user(user)
        return redirect(url_for("complaints.my_complaints"))
    else:
        flash(message, "danger")
        return redirect(url_for("auth.resend_verification"))


@auth_bp.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    form = ResendVerificationForm()
    if request.method == "GET" and current_user.is_authenticated:
        form.email.data = current_user.email

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if not user:
            # Avoid user enumeration in public responses
            flash("If an unverified account exists for this email, a verification link has been sent.", "info")
            return redirect(url_for("auth.login"))

        if user.is_verified:
            flash("This account is already verified. You may log in directly.", "info")
            return redirect(url_for("auth.login"))

        can_resend, cooldown_msg = can_resend_verification(user)
        if not can_resend:
            flash(cooldown_msg, "warning")
            return render_template("auth/resend_verification.html", form=form)

        raw_token, _ = create_verification_token(user)
        sent, err = send_verification_email(user, raw_token)
        if sent:
            flash("A new verification email has been sent. Please check your inbox or Mailpit test interface.", "success")
        else:
            flash(f"Email dispatch encountered an issue: {err}", "danger")

        return redirect(url_for("auth.verification_guidance", email=user.email))

    return render_template("auth/resend_verification.html", form=form)


@auth_bp.route("/verification-guidance")
def verification_guidance():
    email = request.args.get("email", "")
    return render_template("auth/verification_guidance.html", email=email)
