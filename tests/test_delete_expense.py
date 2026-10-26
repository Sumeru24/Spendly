import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import close_db, get_db, init_db
from database.queries import delete_expense


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


def test_delete_expense_removes_owned_row(app):
    expense_id = app.config["EXPENSE_ID"]
    user_id = app.config["TEST_USER_ID"]

    with app.app_context():
        deleted = delete_expense(expense_id, user_id)

    assert deleted == 1
    assert read_expense(app, expense_id) is None


def test_delete_expense_does_not_remove_other_users_row(app):
    expense_id = app.config["EXPENSE_ID"]
    other_user_id = app.config["OTHER_USER_ID"]

    with app.app_context():
        deleted = delete_expense(expense_id, other_user_id)

    assert deleted == 0
    expense = read_expense(app, expense_id)
    assert expense is not None
    assert expense["description"] == "Lunch"


def test_delete_expense_missing_row_does_not_error(app):
    with app.app_context():
        deleted = delete_expense(999999, app.config["TEST_USER_ID"])

    assert deleted == 0


def test_post_delete_expense_requires_login(client, app):
    response = client.post(f"/expenses/{app.config['EXPENSE_ID']}/delete")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_post_delete_expense_removes_row_and_redirects(auth_client, app):
    expense_id = app.config["EXPENSE_ID"]

    response = auth_client.post(f"/expenses/{expense_id}/delete")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
    assert read_expense(app, expense_id) is None

    profile = auth_client.get("/profile")
    assert "Lunch" not in profile.get_data(as_text=True)


def test_post_delete_expense_other_users_row_returns_404(auth_client, app):
    expense_id = app.config["EXPENSE_ID"]

    response = auth_client.post(
        f"/expenses/{app.config['OTHER_EXPENSE_ID']}/delete"
    )

    assert response.status_code == 404
    assert read_expense(app, expense_id) is not None


def test_post_delete_expense_missing_row_returns_404(auth_client):
    response = auth_client.post("/expenses/999999/delete")

    assert response.status_code == 404


def test_get_delete_expense_returns_405(client, app):
    response = client.get(f"/expenses/{app.config['EXPENSE_ID']}/delete")

    assert response.status_code == 405


def test_profile_shows_edit_and_delete_actions(auth_client, app):
    expense_id = app.config["EXPENSE_ID"]

    response = auth_client.get("/profile")
    html = response.get_data(as_text=True)

    assert f"/expenses/{expense_id}/edit" in html
    assert f'action="/expenses/{expense_id}/delete"' in html
    assert ">Delete</button>" in html
    assert "return confirm('Delete this expense?')" in html
