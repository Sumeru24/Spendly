# Step 1 — Database Setup Implementation Plan

## Source Note

The requested spec path `.claude/specs/01-database-setup.md` does not exist. The
available file `.claude/specs/database_setup.md` is empty (0 bytes). This plan is
derived from:

- The intended API documented in `database/db.py`
- `AGENTS.md`
- `file.md`
- The existing `login.html` / `register.html` forms

If a fuller spec exists elsewhere, reconcile the schema below with it before
implementing.

## Goal

Implement the SQLite persistence layer for Spendly:

- `get_db()` — per-request connection with `sqlite3.Row` rows and foreign keys on
- `init_db()` — idempotent creation of the `users` and `expenses` tables
- `seed_db()` — idempotent development seed data

No ORM, migration system, or additional dependencies.

## Assumptions

- Two tables are sufficient for all later steps: `users` and `expenses`.
- Passwords are stored as hashes using `werkzeug.security` (already a Flask
  dependency); never plaintext.
- Money is stored as `REAL` for this teaching project, with a positive-value
  `CHECK`.
- Dates are stored as ISO `YYYY-MM-DD` text.
- The database file remains `expense_tracker.db` at the repo root and stays
  gitignored.
- The DB path is overridable through `app.config["DATABASE"]` so future tests can
  use a temporary file.
- `foreign_keys` must be enabled per connection; SQLite does not persist it.

## Schema

### `users`

```sql
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### `expenses`

```sql
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
```

`ON DELETE CASCADE` requires `PRAGMA foreign_keys = ON` in `get_db()`.

## File Changes

### 1. `database/db.py`

Add:

- Module-level default path:
  `Path(__file__).resolve().parent.parent / "expense_tracker.db"`.
- `get_db()`:
  - Return the existing connection from `flask.g` if present.
  - Otherwise `sqlite3.connect(...)` using
    `current_app.config.get("DATABASE", DEFAULT_DATABASE)`.
  - Set `conn.row_factory = sqlite3.Row`.
  - Execute `PRAGMA foreign_keys = ON`.
  - Store on `g.db` and return it.
- `close_db(_exception=None)`:
  - Close and clear `g.db` when it exists.
- `init_db()`:
  - Use `get_db()`.
  - `executescript(...)` with both `CREATE TABLE IF NOT EXISTS` statements and
    the index.
  - Commit. Safe to run repeatedly.
- `seed_db()`:
  - Call `init_db()` first so seeding works on a fresh checkout.
  - Return early if `users` already has rows (idempotent).
  - Insert one demo user with `generate_password_hash`.
  - Insert several sample expenses for that user across common categories and
    dates relative to today.
  - Commit and print a short confirmation (e.g. demo credentials).

Remove the stub comments and keep imports limited to `sqlite3`, `datetime.date`,
`pathlib.Path`, `flask.current_app`, `flask.g`, and
`werkzeug.security.generate_password_hash`.

### 2. `app.py`

Minimal wiring; do not refactor into an app factory in this step.

- Import `close_db`, `init_db`, and `seed_db` from `database.db`.
- Set `app.config.setdefault("DATABASE", ...)` only if a different default is
  needed; otherwise rely on `db.py`'s path.
- Register `app.teardown_appcontext(close_db)`.
- Add two Flask CLI commands:
  - `init-db` → calls `init_db()`
  - `seed-db` → calls `seed_db()`
- Do **not** initialize the DB automatically on every startup. Auto-init makes
  tests and debugging surprising; CLI commands are explicit.

Suggested commands use plain `@app.cli.command(...)` functions; `click` is
already available via Flask, but no decorators/arguments are required.

### 3. Templates / CSS / JS

No changes.

## Implementation Order

1. Write `get_db()` and `close_db()` in `database/db.py`.
2. Verify the connection settings with a quick script.
3. Add `init_db()` and the schema DDL.
4. Add `seed_db()` with the demo user and expenses.
5. Wire teardown and CLI commands in `app.py`.
6. Run the verification checklist below.

## Verification

Run from the repo root:

```powershell
# 1. Create tables
venv\Scripts\python.exe -m flask --app app init-db

# 2. Seed demo data
venv\Scripts\python.exe -m flask --app app seed-db
```

Then inspect the database:

```powershell
venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('expense_tracker.db'); print(c.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall()); print(c.execute('SELECT COUNT(*) FROM users').fetchone()); print(c.execute('SELECT COUNT(*) FROM expenses').fetchone())"
```

Checks:

- Running `init-db` twice succeeds (idempotent).
- Running `seed-db` twice does not duplicate users/expenses.
- `users.email` uniqueness rejects a duplicate email.
- Inserting an expense with a nonexistent `user_id` fails with a foreign-key
  error.
- Deleting a user cascades to that user's expenses.
- `get_db()` returns rows that support `row["column"]` access.
- Existing `venv\Scripts\python.exe -m pytest` still runs (no project tests
  expected).

## Out of Scope

- Auth POST handlers for `/register` and `/login` (later steps)
- Expense CRUD routes
- Session/login-required behavior
- Migrations, ORMs, or test fixtures
