import os
import csv
import statistics
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import extract, func

app = Flask(__name__)

# =========================
# CONFIG (PostgreSQL via env var)
# =========================
# Put this in your system env:
# DATABASE_URL=postgresql://username:password@localhost:5432/expense_tracker
db_url = os.environ.get("DATABASE_URL")

if not db_url:
    # Local fallback (change ONLY locally, not on GitHub)
    db_url = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/expense_tracker"

# Some hosts provide postgres:// which SQLAlchemy prefers as postgresql://
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================
# MODEL
# =========================
class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    date = db.Column(db.Date, nullable=False)  # we store dummy-year (2000-MM-DD)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# =========================
# HELPERS
# =========================
def make_mmdd_date(month_str: str, day_str: str):
    """
    Convert month/day dropdown into an actual date using a dummy year (2000).
    2000 is leap year (Feb 29 allowed).
    """
    try:
        m = int(month_str)
        d = int(day_str)
        return datetime(year=2000, month=m, day=d).date(), None
    except (TypeError, ValueError):
        return None, "Invalid month/day combination. Please choose a valid date."

def compute_dashboard_data():
    expenses = Expense.query.order_by(Expense.created_at.desc()).all()

    total = sum(exp.amount for exp in expenses)

    category_totals = {}
    for exp in expenses:
        category_totals[exp.category] = category_totals.get(exp.category, 0) + exp.amount

    # Totals grouped by MM-DD
    dm_rows = db.session.query(
        extract("month", Expense.date).label("m"),
        extract("day", Expense.date).label("d"),
        func.sum(Expense.amount).label("t"),
    ).group_by("m", "d").order_by("m", "d").all()

    dm_totals = {f"{int(m):02d}-{int(d):02d}": float(t) for m, d, t in dm_rows}

    # Simple anomaly threshold: mean + 2*stdev
    amounts = [exp.amount for exp in expenses]
    if len(amounts) > 1:
        threshold = statistics.mean(amounts) + 2 * statistics.stdev(amounts)
    else:
        threshold = 0
    anomalies = [exp.id for exp in expenses if exp.amount > threshold]

    return expenses, total, category_totals, dm_totals, anomalies

# =========================
# ROUTES
# =========================
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        category = request.form.get("category")
        month = request.form.get("month")
        day = request.form.get("day")

        # amount safe parse
        try:
            amount = float(request.form.get("amount", "0"))
        except ValueError:
            amount = 0

        if not title or not category or not month or not day or amount <= 0:
            expenses, total, category_totals, dm_totals, anomalies = compute_dashboard_data()
            return render_template(
                "index.html",
                expenses=expenses,
                total=total,
                category_totals=category_totals,
                dm_totals=dm_totals,
                anomalies=anomalies,
                error_message="Please fill all fields correctly."
            )

        date_obj, err = make_mmdd_date(month, day)
        if err:
            expenses, total, category_totals, dm_totals, anomalies = compute_dashboard_data()
            return render_template(
                "index.html",
                expenses=expenses,
                total=total,
                category_totals=category_totals,
                dm_totals=dm_totals,
                anomalies=anomalies,
                error_message=err
            )

        db.session.add(Expense(title=title, amount=amount, category=category, date=date_obj))
        db.session.commit()
        return redirect(url_for("home"))

    expenses, total, category_totals, dm_totals, anomalies = compute_dashboard_data()
    return render_template(
        "index.html",
        expenses=expenses,
        total=total,
        category_totals=category_totals,
        dm_totals=dm_totals,
        anomalies=anomalies
    )

@app.route("/delete/<int:id>")
def delete_expense(id):
    exp = Expense.query.get_or_404(id)
    db.session.delete(exp)
    db.session.commit()
    return redirect(url_for("home"))

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_expense(id):
    expense = Expense.query.get_or_404(id)

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        category = request.form.get("category")
        month = request.form.get("month")
        day = request.form.get("day")

        try:
            amount = float(request.form.get("amount", "0"))
        except ValueError:
            amount = 0

        if not title or not category or not month or not day or amount <= 0:
            return render_template("edit.html", expense=expense, error_message="Please fill all fields correctly.")

        new_date, err = make_mmdd_date(month, day)
        if err:
            return render_template("edit.html", expense=expense, error_message=err)

        expense.title = title
        expense.amount = amount
        expense.category = category
        expense.date = new_date
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("edit.html", expense=expense)

@app.route("/export")
def export_csv():
    expenses = Expense.query.order_by(Expense.created_at.desc()).all()

    def generate():
        writer = csv.writer(open(os.devnull, "w"))
        # header
        yield "ID,Title,Amount,Category,MM-DD\n"
        for exp in expenses:
            row = [exp.id, exp.title, exp.amount, exp.category, exp.date.strftime("%m-%d")]
            # manual csv line (simple & safe enough for this use)
            yield ",".join(map(lambda x: f'"{x}"' if isinstance(x, str) and "," in x else str(x), row)) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=expenses.csv"},
    )

# =========================
# RUN
# =========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)