import smtplib
import json
import urllib.request
import urllib.error
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


def _send_via_resend(user: User, sender: str, text_content: str, html_content: str, api_key: str) -> tuple[bool, str]:
    """Dispatches verification email via Resend HTTPS REST API."""
    if not api_key:
        return False, "Resend API key is not configured in environment variables (RESEND_API_KEY)."

    url = "https://api.resend.com/emails"
    payload = {
        "from": sender,
        "to": [user.email],
        "subject": "Verify Your College Email - CampusVoice",
        "html": html_content,
        "text": text_content,
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "CampusVoice-Mailer/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode("utf-8", errors="replace")
            res_json = json.loads(resp_body) if resp_body else {}
            email_id = res_json.get("id", "dispatched")
            logger.info(f"Verification email successfully dispatched to {user.email} via Resend HTTPS API (id={email_id})")
            return True, "Verification email sent successfully via Resend."
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            err_msg = err_json.get("message") or err_json.get("error") or err_body
        except Exception:
            err_msg = err_body
        logger.warning(f"Resend HTTPS dispatch failed ({e.code}) for {user.email}: {err_msg}")
        return False, f"Resend API error ({e.code}): {err_msg}"
    except Exception as e:
        logger.warning(f"Resend HTTPS dispatch network exception for {user.email}: {e}")
        return False, f"Resend network error: {str(e)}"


def _send_via_sendgrid(user: User, sender: str, text_content: str, html_content: str, api_key: str) -> tuple[bool, str]:
    """Dispatches verification email via SendGrid HTTPS REST API (v3/mail/send)."""
    if not api_key:
        return False, "SendGrid API key is not configured in environment variables (SENDGRID_API_KEY)."

    # Extract sender email and optional display name
    sender_name = "CampusVoice Portal"
    sender_email = sender
    if "<" in sender and ">" in sender:
        parts = sender.split("<")
        sender_name = parts[0].strip() or sender_name
        sender_email = parts[1].replace(">", "").strip()

    url = "https://api.sendgrid.com/v3/mail/send"
    payload = {
        "personalizations": [{"to": [{"email": user.email, "name": user.full_name}]}],
        "from": {"email": sender_email, "name": sender_name},
        "subject": "Verify Your College Email - CampusVoice",
        "content": [
            {"type": "text/plain", "value": text_content},
            {"type": "text/html", "value": html_content},
        ],
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "CampusVoice-Mailer/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            # SendGrid returns 202 Accepted on success
            if resp.status in (200, 201, 202):
                logger.info(f"Verification email successfully dispatched to {user.email} via SendGrid HTTPS API")
                return True, "Verification email sent successfully via SendGrid."
            return False, f"SendGrid returned unexpected HTTP status {resp.status}."
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        logger.warning(f"SendGrid HTTPS dispatch failed ({e.code}) for {user.email}: {err_body}")
        return False, f"SendGrid API error ({e.code}): {err_body[:200]}"
    except Exception as e:
        logger.warning(f"SendGrid HTTPS dispatch network exception for {user.email}: {e}")
        return False, f"SendGrid network error: {str(e)}"


def _send_via_console(user: User, verify_url: str) -> tuple[bool, str]:
    """Captures verification link in application logs (for demo/staging environments)."""
    logger.info("=" * 70)
    logger.info(f"[CONSOLE EMAIL ADAPTER] Recipient: {user.email} ({user.full_name})")
    logger.info(f"[CONSOLE EMAIL ADAPTER] Verification URL: {verify_url}")
    logger.info("=" * 70)
    return True, "Verification email captured in application console logs."


def _send_via_smtp(user: User, sender: str, msg: MIMEMultipart, server_host: str, server_port: int, username: str, password: str, use_tls: bool) -> tuple[bool, str]:
    """Dispatches verification email via standard SMTP."""
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

        logger.info(f"Verification email successfully dispatched to {user.email} via SMTP")
        return True, "Verification email sent successfully."
    except Exception as e:
        logger.warning(f"SMTP dispatch failed to {user.email}: {e}")
        return False, f"Could not connect to SMTP server ({server_host}:{server_port}). You can retry resending."


def send_verification_email(user: User, raw_token: str) -> tuple[bool, str]:
    """
    Sends email with the verification link via configured transport:
    - HTTPS Resend API (EMAIL_PROVIDER='resend' or RESEND_API_KEY present)
    - HTTPS SendGrid API (EMAIL_PROVIDER='sendgrid' or SENDGRID_API_KEY present)
    - Console Adapter (EMAIL_PROVIDER='console')
    - SMTP Transport (fallback / local Mailpit)
    
    Security:
    - Never logs or exposes raw verification token in API responses.
    - Preserves single-use token lifecycle and domain validation.
    """
    public_base_url = current_app.config.get("PUBLIC_BASE_URL", "").rstrip("/")
    if public_base_url:
        verify_url = f"{public_base_url}/auth/verify/{raw_token}"
    else:
        verify_url = url_for("auth.verify_email", token=raw_token, _external=True)

    sender = current_app.config.get("SMTP_DEFAULT_SENDER", "CampusVoice Portal <noreply@campus.edu>")
    provider = (current_app.config.get("EMAIL_PROVIDER") or "").strip().lower()
    resend_key = current_app.config.get("RESEND_API_KEY", "").strip()
    sendgrid_key = current_app.config.get("SENDGRID_API_KEY", "").strip()

    text_content = f"""Hello {user.full_name},

Thank you for registering on CampusVoice.
Please verify your college email address by clicking the link below:

{verify_url}

This link is single-use and will expire in {current_app.config.get('TOKEN_EXPIRATION_HOURS', 24)} hours.

Notice: This is a verified campus reporting system.
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
            <em>Token is single-use and valid for {current_app.config.get('TOKEN_EXPIRATION_HOURS', 24)} hours.</em>
          </p>
        </div>
      </body>
    </html>
    """

    # 1. Console provider (for development or staging environments without external credentials)
    if provider == "console":
        return _send_via_console(user, verify_url)

    # 2. Resend HTTPS provider
    if provider == "resend" or (not provider and resend_key):
        return _send_via_resend(user, sender, text_content, html_content, resend_key)

    # 3. SendGrid HTTPS provider
    if provider == "sendgrid" or (not provider and sendgrid_key):
        return _send_via_sendgrid(user, sender, text_content, html_content, sendgrid_key)

    # 4. Standard SMTP provider (works with local Mailpit or configured SMTP server)
    server_host = current_app.config.get("SMTP_SERVER", "localhost")
    server_port = current_app.config.get("SMTP_PORT", 1025)
    username = current_app.config.get("SMTP_USERNAME", "")
    password = current_app.config.get("SMTP_PASSWORD", "")
    use_tls = current_app.config.get("SMTP_USE_TLS", False)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify Your College Email - CampusVoice"
    msg["From"] = sender
    msg["To"] = user.email
    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    return _send_via_smtp(user, sender, msg, server_host, server_port, username, password, use_tls)


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
    user = db.session.get(User, token_record.user_id)
    if not user:
        return False, "Associated user account not found.", None

    token_record.used_at = datetime.now(timezone.utc)
    user.is_verified = True
    db.session.commit()

    return True, "Email address successfully verified! You may now submit complaints.", user
