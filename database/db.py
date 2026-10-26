import sqlite3
from datetime import date, timedelta
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


DEFAULT_DATABASE = Path(__file__).resolve().parent.parent / "expense_tracker.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    amount      REAL    NOT NULL CHECK (amount > 0),
    category    TEXT    NOT NULL,
    description TEXT,
    date        TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date
    ON expenses (user_id, date);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config.get("DATABASE", DEFAULT_DATABASE))
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()


def seed_db():
    init_db()
    db = get_db()

    if db.execute(
        "SELECT 1 FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone() is not None:
        print("Demo user already exists; skipping seed.")
        return

    today = date.today()
    expenses = [
        (100.00, "Bills", "Electricity bill", today - timedelta(days=1)),
        (80.00, "Bills", "Internet bill", today - timedelta(days=2)),
        (65.50, "Groceries", "Weekly supermarket run", today - timedelta(days=3)),
        (30.00, "Dining", "Dinner with friends", today - timedelta(days=4)),
        (25.00, "Transport", "Monthly transit pass", today - timedelta(days=5)),
        (20.00, "Health", "Pharmacy", today - timedelta(days=6)),
        (15.00, "Entertainment", "Movie tickets", today - timedelta(days=7)),
        (10.74, "Shopping", "Household items", today - timedelta(days=8)),
    ]

    with db:
        cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (
                "Demo User",
                "demo@spendly.com",
                generate_password_hash("demo123"),
            ),
        )
        user_id = cursor.lastrowid
        db.executemany(
            """
            INSERT INTO expenses (user_id, amount, category, description, date)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (user_id, amount, category, description, spent_on.isoformat())
                for amount, category, description, spent_on in expenses
            ],
        )

    print("Seeded demo user: demo@spendly.com / demo123")
