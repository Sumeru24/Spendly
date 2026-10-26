import os
import re
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import close_db, get_db, init_db, seed_db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.teardown_appcontext(close_db)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.cli.command("init-db")
def init_db_command():
    init_db()
    print("Initialized the database.")


@app.cli.command("seed-db")
def seed_db_command():
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        error = None
        if not name or not email or not password or not confirm_password:
            error = "All fields are required."
        elif not 2 <= len(name) <= 80:
            error = "Name must be between 2 and 80 characters."
        elif not EMAIL_PATTERN.match(email):
            error = "Enter a valid email address."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm_password:
            error = "Passwords do not match."

        if error is None:
            db = get_db()
            existing = db.execute(
                "SELECT 1 FROM users WHERE email = ?", (email,)
            ).fetchone()
            if existing is not None:
                error = "Email already registered."
            else:
                try:
                    with db:
                        db.execute(
                            "INSERT INTO users (name, email, password_hash) "
                            "VALUES (?, ?, ?)",
                            (name, email, generate_password_hash(password)),
                        )
                except sqlite3.IntegrityError:
                    error = "Email already registered."

        if error is None:
            flash("Account created successfully. Please sign in.", "success")
            return redirect(url_for("login"))

        return render_template("register.html", error=error, name=name, email=email)

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        error = None
        if not email or not password:
            error = "Invalid email or password."
        else:
            db = get_db()
            user = db.execute(
                "SELECT id, name, password_hash FROM users WHERE email = ?",
                (email.lower(),),
            ).fetchone()
            if user is None or not check_password_hash(
                user["password_hash"], password
            ):
                error = "Invalid email or password."

        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("profile"))

        flash(error, "error")
        return render_template("login.html", email=email)

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name": "Demo User",
        "email": "demo@spendly.test",
        "initials": "DU",
        "member_since": "October 2026",
    }

    stats = {
        "total_spent": "₹1,519.75",
        "transaction_count": 6,
        "top_category": "Rent",
    }

    transactions = [
        {
            "date": "2026-10-24",
            "description": "Weekly supermarket run",
            "category": "Groceries",
            "amount": "₹85.50",
        },
        {
            "date": "2026-10-21",
            "description": "Monthly transit pass",
            "category": "Transport",
            "amount": "₹32.00",
        },
        {
            "date": "2026-10-18",
            "description": "Dinner with friends",
            "category": "Dining",
            "amount": "₹46.75",
        },
        {
            "date": "2026-10-14",
            "description": "Electricity bill",
            "category": "Utilities",
            "amount": "₹120.00",
        },
        {
            "date": "2026-10-11",
            "description": "Monthly rent",
            "category": "Rent",
            "amount": "₹1,200.00",
        },
        {
            "date": "2026-10-06",
            "description": "Pharmacy",
            "category": "Health",
            "amount": "₹35.50",
        },
    ]

    categories = [
        {"name": "Rent", "amount": "₹1,200.00", "pct": 79},
        {"name": "Utilities", "amount": "₹120.00", "pct": 8},
        {"name": "Groceries", "amount": "₹85.50", "pct": 6},
        {"name": "Dining", "amount": "₹46.75", "pct": 3},
        {"name": "Health", "amount": "₹35.50", "pct": 2},
        {"name": "Transport", "amount": "₹32.00", "pct": 2},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
