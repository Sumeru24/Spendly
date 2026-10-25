import os
import re
import sqlite3

from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

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


@app.route("/login")
def login():
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
    return "Logout — coming in Step 3"


@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


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
