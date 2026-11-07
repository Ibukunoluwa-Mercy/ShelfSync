import logging
import os
import smtplib
import threading
from email.message import EmailMessage
from markupsafe import escape

logger = logging.getLogger(__name__)


def send_email_sync(to_address, subject, text_body, html_body):
    """Deliver an email via SMTP or output to terminal if SMTP_HOST is unset."""
    clean_to = "".join(to_address.splitlines()).strip()
    clean_sub = "".join(subject.splitlines()).strip()

    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_from = os.environ.get("SMTP_FROM", "ShelfSync <no-reply@shelfsync.local>").strip()

    if not smtp_host:
        print("\n" + "=" * 60)
        print("===== DEV EMAIL (SMTP not configured) =====")
        print(f"To:      {clean_to}")
        print(f"Subject: {clean_sub}")
        print("-" * 60)
        print(text_body.strip())
        print("=" * 60 + "\n")
        logger.warning("SMTP_HOST is not configured; simulated email logged to terminal.")
        return

    try:
        msg = EmailMessage()
        msg["From"] = smtp_from
        msg["To"] = clean_to
        msg["Subject"] = clean_sub
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")

        port = int(os.environ.get("SMTP_PORT", 587))
        username = os.environ.get("SMTP_USERNAME", "").strip()
        password = os.environ.get("SMTP_PASSWORD", "")

        with smtplib.SMTP(smtp_host, port, timeout=10) as server:
            server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)
    except Exception:
        logger.exception("Failed to deliver email message to recipient")


def send_email(to_address, subject, text_body, html_body):
    """Dispatch email delivery asynchronously in a background daemon thread."""
    thread = threading.Thread(
        target=send_email_sync,
        args=(to_address, subject, text_body, html_body),
        daemon=True,
    )
    thread.start()


def send_reset_email(user, reset_url):
    """Send a secure password reset link to the account owner."""
    raw_name = str(user["full_name"] if "full_name" in user.keys() else "").strip()
    first_name = raw_name.split()[0] if raw_name else "there"
    safe_name = escape(first_name)

    subject = "Reset your ShelfSync password"
    text_body = f"""Hello {first_name},

Someone requested a link to reset the password for your ShelfSync account.

You can reset your password using the link below:
{reset_url}

This link expires in 30 minutes and can only be used once.

If you didn't ask for this, you can ignore this email. Your password will not change.

— The ShelfSync Team
"""

    html_body = f"""<!doctype html>
<html>
<body style="background-color:#FEFAE0;font-family:sans-serif;color:#1f2937;padding:32px;margin:0;">
  <div style="background-color:#ffffff;max-width:540px;margin:0 auto;padding:32px;border-radius:16px;border:1px solid #e5e0c8;">
    <h2 style="margin-top:0;"><span style="color:#2D6A4F;">Shelf</span><span style="color:#D4A373;">Sync</span></h2>
    <h3 style="color:#2D6A4F;margin-bottom:12px;">Reset Your Password</h3>
    <p>Hello {safe_name},</p>
    <p>Someone requested a link to reset the password for your ShelfSync account.</p>
    <div style="margin:24px 0;text-align:center;">
      <a href="{reset_url}" style="background-color:#2D6A4F;color:#ffffff;padding:12px 24px;border-radius:999px;text-decoration:none;font-weight:bold;display:inline-block;">Reset Password</a>
    </div>
    <p style="font-size:0.9em;color:#4b5563;">This link expires in 30 minutes and can only be used once.</p>
    <p style="font-size:0.85em;color:#6b7280;margin-top:24px;">If you didn't ask for this, you can ignore this email. Your password will not change.</p>
  </div>
</body>
</html>"""

    send_email(user["email"], subject, text_body, html_body)


def send_password_changed_email(user):
    """Notify the user that their password was modified."""
    try:
        raw_name = str(user["full_name"] if "full_name" in user.keys() else "").strip()
        first_name = raw_name.split()[0] if raw_name else "there"
        safe_name = escape(first_name)

        subject = "Your ShelfSync password was changed"
        text_body = f"""Hello {first_name},

Your ShelfSync password was just changed.

If this wasn't you, contact your shop administrator immediately to secure your account.

— The ShelfSync Team
"""

        html_body = f"""<!doctype html>
<html>
<body style="background-color:#FEFAE0;font-family:sans-serif;color:#1f2937;padding:32px;margin:0;">
  <div style="background-color:#ffffff;max-width:540px;margin:0 auto;padding:32px;border-radius:16px;border:1px solid #e5e0c8;">
    <h2 style="margin-top:0;"><span style="color:#2D6A4F;">Shelf</span><span style="color:#D4A373;">Sync</span></h2>
    <h3 style="color:#2D6A4F;margin-bottom:12px;">Password Changed</h3>
    <p>Hello {safe_name},</p>
    <p>Your ShelfSync password was just changed.</p>
    <p style="color:#b3402a;font-weight:bold;">If this wasn't you, contact your shop administrator immediately to secure your account.</p>
  </div>
</body>
</html>"""

        send_email(user["email"], subject, text_body, html_body)
    except Exception:
        logger.exception("Failed to send password changed notification email")
