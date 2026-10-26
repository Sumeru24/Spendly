import re
from datetime import date

import pytest
from werkzeug.security import generate_password_hash

from app import _months_before, _profile_presets, app as flask_app
from database.db import close_db, get_db, init_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

SEED_EXPENSES = [
    ("2026-04-20", 100.00, "Bills", "Electricity bill"),
    ("2026-04-19", 80.00, "Bills", "Internet bill"),
    ("2026-04-18", 65.50, "Groceries", "Weekly supermarket run"),
    ("2026-04-17", 30.00, "Dining", "Dinner with friends"),
    ("2026-04-16", 25.00, "Transport", "Monthly transit pass"),
    ("2026-04-15", 20.00, "Health", "Pharmacy"),
    ("2026-04-14", 15.00, "Entertainment", "Movie tickets"),
    ("2026-04-13", 10.74, "Shopping", "Household items"),
]

CATEGORY_NAMES = [
    "Bills",
    "Groceries",
    "Dining",
    "Transport",
    "Health",
    "Entertainment",
    "Shopping",
]


@pytest.fixture()
def app(tmp_path):
    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        DATABASE=tmp_path / "test.db",
    )

    with flask_app.app_context():
        init_db()
        db = get_db()
        with db:
            demo_cursor = db.execute(
                "INSERT INTO users (name, email, password_hash, created_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    "Demo User",
                    "demo@spendly.com",
                    generate_password_hash("demo123"),
                    "2026-01-15 10:00:00",
                ),
            )
            empty_cursor = db.execute(
                "INSERT INTO users (name, email, password_hash, created_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    "Empty User",
                    "empty@spendly.com",
                    generate_password_hash("emptypass"),
                    "2026-02-20 10:00:00",
                ),
            )
            db.executemany(
                "INSERT INTO expenses "
                "(user_id, amount, category, description, date) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (demo_cursor.lastrowid, amount, category, description, spent_on)
                    for spent_on, amount, category, description in SEED_EXPENSES
                ],
            )
        close_db()

    flask_app.config["TEST_DEMO_USER_ID"] = demo_cursor.lastrowid
    flask_app.config["TEST_EMPTY_USER_ID"] = empty_cursor.lastrowid

    yield flask_app

    with flask_app.app_context():
        close_db()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user_ids(app):
    return {
        "demo": app.config["TEST_DEMO_USER_ID"],
        "empty": app.config["TEST_EMPTY_USER_ID"],
    }


def test_get_user_by_id_returns_profile_fields(app, user_ids):
    with app.app_context():
        user = get_user_by_id(user_ids["demo"])

    assert user == {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "member_since": "January 2026",
    }


def test_get_user_by_id_returns_none_for_missing_user(app):
    with app.app_context():
        assert get_user_by_id(9999) is None


def test_get_summary_stats_with_expenses(app, user_ids):
    with app.app_context():
        stats = get_summary_stats(user_ids["demo"])

    assert stats["total_spent"] == pytest.approx(346.24)
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_without_expenses(app, user_ids):
    with app.app_context():
        stats = get_summary_stats(user_ids["empty"])

    assert stats == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


def test_get_recent_transactions_returns_newest_first(app, user_ids):
    with app.app_context():
        transactions = get_recent_transactions(user_ids["demo"])

    assert len(transactions) == 8
    assert [txn["date"] for txn in transactions] == [
        expense[0] for expense in SEED_EXPENSES
    ]
    assert all(
        set(txn) == {"id", "date", "description", "category", "amount"}
        for txn in transactions
    )
    assert transactions[0]["description"] == "Electricity bill"


def test_get_recent_transactions_respects_limit(app, user_ids):
    with app.app_context():
        transactions = get_recent_transactions(user_ids["demo"], limit=3)

    assert len(transactions) == 3


def test_get_recent_transactions_without_expenses(app, user_ids):
    with app.app_context():
        assert get_recent_transactions(user_ids["empty"]) == []


def test_get_category_breakdown_orders_and_sums_to_100(app, user_ids):
    with app.app_context():
        breakdown = get_category_breakdown(user_ids["demo"])

    assert [row["name"] for row in breakdown] == CATEGORY_NAMES
    amounts = [row["amount"] for row in breakdown]
    assert amounts == sorted(amounts, reverse=True)
    assert all(isinstance(row["pct"], int) for row in breakdown)
    assert sum(row["pct"] for row in breakdown) == 100
    assert breakdown[0]["name"] == "Bills"
    assert breakdown[0]["amount"] == pytest.approx(180.00)


def test_get_category_breakdown_without_expenses(app, user_ids):
    with app.app_context():
        assert get_category_breakdown(user_ids["empty"]) == []


def test_profile_requires_login(client):
    response = client.get("/profile")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_shows_live_seed_user_data(client, user_ids):
    with client.session_transaction() as session:
        session["user_id"] = user_ids["demo"]

    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Demo User" in html
    assert "demo@spendly.com" in html
    assert '<span class="stat-value">₹346.24</span>' in html
    assert '<span class="stat-value">8</span>' in html
    assert '<span class="stat-value">Bills</span>' in html
    assert "₹" in html
    assert "$" not in html
    assert "£" not in html

    assert html.count("<time ") == 8
    positions = [html.index(expense[3]) for expense in SEED_EXPENSES]
    assert positions == sorted(positions)

    for category in CATEGORY_NAMES:
        assert category in html

    percentages = [
        int(value) for value in re.findall(r'aria-valuenow="(\d+)"', html)
    ]
    assert len(percentages) == 7
    assert sum(percentages) == 100


def test_profile_shows_empty_state_for_new_user(client, user_ids):
    with client.session_transaction() as session:
        session["user_id"] = user_ids["empty"]

    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<span class="stat-value">₹0.00</span>' in html
    assert '<span class="stat-value">0</span>' in html
    assert '<span class="stat-value">—</span>' in html
    assert "No transactions yet." in html
    assert "No spending data yet." in html


def test_profile_redirects_when_session_user_is_missing(client):
    with client.session_transaction() as session:
        session["user_id"] = 9999

    response = client.get("/profile")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_queries_apply_date_range(app, user_ids):
    with app.app_context():
        stats = get_summary_stats(
            user_ids["demo"], "2026-04-18", "2026-04-20"
        )
        transactions = get_recent_transactions(
            user_ids["demo"], date_from="2026-04-18", date_to="2026-04-20"
        )
        breakdown = get_category_breakdown(
            user_ids["demo"], "2026-04-18", "2026-04-20"
        )

    assert stats["total_spent"] == pytest.approx(245.50)
    assert stats["transaction_count"] == 3
    assert stats["top_category"] == "Bills"
    assert [txn["date"] for txn in transactions] == [
        "2026-04-20",
        "2026-04-19",
        "2026-04-18",
    ]
    assert [row["name"] for row in breakdown] == ["Bills", "Groceries"]
    assert sum(row["pct"] for row in breakdown) == 100


def test_profile_custom_date_range(client, user_ids):
    with client.session_transaction() as session:
        session["user_id"] = user_ids["demo"]

    response = client.get("/profile?date_from=2026-04-18&date_to=2026-04-20")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<span class="stat-value">₹245.50</span>' in html
    assert '<span class="stat-value">3</span>' in html
    assert html.count("<time ") == 3
    assert "Bills" in html
    assert "Groceries" in html
    assert "Dining" not in html
    assert "filter-custom is-active" in html


def test_profile_all_time_has_no_active_filter(client, user_ids):
    with client.session_transaction() as session:
        session["user_id"] = user_ids["demo"]

    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert '<span class="stat-value">₹346.24</span>' in html
    assert html.count("<time ") == 8
    assert html.count("filter-preset is-active") == 1
    assert "All Time" in html


def test_profile_inverted_range_flashes_and_falls_back(client, user_ids):
    with client.session_transaction() as session:
        session["user_id"] = user_ids["demo"]

    response = client.get("/profile?date_from=2026-04-20&date_to=2026-04-01")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Start date must be before end date." in html
    assert '<span class="stat-value">₹346.24</span>' in html


def test_profile_malformed_date_falls_back(client, user_ids):
    with client.session_transaction() as session:
        session["user_id"] = user_ids["demo"]

    response = client.get("/profile?date_from=not-a-date&date_to=2026-04-20")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<span class="stat-value">₹346.24</span>' in html


def test_profile_empty_date_range_shows_empty_state(client, user_ids):
    with client.session_transaction() as session:
        session["user_id"] = user_ids["demo"]

    response = client.get("/profile?date_from=2025-01-01&date_to=2025-01-31")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<span class="stat-value">₹0.00</span>' in html
    assert "No transactions yet." in html
    assert "No spending data yet." in html


def test_preset_dates_are_calculated_correctly():
    today = date(2026, 5, 31)
    presets = {preset["label"]: preset for preset in _profile_presets(today)}

    assert presets["This Month"]["date_from"] == "2026-05-01"
    assert presets["This Month"]["date_to"] == "2026-05-31"
    assert presets["Last 3 Months"]["date_from"] == "2026-02-28"
    assert presets["Last 6 Months"]["date_from"] == "2025-11-30"
    assert presets["All Time"]["date_from"] is None
    assert presets["All Time"]["date_to"] is None
    assert _months_before(date(2026, 1, 31), 1) == date(2025, 12, 31)
