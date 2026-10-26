from datetime import datetime

from database.db import close_db, get_db


def _format_member_since(created_at):
    if not created_at:
        return ""
    try:
        return datetime.fromisoformat(created_at).strftime("%B %Y")
    except (TypeError, ValueError):
        return ""


def get_user_by_id(user_id):
    db = get_db()
    try:
        row = db.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "name": row["name"],
            "email": row["email"],
            "member_since": _format_member_since(row["created_at"]),
        }
    finally:
        close_db()


def _expense_filter(user_id, date_from, date_to):
    if date_from and date_to:
        return (
            "WHERE user_id = ? AND date BETWEEN ? AND ?",
            (user_id, date_from, date_to),
        )
    return "WHERE user_id = ?", (user_id,)


def get_summary_stats(user_id, date_from=None, date_to=None):
    where, params = _expense_filter(user_id, date_from, date_to)
    db = get_db()
    try:
        totals = db.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total_spent, "
            f"COUNT(*) AS transaction_count FROM expenses {where}",
            params,
        ).fetchone()
        top = db.execute(
            "SELECT category FROM expenses "
            f"{where} GROUP BY category "
            "ORDER BY SUM(amount) DESC, category ASC LIMIT 1",
            params,
        ).fetchone()

        total_spent = totals["total_spent"] if totals is not None else 0
        if total_spent is None:
            total_spent = 0
        transaction_count = totals["transaction_count"] if totals is not None else 0

        return {
            "total_spent": total_spent,
            "transaction_count": int(transaction_count),
            "top_category": top["category"] if top is not None else "—",
        }
    finally:
        close_db()


def insert_expense(user_id, amount, category, date, description):
    db = get_db()
    try:
        with db:
            cursor = db.execute(
                "INSERT INTO expenses "
                "(user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, date, description),
            )
        return cursor.lastrowid
    finally:
        close_db()


def get_expense_by_id(expense_id, user_id):
    db = get_db()
    try:
        row = db.execute(
            "SELECT id, user_id, amount, category, date, description "
            "FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        ).fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        close_db()


def update_expense(expense_id, user_id, amount, category, date, description):
    db = get_db()
    try:
        with db:
            cursor = db.execute(
                "UPDATE expenses "
                "SET amount = ?, category = ?, date = ?, description = ? "
                "WHERE id = ? AND user_id = ?",
                (amount, category, date, description, expense_id, user_id),
            )
        return cursor.rowcount
    finally:
        close_db()


def delete_expense(expense_id, user_id):
    db = get_db()
    try:
        with db:
            cursor = db.execute(
                "DELETE FROM expenses WHERE id = ? AND user_id = ?",
                (expense_id, user_id),
            )
        return cursor.rowcount
    finally:
        close_db()


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    where, params = _expense_filter(user_id, date_from, date_to)
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, date, COALESCE(description, '') AS description, "
            f"category, amount FROM expenses {where} "
            "ORDER BY date DESC, id DESC LIMIT ?",
            params + (limit,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "date": row["date"],
                "description": row["description"],
                "category": row["category"],
                "amount": row["amount"],
            }
            for row in rows
        ]
    finally:
        close_db()


def get_category_breakdown(user_id, date_from=None, date_to=None):
    where, params = _expense_filter(user_id, date_from, date_to)
    db = get_db()
    try:
        rows = db.execute(
            "SELECT category AS name, SUM(amount) AS amount "
            f"FROM expenses {where} "
            "GROUP BY category "
            "ORDER BY SUM(amount) DESC, category ASC",
            params,
        ).fetchall()
        if not rows:
            return []
        total = sum(row["amount"] for row in rows)
        if not total:
            return [
                {"name": row["name"], "amount": row["amount"], "pct": 0}
                for row in rows
            ]
        breakdown = []
        allocated = 0
        for row in rows:
            pct = round(row["amount"] / total * 100)
            allocated += pct
            breakdown.append(
                {"name": row["name"], "amount": row["amount"], "pct": pct}
            )
        breakdown[0]["pct"] += 100 - allocated
        return breakdown
    finally:
        close_db()
