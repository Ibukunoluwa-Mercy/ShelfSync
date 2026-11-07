import hashlib
import os
import re
import secrets
from urllib.parse import urljoin

from flask import current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db
from emailer import send_password_changed_email, send_reset_email

TOKEN_REGEX = re.compile(r"^[A-Za-z0-9_-]{43}$")
RESET_COOLDOWN_SECONDS = 60
RESET_MAX_PER_EMAIL_PER_HOUR = 3
RESET_MAX_PER_IP_PER_HOUR = 10


def handle_forgot_password(logger):
    """Process password reset requests with silent rate limiting and neutral responses."""
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    form_values = {"email": ""}
    errors = {}

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        form_values["email"] = email

        if not email:
            errors["email"] = "Please enter your email address."
        elif len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            errors["email"] = "Please enter a valid email address."

        if errors:
            return render_template("forgot_password.html", form_values=form_values, errors=errors), 400

        client_ip = request.remote_addr or "127.0.0.1"
        db = get_db()
        try:
            # Housekeeping: remove request rows and resets older than 1 day
            db.execute("DELETE FROM password_reset_requests WHERE requested_at < datetime('now', '-1 day')")
            db.execute("DELETE FROM password_resets WHERE created_at < datetime('now', '-1 day')")

            email_reqs_hour = db.execute(
                "SELECT COUNT(*) FROM password_reset_requests WHERE email = ? AND requested_at >= datetime('now', '-1 hour')",
                (email,),
            ).fetchone()[0]

            ip_reqs_hour = db.execute(
                "SELECT COUNT(*) FROM password_reset_requests WHERE ip_address = ? AND requested_at >= datetime('now', '-1 hour')",
                (client_ip,),
            ).fetchone()[0]

            recent_req = db.execute(
                "SELECT COUNT(*) FROM password_reset_requests WHERE email = ? AND requested_at >= datetime('now', '-60 seconds')",
                (email,),
            ).fetchone()[0]

            blocked = (
                email_reqs_hour >= RESET_MAX_PER_EMAIL_PER_HOUR
                or ip_reqs_hour >= RESET_MAX_PER_IP_PER_HOUR
                or recent_req > 0
            )

            db.execute(
                "INSERT INTO password_reset_requests (email, ip_address) VALUES (?, ?)",
                (email, client_ip),
            )
            db.commit()

            if not blocked:
                user = db.execute(
                    "SELECT id, full_name, email FROM users WHERE email = ? COLLATE NOCASE",
                    (email,),
                ).fetchone()

                if user:
                    # Invalidate existing unused tokens for this user
                    db.execute(
                        "DELETE FROM password_resets WHERE user_id = ? AND used_at IS NULL",
                        (user["id"],),
                    )
                    token = secrets.token_urlsafe(32)
                    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

                    db.execute(
                        """
                        INSERT INTO password_resets (user_id, token_hash, expires_at, requested_ip)
                        VALUES (?, ?, datetime('now', '+30 minutes'), ?)
                        """,
                        (user["id"], token_hash, client_ip),
                    )
                    db.commit()

                    base_url = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
                    reset_url = f"{base_url}{url_for('reset_password', token=token)}"
                    send_reset_email(user, reset_url)
        except Exception:
            db.rollback()
            logger.exception("Error processing forgot password request")

        flash(
            "If an account exists for that email, we've sent a password reset link. It expires in 30 minutes.",
            "success",
        )
        return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html", form_values=form_values, errors=errors)


def find_valid_reset(db, token):
    """Retrieve active reset record if token is valid, unexpired, and unused."""
    if not token or not TOKEN_REGEX.match(token):
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return db.execute(
        """
        SELECT pr.id, pr.user_id, u.email, u.full_name, u.password_hash
        FROM password_resets pr
        JOIN users u ON u.id = pr.user_id
        WHERE pr.token_hash = ? AND pr.used_at IS NULL AND pr.expires_at > datetime('now')
        """,
        (token_hash,),
    ).fetchone()


def handle_reset_password(token, logger):
    """Validate password reset token and update user credentials."""
    db = get_db()
    reset_record = find_valid_reset(db, token)

    if not reset_record:
        response = render_template("reset_password.html", invalid_link=True)
        return response, 400, {
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store, no-cache, must-revalidate",
        }

    errors = {}
    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not new_password:
            errors["new_password"] = "Please enter a new password."
        elif not 8 <= len(new_password) <= 128:
            errors["new_password"] = "Password must be between 8 and 128 characters."
        elif not re.search(r"[A-Za-z]", new_password) or not re.search(r"\d", new_password):
            errors["new_password"] = "Password must include at least one letter and one number."
        elif new_password.lower() == reset_record["email"].lower():
            errors["new_password"] = "Password cannot be the same as your email."
        elif check_password_hash(reset_record["password_hash"], new_password):
            errors["new_password"] = "Please choose a password you haven't used before."

        if not confirm_password:
            errors["confirm_password"] = "Please confirm your new password."
        elif new_password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        if errors:
            return (
                render_template("reset_password.html", token=token, errors=errors, invalid_link=False),
                400,
                {"Referrer-Policy": "no-referrer", "Cache-Control": "no-store, no-cache, must-revalidate"},
            )

        try:
            db.execute("BEGIN IMMEDIATE")
            # Re-check token within immediate transaction to prevent race conditions
            current_reset = find_valid_reset(db, token)
            if not current_reset:
                db.rollback()
                return (
                    render_template("reset_password.html", invalid_link=True),
                    400,
                    {"Referrer-Policy": "no-referrer", "Cache-Control": "no-store, no-cache, must-revalidate"},
                )

            new_hash = generate_password_hash(new_password)
            db.execute(
                "UPDATE users SET password_hash = ?, session_version = session_version + 1 WHERE id = ?",
                (new_hash, current_reset["user_id"]),
            )
            db.execute(
                "UPDATE password_resets SET used_at = CURRENT_TIMESTAMP WHERE id = ?",
                (current_reset["id"],),
            )
            db.commit()

            send_password_changed_email(current_reset)
            flash("Your password has been reset successfully. Please sign in.", "success")
            return redirect(url_for("login"))
        except Exception:
            db.rollback()
            logger.exception("Failed to update user password during reset")
            flash("Something went wrong. Please try again.", "danger")
            return (
                render_template("reset_password.html", token=token, errors={}, invalid_link=False),
                500,
                {"Referrer-Policy": "no-referrer", "Cache-Control": "no-store, no-cache, must-revalidate"},
            )

    return (
        render_template("reset_password.html", token=token, errors=errors, invalid_link=False),
        200,
        {"Referrer-Policy": "no-referrer", "Cache-Control": "no-store, no-cache, must-revalidate"},
    )

