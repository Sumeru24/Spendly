# AGENTS.md

Spendly is a small Flask teaching project. Features are intentionally added in numbered "steps"; routes/templates/db helpers are scaffolding for those steps, not bugs to remove.

## Commands

Use the checked-in virtualenv (Python 3.13); do not recreate it unless asked.

- Run app: `venv\Scripts\python.exe app.py` (debug, `http://127.0.0.1:5001`)
- Install deps: `venv\Scripts\python.exe -m pip install -r requirements.txt`
- Tests: `venv\Scripts\python.exe -m pytest` (pytest is installed but there are currently no project tests; don't assume a test file/config exists)

## Structure

- `app.py` is the only entrypoint and routes are plain functions; templates use those function names with `url_for(...)` (see `templates/base.html`).
- `templates/` pages extend `base.html`; shared nav/footer and CSS/JS includes live there.
- `static/css/style.css` holds all styling; `static/js/main.js` is vanilla JS, currently only the landing-page video modal.
- `database/db.py` is a stub. Intended API: `get_db()`, `init_db()`, `seed_db()` using SQLite. DB file is `expense_tracker.db` (gitignored); there is no ORM or migration system.
- `file.md` is the project/roadmap doc (tech stack, route status, intended DB functions).

## Gotchas

- `login.html` and `register.html` submit POST to `/login` and `/register`, but `app.py` currently only defines GET routes for them. Supporting these forms requires adding POST handlers.
- `/logout`, `/profile`, and `/expenses/*` return "coming in Step N" placeholders. Implement the feature rather than treating the text as final.
- `venv/`, `__pycache__/`, and `expense_tracker.db` are gitignored; never edit or commit vendored `venv` files.
- Recent commit messages use short lowercase prefixes, e.g. `landing: add privacy policy page and route`.
