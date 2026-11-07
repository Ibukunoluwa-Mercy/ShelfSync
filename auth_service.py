import re
import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database import get_db

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
SESSION_HOURS = 8
DUMMY_PASSWORD_HASH = (
    "scrypt:32768:8:1$dummy$d1a6c085020959f63628e9d8e788ad72fb4fa980f845a7d77b8"
    "d0e70404fa3a067087e594d40a1b6352c803527aa1e2de66c6b8c8d827299a910ecb2aa712a64"
)


def is_safe_url(target):
    """Validate relative redirection targets to prevent open-redirect attacks."""
    if not target or target.startswith("//") or "\\" in target or not target.startswith("/"):
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc


def login_required(view):
    """Require an authenticated user and verify user still exists in the database."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        db = get_db()
        user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            session.clear()
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    """Require an active user with admin role privileges."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("role") != "admin":
            flash("You do not have permission to open that page.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)

    return wrapped_view


def handle_login(logger):
    """Process user login authentication, rate limiting and session establishment."""
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    raw_next = request.args.get("next") or request.form.get("next") or ""
    next_url = raw_next if is_safe_url(raw_next) else ""
    form_values = {"email": ""}
    errors = {}

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        form_values["email"] = email

        if not email:
            errors["email"] = "Please enter your email address."
        elif len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            errors["email"] = "Please enter a valid email address."

        if not password:
            errors["password"] = "Please enter your password."

        if errors:
            return render_template("login.html", form_values=form_values, errors=errors, next_url=next_url), 400

        client_ip = request.remote_addr or "127.0.0.1"
        db = get_db()
        failures = db.execute(
            """
            SELECT COUNT(*) FROM login_attempts
            WHERE email = ? AND ip_address = ? AND success = 0
              AND attempted_at >= datetime('now', '-15 minutes')
            """,
            (email, client_ip),
        ).fetchone()[0]

        if failures >= MAX_FAILED_ATTEMPTS:
            flash("Too many failed attempts. Please wait 15 minutes and try again, or use Forgot Password.", "warning")
            return render_template("login.html", form_values=form_values, errors={}, next_url=next_url), 429

        user = db.execute(
            "SELECT id, full_name, email, password_hash, role FROM users WHERE email = ? COLLATE NOCASE",
            (email,),
        ).fetchone()

        valid = False
        if len(password) <= 128:
            if user:
                valid = check_password_hash(user["password_hash"], password)
            else:
                check_password_hash(DUMMY_PASSWORD_HASH, password)
        else:
            check_password_hash(DUMMY_PASSWORD_HASH, "dummy")

        if not valid:
            try:
                db.execute(
                    "INSERT INTO login_attempts (email, ip_address, success) VALUES (?, ?, 0)",
                    (email, client_ip),
                )
                db.commit()
            except Exception:
                db.rollback()
            errors["general"] = "Invalid email or password."
            return render_template("login.html", form_values=form_values, errors=errors, next_url=next_url), 401

        try:
            db.execute("DELETE FROM login_attempts WHERE email = ? AND success = 0", (email,))
            db.execute("INSERT INTO login_attempts (email, ip_address, success) VALUES (?, ?, 1)", (email, client_ip))
            db.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to record login timestamp")
            flash("Something went wrong. Please try again.", "danger")
            return render_template("login.html", form_values=form_values, errors={}, next_url=next_url), 500

        session.clear()
        session["user_id"] = user["id"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]
        session["csrf_token"] = secrets.token_hex(32)
        session.permanent = True

        first_name = user["full_name"].strip().split()[0] if user["full_name"] else "there"
        flash(f"Welcome back, {first_name}!", "success")
        return redirect(next_url if next_url else url_for("dashboard"))

    return render_template("login.html", form_values=form_values, errors=errors, next_url=next_url)

