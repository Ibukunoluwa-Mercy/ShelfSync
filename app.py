import os
import sqlite3
from functools import wraps

from flask import Flask, flash, redirect, render_template, session, url_for

from database import close_db, init_db


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "dev-only-change-this-secret-key",
)  # Set SECRET_KEY in production.
app.teardown_appcontext(close_db)


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


@app.route("/_layout-test")
def layout_test():
    """Temporary visual test route; remove when real pages are added."""
    return render_template(
        "base_app.html",
        page_title="Layout Test",
        demo_page=True,
    )


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
