import os
import re
import secrets
import sqlite3
from logging import getLogger
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from database import close_db, init_db


app = Flask(__name__)
logger = getLogger(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "dev-only-change-this-secret-key",
)  # Set SECRET_KEY in production.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.teardown_appcontext(close_db)
with app.app_context():
    init_db()


@app.template_filter("naira")
def format_naira(value):
    """Format a number as Nigerian Naira."""
    try:
        return f"₦{float(value):,.0f}"
    except (TypeError, ValueError):
        raise ValueError("The naira filter requires a numeric value")


@app.context_processor
def inject_shop_name():
    return {"shop_name": "ShelfSync"}


def get_csrf_token():
    """Create and return the session token used to protect POST forms."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = get_csrf_token


@app.before_request
def validate_csrf_token():
    """Reject every POST without the token generated for the current session."""
    if request.method == "POST":
        submitted_token = request.form.get("csrf_token", "")
        session_token = session.get("csrf_token", "")
        if not session_token or not secrets.compare_digest(
            submitted_token, session_token
        ):
            flash("Your session expired. Please try again.", "warning")
            return redirect(request.referrer or url_for("homepage"))
    return None


def login_required(view):
    """Require a signed-in user before allowing access to a view."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("layout_test"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    """Require a signed-in administrator before allowing access to a view."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Administrator access is required.", "danger")
            return redirect(url_for("layout_test"))
        return view(*args, **kwargs)

    return wrapped_view


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.route("/")
def homepage():
    return render_template("homepage.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Create a staff account, or the first admin account for the shop."""
    if session.get("user_id"):
        # Point this redirect at the dashboard once that route exists.
        return redirect(url_for("homepage"))

    form_values = {"full_name": "", "email": ""}
    errors = {}
    if request.method == "POST":
        full_name = " ".join(request.form.get("full_name", "").strip().split())
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        form_values = {"full_name": full_name, "email": email}

        if not full_name:
            errors["full_name"] = "Please enter your full name."
        elif not 2 <= len(full_name) <= 100:
            errors["full_name"] = "Full name must be between 2 and 100 characters."

        if not email:
            errors["email"] = "Please enter your email address."
        elif (
            len(email) > 254
            or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
        ):
            errors["email"] = "Please enter a valid email address."
        elif get_db().execute(
            "SELECT 1 FROM users WHERE email = ? COLLATE NOCASE", (email,)
        ).fetchone():
            errors["email"] = (
                "An account with this email already exists. Try signing in."
            )

        if not password:
            errors["password"] = "Please enter a password."
        elif not 8 <= len(password) <= 128:
            errors["password"] = "Password must be between 8 and 128 characters."
        elif not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            errors["password"] = (
                "Password must include at least one letter and one number."
            )
        elif password.lower() == email.lower():
            errors["password"] = "Password cannot be the same as your email."

        if password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        if errors:
            return render_template(
                "register.html", form_values=form_values, errors=errors
            ), 400

        db = get_db()
        try:
            db.execute("BEGIN IMMEDIATE")
            user_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            role = "admin" if user_count == 0 else "staff"
            db.execute(
                """
                INSERT INTO users (full_name, email, password_hash, role)
                VALUES (?, ?, ?, ?)
                """,
                (full_name, email, generate_password_hash(password), role),
            )
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            errors["email"] = (
                "An account with this email already exists. Try signing in."
            )
            return render_template(
                "register.html", form_values=form_values, errors=errors
            ), 400
        except sqlite3.Error:
            db.rollback()
            logger.exception("Could not create an account")
            flash("Something went wrong. Please try again.", "danger")
            return render_template(
                "register.html", form_values=form_values, errors={}
            ), 500

        if role == "admin":
            flash(
                "Welcome! Your admin account has been created. Please sign in.",
                "success",
            )
        else:
            flash("Account created successfully. Please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form_values=form_values, errors=errors)


@app.route("/login")
def login():
    # TEMPORARY: replaced when the Login page is built.
    return "Login page coming soon."


@app.route("/_layout-test")
def layout_test():
    """Temporary visual test route; remove when real pages are added."""
    return render_template(
        "base_app.html",
        page_title="Layout Test",
        demo_page=True,
    )


if __name__ == "__main__":
    app.run(debug=True)
