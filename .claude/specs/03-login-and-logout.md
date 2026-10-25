# Spec: Login and Logout

## Overview

Login and logout give registered users a session-backed way to enter and leave Spendly. A returning visitor submits their email and password; the app looks up the user, verifies the stored Werkzeug hash, and records the user id in Flask's signed session cookie before redirecting to the landing page. Logout clears that session. The shared navigation reflects the auth state so the rest of the app can build on "who is signed in" in later steps.

## Depends on

- Step 1 — Database Setup (`users` table, `get_db()`)
- Step 2 — Registration (existing users with hashed passwords)

## Routes

- `GET /login` — render the sign-in form; already exists, keep it — public
- `POST /login` — validate credentials, set `session["user_id"]`, redirect to landing on success; re-render the form with an error on failure — public
- `GET /logout` — clear the session and redirect to landing — logged-in (safe to call when logged out)

No other routes change in this step. Do not protect `/profile` or `/expenses/*` yet; that belongs to later steps.

## Database changes

No database changes. Login reads the existing `users` table:

```sql
SELECT id, name, password_hash FROM users WHERE email = ?
```

The email column is already `UNIQUE COLLATE NOCASE`, and passwords were stored by Step 2 using `generate_password_hash`, so verification uses `werkzeug.security.check_password_hash`.

## Templates

- **Create:** none
- **Modify:**
  - `templates/login.html` — keep the existing form and `extends "base.html"`; re-populate the email input from the submitted value on error; leave the password input empty. Remove the page-local flash block if flash messages move to `base.html`.
  - `templates/base.html` — render flashed messages once in the main content area; show `Profile` and a `Sign out` link when `session["user_id"]` is set, otherwise keep `Sign in` and `Get started`.
  - `static/css/style.css` — add a small `.flash-container` rule using existing CSS variables (`--auth-width`, `--radius-sm`) so flashed messages align with the auth layout.

## Files to change

- `app.py` — import `session` and `check_password_hash`, add `POST /login` and real `/logout`
- `templates/base.html` — auth-aware nav and shared flash rendering
- `templates/login.html` — email preservation and removal of duplicate flash rendering
- `static/css/style.css` — `.flash-container` styling

## Files to create

- None

## New dependencies

No new dependencies. Use Flask's built-in `session` and `werkzeug.security.check_password_hash`, both already available.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `get_db()` from `database/db.py`; do not open ad-hoc SQLite connections inside routes
- Never store or log plaintext passwords; never echo the submitted password back into the form
- Look up the user by the normalised (trimmed, lowercased) email, then verify with `check_password_hash`
- Use one generic failure message ("Invalid email or password.") for unknown email, wrong password, and empty fields, so the form does not reveal which emails exist
- On successful login, call `session.clear()` before setting `session["user_id"]` to the user's id
- On logout, call `session.clear()`, flash a short confirmation, and redirect to `url_for("landing")`
- Keep working without JavaScript; the forms are plain HTML POSTs
- Do not auto-login after registration in this step; registration already redirects to `/login`
- Ensure flashed messages render exactly once per page (move them to `base.html` rather than duplicating)

## Definition of done

- [ ] `GET /login` renders the sign-in page without errors
- [ ] Signing in with a registered email and correct password sets a session cookie and redirects to `/`
- [ ] After signing in, the landing-page nav shows `Profile` and `Sign out` instead of `Sign in` and `Get started`
- [ ] Signing in with an unregistered email shows "Invalid email or password." and does not set a session
- [ ] Signing in with a wrong password shows the same generic error and does not set a session
- [ ] Submitting with an empty email or password shows the same generic error
- [ ] After a failed sign-in, the submitted email remains in the form and the password field is empty
- [ ] Visiting `/logout` clears the session, redirects to `/`, and the nav returns to `Sign in` and `Get started`
- [ ] The signed-in state survives a page reload (session cookie is honoured)
- [ ] Registration still works and its success message appears exactly once on the login page
- [ ] The app still starts with `venv\Scripts\python.exe app.py` and existing public pages are unaffected
