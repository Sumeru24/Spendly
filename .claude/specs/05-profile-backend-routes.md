# Spec: Profile Backend Routes

## Overview

Step 5 replaces the hardcoded demo context in the `/profile` view with live
queries against the `users` and `expenses` tables. The profile page already has
its final layout (user card, summary stats, recent transactions, category
breakdown); this step makes it show the signed-in user's real account and
spending data instead of the same "Demo User" placeholders for everyone. This
completes the read side of expense tracking and unblocks the add/edit/delete
flows in later steps.

## Depends on

- Step 1 — Database Setup (`users` and `expenses` tables, `get_db()`)
- Step 2 — Registration (real users with hashed passwords)
- Step 3 — Login and Logout (`session["user_id"]` identifies the current user)
- Step 4 — Profile Page UI (`templates/profile.html` and its context shape)

## Routes

No new routes.

- `GET /profile` — render the signed-in user's account and spending data from
  SQLite; redirect to `/login` when there is no session — logged-in

The route path, method, and access level are unchanged from Step 4. Only the
data source changes.

## Database changes

No database changes. The existing schema is sufficient:

- `users (id, name, email, password_hash, created_at)`
- `expenses (id, user_id, amount, category, description, date, created_at)`
- `idx_expenses_user_date` already supports per-user date queries

All reads use the existing `get_db()` helper and parameterised SQL. No new
tables, columns, indexes, migrations, or seed changes.

## Templates

- **Create:** None
- **Modify:**
  - `templates/profile.html` — no structural change is required. The existing
    template already renders `user`, `stats`, `transactions`, and `categories`
    and already has `{% else %}` empty states. Keep it unchanged as long as the
    context shape below is preserved.
  - `templates/base.html` — no change.

Context shape to preserve exactly (same keys as Step 4):

```python
user = {"name": str, "email": str, "initials": str, "member_since": str}
stats = {"total_spent": str, "transaction_count": int, "top_category": str}
transactions = [
    {"date": str, "description": str, "category": str, "amount": str},
]
categories = [{"name": str, "amount": str, "pct": int}]
```

## Files to change

- `app.py` — replace the hardcoded data inside `profile()` with database
  queries scoped to `session["user_id"]`; add the `datetime` import needed for
  formatting `created_at`.

## Files to create

None.

## New dependencies

No new dependencies. Use only Flask, the existing `database.db.get_db()` helper,
and the Python standard library (`datetime`).

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `get_db()` from `database/db.py`; do not open ad-hoc SQLite connections
- Keep `profile()` a plain route function; do not introduce an app factory,
  blueprints, or service/repository layers
- Keep the `session.get("user_id")` guard and `redirect(url_for("login"))`
- Every expense query must filter by the session's `user_id`; never accept a
  user id from the URL, form, or query string
- If the session references a user that no longer exists, clear the session,
  flash a short message, and redirect to `/login`
- Fetch the user with `SELECT id, name, email, created_at FROM users WHERE id = ?`
  and never expose `password_hash`
- Compute statistics with SQL, not by loading all rows into Python:
  - total spent: `COALESCE(SUM(amount), 0)` for the user
  - transaction count: `COUNT(*)` for the user
  - top category: highest `SUM(amount)` grouped by `category`; use `—` when the
    user has no expenses
- Recent transactions: select `date, description, category, amount` for the
  user, ordered `date DESC, id DESC`, limited to 10. Use `COALESCE(description,
  '')` so NULL descriptions never render as `None`
- Category breakdown: `SELECT category, SUM(amount) AS total ... GROUP BY
  category ORDER BY total DESC, category ASC`. Compute each `pct` in Python from
  the user's overall total; handle a zero total without dividing by zero
- Format money in Python as `₹` plus thousands separators and exactly two
  decimals (e.g. `₹1,519.75`, `₹0.00`); the template must keep receiving strings
- Format `member_since` from `users.created_at` as `Month YYYY` (e.g.
  `October 2026`); tolerate the SQLite `YYYY-MM-DD HH:MM:SS` format
- Derive `initials` from the user's name (first letter of the first two name
  parts, uppercase); never hardcode them
- Preserve the existing empty states: a new user with no expenses must get
  `₹0.00`, `0`, `—`, an empty transactions list, and an empty category list
  rather than an error
- Do not change any other route, template, stylesheet, JavaScript file, or
  dependency

## Definition of done

- [ ] Visiting `/profile` without a session redirects to `/login` (302).
- [ ] Signing in as the seeded demo user (`demo@spendly.test` / `password123`)
      shows `Demo User`, `demo@spendly.test`, and a member-since month/year
      taken from the database.
- [ ] The demo user's total spent shows `₹1,519.75` and transaction count shows
      `6`.
- [ ] The demo user's top category shows `Rent`, and the category breakdown
      lists Rent, Utilities, Groceries, Dining, Health, and Transport with
      amounts matching their sums.
- [ ] Recent transactions show the user's six expenses newest-first, each with
      date, description, category badge, and a `₹x,xxx.xx` amount.
- [ ] Registering a brand-new account and opening `/profile` shows `₹0.00`,
      `0`, `—`, "No transactions yet.", and "No spending data yet." without an
      error.
- [ ] After signing in as a second user, the first user's expenses are not
      visible anywhere on the page.
- [ ] Adding an expense row for user A directly in SQLite does not change user
      B's profile totals when signed in as B.
- [ ] Deleting the signed-in user's row (or otherwise pointing the session at a
      nonexistent user id) redirects to `/login` with a flash message instead of
      raising an error.
- [ ] No hardcoded demo name, email, totals, transactions, or categories remain
      inside `profile()` in `app.py`.
- [ ] `templates/profile.html`, `static/css/style.css`, and `database/db.py`
      are unchanged by this step.
- [ ] The app still starts with `venv\Scripts\python.exe app.py`, and the
      landing, register, login, logout, terms, and privacy pages are unaffected.
- [ ] `venv\Scripts\python.exe -m pytest` still runs without errors (no project
      tests are expected).
