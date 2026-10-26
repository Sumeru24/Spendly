import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import close_db, get_db, init_db
from database.queries import insert_expense

CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
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
            cursor = db.execute(
                "INSERT INTO users (name, email, password_hash, created_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    "Test User",
                    "test@example.com",
                    generate_password_hash("password123"),
                    "2026-01-15 10:00:00",
                ),
            )
        close_db()

    flask_app.config["TEST_USER_ID"] = cursor.lastrowid

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


def read_expenses(app, user_id):
    with app.app_context():
        db = get_db()
        try:
            rows = db.execute(
                "SELECT * FROM expenses WHERE user_id = ? ORDER BY id",
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            close_db()


def test_insert_expense_persists_row(app):
    user_id = app.config["TEST_USER_ID"]

    with app.app_context():
        row_id = insert_expense(
            user_id, 50.0, "Food", "2026-03-20", "Lunch"
        )

    expenses = read_expenses(app, user_id)
    assert len(expenses) == 1
    assert expenses[0]["id"] == row_id
    assert expenses[0]["user_id"] == user_id
    assert expenses[0]["amount"] == pytest.approx(50.0)
    assert expenses[0]["category"] == "Food"
    assert expenses[0]["date"] == "2026-03-20"
    assert expenses[0]["description"] == "Lunch"


def test_insert_expense_stores_null_description(app):
    user_id = app.config["TEST_USER_ID"]

    with app.app_context():
        insert_expense(user_id, 25.0, "Transport", "2026-03-21", None)

    expenses = read_expenses(app, user_id)
    assert len(expenses) == 1
    assert expenses[0]["description"] is None


def test_get_add_expense_requires_login(client):
    response = client.get("/expenses/add")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_get_add_expense_renders_form(auth_client):
    response = auth_client.get("/expenses/add")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "<form" in html
    assert 'method="POST"' in html
    assert html.count("<option") == 7
    for category in CATEGORIES:
        assert f'value="{category}"' in html
    assert 'type="date"' in html
    assert 'name="amount"' in html
    assert 'name="description"' in html


def test_post_add_expense_requires_login(client):
    response = client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_post_add_expense_inserts_and_redirects(auth_client, app):
    response = auth_client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    expenses = read_expenses(app, app.config["TEST_USER_ID"])
    assert len(expenses) == 1
    assert expenses[0]["amount"] == pytest.approx(50.0)
    assert expenses[0]["category"] == "Food"
    assert expenses[0]["date"] == "2026-03-20"
    assert expenses[0]["description"] == "Lunch"

    profile = auth_client.get("/profile")
    assert "Lunch" in profile.get_data(as_text=True)


def test_post_add_expense_missing_amount_rerenders(auth_client):
    response = auth_client.post(
        "/expenses/add",
        data={
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "auth-error" in html
    assert 'value="2026-03-20"' in html
    assert 'value="Lunch"' in html


def test_post_add_expense_zero_amount_rerenders(auth_client):
    response = auth_client.post(
        "/expenses/add",
        data={
            "amount": "0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "auth-error" in html


def test_post_add_expense_non_numeric_amount_rerenders(auth_client):
    response = auth_client.post(
        "/expenses/add",
        data={
            "amount": "abc",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "auth-error" in html


def test_post_add_expense_invalid_category_rerenders(auth_client):
    response = auth_client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Groceries",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "auth-error" in html


def test_post_add_expense_invalid_date_rerenders(auth_client):
    response = auth_client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "not-a-date",
            "description": "Lunch",
        },
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "auth-error" in html


def test_post_add_expense_without_description_saves_null(auth_client, app):
    response = auth_client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    expenses = read_expenses(app, app.config["TEST_USER_ID"])
    assert len(expenses) == 1
    assert expenses[0]["description"] is None
