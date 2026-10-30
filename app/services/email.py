import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
import secrets
import logging
from flask import current_app, url_for
from app.extensions import db
from app.models.user import User, VerificationToken

logger = logging.getLogger(__name__)


def create_verification_token(user: User) -> tuple[str, VerificationToken]:
    """
    Generates a secure random verification token, hashes it, and stores the hash.
    Returns (raw_token, token_record).
    The raw token is only returned to be transmitted via email.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = VerificationToken.hash_token(raw_token)
    
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=current_app.config.get("TOKEN_EXPIRATION_HOURS", 24)
    )
    
    token_record = VerificationToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.session.add(token_record)
    db.session.commit()
    
    return raw_token, token_record


def can_resend_verification(user: User) -> tuple[bool, str]:
    """Check rate-limiting for resending verification tokens."""
    cooldown = current_app.config.get("RESEND_COOLDOWN_SECONDS", 60)
    last_token = (
        VerificationToken.query.filter_by(user_id=user.id)
        .order_by(VerificationToken.created_at.desc())
        .first()
    )
    if last_token:
        created_at = last_token.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - created_at).total_seconds()
        if elapsed < cooldown:
            remaining = int(cooldown - elapsed)
            return False, f"Please wait {remaining} seconds before requesting a new verification email."
    return True, ""


def send_verification_email(user: User, raw_token: str) -> tuple[bool, str]:
    """
    Sends email with the verification link via SMTP.
    Works with local Mailpit or standard SMTP servers.
    Does NOT log the raw token.
    """
    public_base_url = current_app.config.get("PUBLIC_BASE_URL", "").rstrip("/")
    if public_base_url:
        verify_url = f"{public_base_url}/auth/verify/{raw_token}"
    else:
        verify_url = url_for("auth.verify_email", token=raw_token, _external=True)
    
    server_host = current_app.config.get("SMTP_SERVER", "localhost")
    server_port = current_app.config.get("SMTP_PORT", 1025)
    sender = current_app.config.get("SMTP_DEFAULT_SENDER", "CampusVoice <noreply@campus.edu>")
    username = current_app.config.get("SMTP_USERNAME", "")
    password = current_app.config.get("SMTP_PASSWORD", "")
    use_tls = current_app.config.get("SMTP_USE_TLS", False)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify Your College Email - CampusVoice"
    msg["From"] = sender
    msg["To"] = user.email

    text_content = f"""Hello {user.full_name},

Thank you for registering on CampusVoice.
Please verify your college email address by clicking the link below:

{verify_url}

This link is single-use and will expire in {current_app.config.get('TOKEN_EXPIRATION_HOURS', 24)} hours.

Notice: This is a hackathon prototype/demo verification system.
If you did not request this registration, please ignore this email.
"""

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 6px;">
          <h2 style="color: #0d6efd;">CampusVoice Verification</h2>
          <p>Hello <strong>{user.full_name}</strong>,</p>
          <p>Please click the button below to verify your email address and activate your account:</p>
          <p style="text-align: center; margin: 30px 0;">
            <a href="{verify_url}" style="background-color: #0d6efd; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">
              Verify Email Address
            </a>
          </p>
          <p style="font-size: 13px; color: #666;">Or copy and paste this link into your browser:<br>
            <a href="{verify_url}">{verify_url}</a>
          </p>
          <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
          <p style="font-size: 12px; color: #888;">
            <em>Note: Locally captured email verification is configured for demo/prototype testing (e.g., Mailpit). Token is single-use and valid for {current_app.config.get('TOKEN_EXPIRATION_HOURS', 24)} hours.</em>
          </p>
        </div>
      </body>
    </html>
    """

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        if use_tls:
            server = smtplib.SMTP(server_host, server_port, timeout=5)
            server.starttls()
            if username and password:
                server.login(username, password)
            server.sendmail(sender, [user.email], msg.as_string())
            server.quit()
        else:
            with smtplib.SMTP(server_host, server_port, timeout=5) as server:
                if username and password:
                    server.login(username, password)
                server.sendmail(sender, [user.email], msg.as_string())
        
        logger.info(f"Verification email successfully dispatched to {user.email}")
        return True, "Verification email sent successfully."
    except Exception as e:
        logger.warning(f"SMTP dispatch failed to {user.email}: {e}")
        return False, f"Could not connect to SMTP server ({server_host}:{server_port}). You can retry resending."


def verify_token(raw_token: str) -> tuple[bool, str, User | None]:
    """
    Validates a submitted raw verification token.
    Enforces expiration, single-use, and attempt limits.
    """
    token_hash = VerificationToken.hash_token(raw_token)
    token_record = VerificationToken.query.filter_by(token_hash=token_hash).first()

    if not token_record:
        return False, "Invalid or unrecognized verification token.", None

    max_attempts = current_app.config.get("MAX_VERIFICATION_ATTEMPTS", 5)
    token_record.attempts += 1

    if token_record.attempts > max_attempts:
        db.session.commit()
        return False, "Too many verification attempts for this token. Please request a new one.", None

    if token_record.used_at is not None:
        db.session.commit()
        return False, "This verification token has already been used.", None

    if token_record.is_expired():
        db.session.commit()
        return False, "This verification link has expired. Please request a new one.", None

    # Mark token used and verify user
    user = User.query.get(token_record.user_id)
    if not user:
        return False, "Associated user account not found.", None

    token_record.used_at = datetime.now(timezone.utc)
    user.is_verified = True
    db.session.commit()

    return True, "Email address successfully verified! You may now submit complaints.", user
