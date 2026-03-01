import csv
from flask import Flask, render_template, request, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import extract, func
import statistics

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postpinky@localhost:5432/expense_tracker"
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
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# =========================
# DATE VALIDATION
# =========================
def make_mmdd_date(month_str, day_str):
    try:
        month = int(month_str)
        day = int(day_str)
        return datetime(year=2000, month=month, day=day).date(), None
    except:
        return None, "Invalid month/day combination."

# =========================
# DASHBOARD DATA
# =========================
def compute_dashboard_data():
    expenses = Expense.query.order_by(Expense.created_at.desc()).all()

    total = sum(exp.amount for exp in expenses)

    category_totals = {}
    for exp in expenses:
        category_totals[exp.category] = category_totals.get(exp.category, 0) + exp.amount

    dm_query = db.session.query(
        extract("month", Expense.date),
        extract("day", Expense.date),
        func.sum(Expense.amount)
    ).group_by(
        extract("month", Expense.date),
        extract("day", Expense.date)
    ).order_by(
        extract("month", Expense.date),
        extract("day", Expense.date)
    ).all()

    dm_totals = {f"{int(m):02d}-{int(d):02d}": float(t) for m, d, t in dm_query}

    amounts = [exp.amount for exp in expenses]
    threshold = (statistics.mean(amounts) + 2 * statistics.stdev(amounts)) if len(amounts) > 1 else 0
    anomalies = [exp.id for exp in expenses if exp.amount > threshold]

    return expenses, total, category_totals, dm_totals, anomalies

# =========================
# ROUTES
# =========================
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        title = request.form.get("title")
        amount = float(request.form.get("amount", 0))
        category = request.form.get("category")
        month = request.form.get("month")
        day = request.form.get("day")

        if not title or amount <= 0 or not category:
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

        expense_date, err = make_mmdd_date(month, day)
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

        new_expense = Expense(
            title=title,
            amount=amount,
            category=category,
            date=expense_date
        )

        db.session.add(new_expense)
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
    expense = Expense.query.get_or_404(id)
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for("home"))

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_expense(id):
    expense = Expense.query.get_or_404(id)

    if request.method == "POST":
        expense.title = request.form.get("title")
        expense.amount = float(request.form.get("amount", 0))
        expense.category = request.form.get("category")

        month = request.form.get("month")
        day = request.form.get("day")

        new_date, err = make_mmdd_date(month, day)
        if err:
            return render_template("edit.html", expense=expense, error_message=err)

        expense.date = new_date
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("edit.html", expense=expense)

@app.route("/export")
def export_csv():
    expenses = Expense.query.order_by(Expense.created_at.desc()).all()

    def generate():
        header = ["ID", "Title", "Amount", "Category", "MM-DD"]
        yield ",".join(header) + "\n"

        for exp in expenses:
            row = [
                exp.id,
                exp.title,
                exp.amount,
                exp.category,
                exp.date.strftime("%m-%d")
            ]
            yield ",".join(map(str, row)) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=expenses.csv"}
    )

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)