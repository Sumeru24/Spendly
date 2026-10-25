# Spec: Registration

## Overview

Registration turns the existing static sign-up page into a working account-creation flow. A public visitor submits their name, email, and password; the app validates the input, rejects duplicate emails, hashes the password with Werkzeug, and inserts a row into the `users` table created in Step 1. On success the visitor is sent to the sign-in page with a confirmation message. This is the first step that writes user data and unblocks Step 3 (login/logout) and all later logged-in features.

## Depends on

- Step 1 — Database Setup (`users` table, `get_db()`, `init_db()`)

## Routes

- `GET /register` — render the registration form — public (already exists; keep as-is)
- `POST /register` — validate and create a user, then redirect to `/login` on success; re-render the form with an error and preserved values on failure — public

No other routes change in this step.

## Database changes

No database changes. The existing `users` table already provides everything needed:

```sql
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

`email` uniqueness is case-insensitive thanks to `COLLATE NOCASE`, so the application must still treat `User@x.com` and `user@x.com` as duplicates. The `created_at` column is populated by its default; do not pass it explicitly.

## Templates

- **Create:** none
- **Modify:**
  - `templates/register.html` — keep the existing markup and `extends "base.html"`; rely on the existing `{% if error %}` block for failures; add a confirm-password field; re-populate `name` and `email` from the values passed by the view; ensure all inputs keep `required`.
  - `templates/login.html` — render flashed success/error messages (e.g. `get_flashed_messages(with_categories=true)`) above the form to confirm account creation.
  - `static/css/style.css` — add an `.auth-success` rule next to `.auth-error` using existing CSS variables (`--accent`, `--accent-light`, `--radius-sm`) rather than hardcoded hex values.

## Files to change

- `app.py` — add the `POST /register` handler and required imports
- `templates/register.html` — error display and value preservation
- `templates/login.html` — registration success banner
- `static/css/style.css` — `.auth-success` styling

## Files to create

- None

## New dependencies

No new dependencies. Use only the standard library plus packages already present: Flask, Werkzeug (`generate_password_hash`), and the existing `database.db` helpers.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `get_db()` from `database/db.py`; do not open ad-hoc SQLite connections inside the route
- Never store or log plaintext passwords; do not echo the password back into the form
- Validate on the server even though the form has HTML5 validation:
  - `name`, `email`, `password`, and `confirm_password` are required after `.strip()`
  - `name` length 2–80 characters
  - `email` must match a basic `something@domain.tld` pattern; normalise to lowercase and strip whitespace before storing
  - `password` must be at least 8 characters
  - `password` and `confirm_password` must match
- Duplicate handling: check with a parameterised `SELECT 1 FROM users WHERE email = ?` before inserting, and also catch `sqlite3.IntegrityError` around the insert as the race-condition fallback; both paths display "Email already registered." and insert nothing
- On validation failure, re-render `register.html` with the first error message and the submitted `name`/`email` values (never the password)
- On success, flash a confirmation and use `redirect(url_for("login"))`; do not auto-login in this step. Configure `app.config["SECRET_KEY"]` (environment override with a development fallback) so flashing works.
- Keep the handler as a plain function, consistent with the existing routes; do not introduce an app factory, blueprints, or CSRF library in this step
- Commit nothing to the database when validation fails

## Definition of done

- [ ] `GET /register` renders the registration form without errors
- [ ] Submitting with all valid fields creates a new user in `users` and redirects to `/login`
- [ ] The sign-in page shows a success message after that redirect
- [ ] Submitting with mismatched passwords re-renders the form with an error and inserts no row
- [ ] Submitting an already-registered email (including a differently-cased variant) re-renders the form with "Email already registered." and inserts no second row
- [ ] Submitting with any empty field re-renders the form with a validation error and inserts no row
- [ ] The password is stored as a hash, never plaintext, verifiable by inspecting `expense_tracker.db`
- [ ] Repeated valid submissions with the same email never create duplicate users
- [ ] After a validation error, the submitted name and email remain in the form and the password fields are empty
- [ ] The raw password never appears in the database, HTML response, or console output
- [ ] The app still starts with `venv\Scripts\python.exe app.py` and the existing landing/login pages are unaffected
