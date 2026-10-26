import calendar
import math
import os
import re
import sqlite3
from datetime import date, datetime

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import close_db, get_db, init_db, seed_db
from database.queries import (
    delete_expense as delete_expense_row,
    get_category_breakdown,
    get_expense_by_id,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
    insert_expense,
    update_expense,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.teardown_appcontext(close_db)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EXPENSE_CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)


def _expense_form_from_request():
    return {
        "amount": request.form.get("amount", "").strip(),
        "category": request.form.get("category", "").strip(),
        "date": request.form.get("date", "").strip(),
        "description": request.form.get("description", "").strip(),
    }


def _validate_expense_form(form):
    amount = None
    error = None

    try:
        amount = float(form["amount"])
    except (TypeError, ValueError):
        error = "Enter a valid amount greater than 0."
    else:
        if not math.isfinite(amount) or amount <= 0:
            error = "Enter a valid amount greater than 0."

    if error is None and form["category"] not in EXPENSE_CATEGORIES:
        error = "Select a valid category."

    expense_date = None
    if error is None:
        try:
            expense_date = datetime.strptime(form["date"], "%Y-%m-%d").date()
        except ValueError:
            error = "Enter a valid date."

    return error, amount, expense_date


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


def _format_currency(amount):
    return f"₹{amount:,.2f}"


def _initials_for(name):
    parts = name.split()
    return "".join(part[0] for part in parts[:2]).upper() or "?"


def _parse_iso_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _months_before(day, months):
    month_index = day.year * 12 + (day.month - 1) - months
    year, month = divmod(month_index, 12)
    month += 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def _profile_presets(today):
    return [
        {
            "label": "This Month",
            "date_from": today.replace(day=1).isoformat(),
            "date_to": today.isoformat(),
        },
        {
            "label": "Last 3 Months",
            "date_from": _months_before(today, 3).isoformat(),
            "date_to": today.isoformat(),
        },
        {
            "label": "Last 6 Months",
            "date_from": _months_before(today, 6).isoformat(),
            "date_to": today.isoformat(),
        },
        {
            "label": "All Time",
            "date_from": None,
            "date_to": None,
        },
    ]


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        flash("Your session has expired. Please sign in again.", "error")
        return redirect(url_for("login"))

    user["initials"] = _initials_for(user["name"])

    date_from = _parse_iso_date(request.args.get("date_from", "").strip())
    date_to = _parse_iso_date(request.args.get("date_to", "").strip())
    if date_from is None or date_to is None:
        date_from = None
        date_to = None
    elif date_from > date_to:
        flash("Start date must be before end date.", "error")
        date_from = None
        date_to = None

    filter_from = date_from.isoformat() if date_from else None
    filter_to = date_to.isoformat() if date_to else None

    presets = _profile_presets(date.today())
    for preset in presets:
        preset["active"] = (
            preset["date_from"] == filter_from
            and preset["date_to"] == filter_to
        )
    custom_active = bool(
        filter_from and filter_to and not any(p["active"] for p in presets)
    )

    summary = get_summary_stats(user_id, filter_from, filter_to)
    stats = {
        "total_spent": _format_currency(summary["total_spent"]),
        "transaction_count": summary["transaction_count"],
        "top_category": summary["top_category"],
    }

    transactions = [
        {
            "id": txn["id"],
            "date": txn["date"],
            "description": txn["description"],
            "category": txn["category"],
            "amount": _format_currency(txn["amount"]),
        }
        for txn in get_recent_transactions(
            user_id, date_from=filter_from, date_to=filter_to
        )
    ]

    categories = [
        {
            "name": cat["name"],
            "amount": _format_currency(cat["amount"]),
            "pct": cat["pct"],
        }
        for cat in get_category_breakdown(user_id, filter_from, filter_to)
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        presets=presets,
        date_from=filter_from or "",
        date_to=filter_to or "",
        custom_active=custom_active,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    form = {
        "amount": "",
        "category": EXPENSE_CATEGORIES[0],
        "date": date.today().isoformat(),
        "description": "",
    }
    error = None

    if request.method == "POST":
        form = _expense_form_from_request()
        error, amount, expense_date = _validate_expense_form(form)

        if error is None:
            insert_expense(
                session["user_id"],
                amount,
                form["category"],
                expense_date.isoformat(),
                form["description"] or None,
            )
            flash("Expense added successfully.", "success")
            return redirect(url_for("profile"))

    return render_template(
        "add_expense.html",
        categories=EXPENSE_CATEGORIES,
        error=error,
        today=date.today().isoformat(),
        **form,
    )


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    form = {
        "amount": expense["amount"],
        "category": expense["category"],
        "date": expense["date"],
        "description": expense["description"] or "",
    }
    error = None

    if request.method == "POST":
        form = _expense_form_from_request()
        error, amount, expense_date = _validate_expense_form(form)

        if error is None:
            update_expense(
                id,
                session["user_id"],
                amount,
                form["category"],
                expense_date.isoformat(),
                form["description"] or None,
            )
            flash("Expense updated successfully.", "success")
            return redirect(url_for("profile"))

    return render_template(
        "edit_expense.html",
        expense=expense,
        categories=EXPENSE_CATEGORIES,
        error=error,
        **form,
    )


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if get_expense_by_id(id, session["user_id"]) is None:
        abort(404)

    delete_expense_row(id, session["user_id"])
    flash("Expense deleted successfully.", "success")
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
