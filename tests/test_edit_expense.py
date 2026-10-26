import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import close_db, get_db, init_db
from database.queries import get_expense_by_id, update_expense


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
            user_cursor = db.execute(
                "INSERT INTO users (name, email, password_hash, created_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    "Test User",
                    "test@example.com",
                    generate_password_hash("password123"),
                    "2026-01-15 10:00:00",
                ),
            )
            other_cursor = db.execute(
                "INSERT INTO users (name, email, password_hash, created_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    "Other User",
                    "other@example.com",
                    generate_password_hash("password123"),
                    "2026-01-16 10:00:00",
                ),
            )
            expense_cursor = db.execute(
                "INSERT INTO expenses "
                "(user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    user_cursor.lastrowid,
                    42.5,
                    "Food",
                    "2026-03-20",
                    "Lunch",
                ),
            )
            other_expense_cursor = db.execute(
                "INSERT INTO expenses "
                "(user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    other_cursor.lastrowid,
                    10.0,
                    "Bills",
                    "2026-03-21",
                    "Other user's bill",
                ),
            )
        close_db()

    flask_app.config["TEST_USER_ID"] = user_cursor.lastrowid
    flask_app.config["OTHER_USER_ID"] = other_cursor.lastrowid
    flask_app.config["EXPENSE_ID"] = expense_cursor.lastrowid
    flask_app.config["OTHER_EXPENSE_ID"] = other_expense_cursor.lastrowid

    yield flask_app

    with flask_app.app_context():
        close_db()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(client, app):
    with client.session_transaction() as session:
        session["user_id"] = app.config["TEST_USER_ID"]
    return client


def read_expense(app, expense_id):
    with app.app_context():
        db = get_db()
        try:
            row = db.execute(
                "SELECT * FROM expenses WHERE id = ?",
                (expense_id,),
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            close_db()


def test_get_expense_by_id_returns_owned_expense(app):
    expense_id = app.config["EXPENSE_ID"]
    user_id = app.config["TEST_USER_ID"]

    with app.app_context():
        expense = get_expense_by_id(expense_id, user_id)

    assert expense is not None
    assert expense["id"] == expense_id
    assert expense["user_id"] == user_id
    assert expense["amount"] == pytest.approx(42.5)
    assert expense["category"] == "Food"
    assert expense["date"] == "2026-03-20"
    assert expense["description"] == "Lunch"


def test_get_expense_by_id_rejects_other_user(app):
    expense_id = app.config["EXPENSE_ID"]
    other_user_id = app.config["OTHER_USER_ID"]

    with app.app_context():
        expense = get_expense_by_id(expense_id, other_user_id)

    assert expense is None


def test_get_expense_by_id_returns_none_for_missing_expense(app):
    with app.app_context():
        expense = get_expense_by_id(999999, app.config["TEST_USER_ID"])

    assert expense is None


def test_update_expense_updates_owned_row(app):
    expense_id = app.config["EXPENSE_ID"]
    user_id = app.config["TEST_USER_ID"]

    with app.app_context():
        changed = update_expense(
            expense_id,
            user_id,
            99.0,
            "Transport",
            "2026-04-01",
            "Taxi",
        )

    assert changed == 1
    expense = read_expense(app, expense_id)
    assert expense["amount"] == pytest.approx(99.0)
    assert expense["category"] == "Transport"
    assert expense["date"] == "2026-04-01"
    assert expense["description"] == "Taxi"


def test_update_expense_does_not_touch_other_users_row(app):
    expense_id = app.config["EXPENSE_ID"]
    other_user_id = app.config["OTHER_USER_ID"]

    with app.app_context():
        changed = update_expense(
            expense_id,
            other_user_id,
            99.0,
            "Transport",
            "2026-04-01",
            "Taxi",
        )

    assert changed == 0
    expense = read_expense(app, expense_id)
    assert expense["amount"] == pytest.approx(42.5)
    assert expense["category"] == "Food"
    assert expense["date"] == "2026-03-20"
    assert expense["description"] == "Lunch"


def test_get_edit_expense_requires_login(client, app):
    response = client.get(f"/expenses/{app.config['EXPENSE_ID']}/edit")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_get_edit_expense_renders_prefilled_form(auth_client, app):
    expense_id = app.config["EXPENSE_ID"]

    response = auth_client.get(f"/expenses/{expense_id}/edit")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'action="/expenses/{expense_id}/edit"' in html
    assert 'value="42.5"' in html
    assert 'value="2026-03-20"' in html
    assert 'value="Lunch"' in html
    assert 'value="Food" selected' in html
    assert 'value="Transport" selected' not in html
    assert "Save Changes" in html


def test_get_edit_expense_other_users_expense_returns_404(auth_client, app):
    response = auth_client.get(
        f"/expenses/{app.config['OTHER_EXPENSE_ID']}/edit"
    )

    assert response.status_code == 404


def test_get_edit_expense_missing_expense_returns_404(auth_client):
    response = auth_client.get("/expenses/999999/edit")

    assert response.status_code == 404


def test_post_edit_expense_requires_login(client, app):
    response = client.post(
        f"/expenses/{app.config['EXPENSE_ID']}/edit",
        data={
            "amount": "99.0",
            "category": "Transport",
            "date": "2026-04-01",
            "description": "Taxi",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_post_edit_expense_updates_and_redirects(auth_client, app):
    expense_id = app.config["EXPENSE_ID"]

    response = auth_client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "99.0",
            "category": "Transport",
            "date": "2026-04-01",
            "description": "Taxi",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    expense = read_expense(app, expense_id)
    assert expense["amount"] == pytest.approx(99.0)
    assert expense["category"] == "Transport"
    assert expense["date"] == "2026-04-01"
    assert expense["description"] == "Taxi"

    profile = auth_client.get("/profile")
    profile_html = profile.get_data(as_text=True)
    assert "Taxi" in profile_html
    assert f"/expenses/{expense_id}/edit" in profile_html


def test_post_edit_expense_other_users_expense_returns_404(auth_client, app):
    expense_id = app.config["EXPENSE_ID"]

    response = auth_client.post(
        f"/expenses/{app.config['OTHER_EXPENSE_ID']}/edit",
        data={
            "amount": "99.0",
            "category": "Transport",
            "date": "2026-04-01",
            "description": "Taxi",
        },
    )

    assert response.status_code == 404
    expense = read_expense(app, expense_id)
    assert expense["amount"] == pytest.approx(42.5)


def test_post_edit_expense_missing_amount_rerenders(auth_client, app):
    expense_id = app.config["EXPENSE_ID"]

    response = auth_client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "category": "Transport",
            "date": "2026-04-01",
            "description": "Taxi",
        },
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "auth-error" in html
    assert 'value="2026-04-01"' in html
    assert 'value="Taxi"' in html


def test_post_edit_expense_zero_amount_rerenders(auth_client, app):
    expense_id = app.config["EXPENSE_ID"]

    response = auth_client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "0",
            "category": "Transport",
            "date": "2026-04-01",
            "description": "Taxi",
        },
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "auth-error" in html
    assert 'value="0"' in html


def test_post_edit_expense_non_numeric_amount_rerenders(auth_client, app):
    expense_id = app.config["EXPENSE_ID"]

    response = auth_client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "abc",
            "category": "Transport",
            "date": "2026-04-01",
            "description": "Taxi",
        },
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "auth-error" in html


def test_post_edit_expense_invalid_category_rerenders(auth_client, app):
    expense_id = app.config["EXPENSE_ID"]

    response = auth_client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "99.0",
            "category": "Groceries",
            "date": "2026-04-01",
            "description": "Taxi",
        },
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "auth-error" in html


def test_post_edit_expense_invalid_date_rerenders(auth_client, app):
    expense_id = app.config["EXPENSE_ID"]

    response = auth_client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "99.0",
            "category": "Transport",
            "date": "not-a-date",
            "description": "Taxi",
        },
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "auth-error" in html


def test_post_edit_expense_without_description_saves_null(auth_client, app):
    expense_id = app.config["EXPENSE_ID"]

    response = auth_client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "99.0",
            "category": "Transport",
            "date": "2026-04-01",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    expense = read_expense(app, expense_id)
    assert expense["amount"] == pytest.approx(99.0)
    assert expense["description"] is None
