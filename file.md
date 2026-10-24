# Spendly - Expense Tracker

## Project Overview

Spendly is a Flask-based personal finance tracker web application. It allows users to log expenses, understand spending patterns, and take control of their finances with a clean, modern interface.

## Tech Stack

- **Backend:** Python + Flask 3.1.3 (Werkzeug 3.1.6)
- **Templating:** Jinja2 (HTML templates)
- **Frontend:** HTML5, CSS3, vanilla JavaScript
- **Database:** SQLite (to be implemented in `database/db.py`)
- **Testing:** pytest 8.3.5, pytest-flask 1.3.0

## Project Structure

```
expense-tracker/
├── app.py              # Flask app, routes (landing/register/login + placeholders)
├── database/
│   ├── __init__.py
│   └── db.py           # DB helpers stub (to implement)
├── static/
│   ├── css/style.css   # Full styling
│   └── js/main.js
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── login.html
│   └── register.html
├── requirements.txt
├── .gitignore
└── venv/               # Local env (not project code)
```

## Features

- **Landing page** with hero section showcasing spending overview
- **User authentication** routes for login and registration
- **Expense management** (routes for add/edit/delete expenses - to be implemented)
- **User profile** (to be implemented)
- **Clean, modern UI** with custom CSS variables and responsive design

## Getting Started

### Prerequisites
- Python 3.x
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Sumeru24/Spendly.git
cd Spendly
```

2. Create and activate virtual environment:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

The app will run on `http://127.0.0.1:5001` in debug mode.

## Routes

| Route | Method | Description | Status |
|---|---|---|---|
| `/` | GET | Landing page | Implemented |
| `/register` | GET | User registration | Template exists |
| `/login` | GET | User login | Template exists |
| `/logout` | GET | User logout | Placeholder |
| `/profile` | GET | User profile | Placeholder |
| `/expenses/add` | GET | Add expense | Placeholder |
| `/expenses/<id>/edit` | GET | Edit expense | Placeholder |
| `/expenses/<id>/delete` | GET | Delete expense | Placeholder |

## Development Status

This is a work-in-progress project with many features marked as "coming in Step X". The database layer (`database/db.py`) needs to be implemented with `get_db()`, `init_db()`, and `seed_db()` functions.
