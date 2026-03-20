import csv
from flask import Flask, render_template, request, redirect, url_for, Response, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import extract, func
import statistics

app = Flask(__name__)

app.config["SECRET_KEY"] = "change-this-to-a-random-secret"   # REQUIRED for sessions
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postpinky@localhost:5432/expense_tracker"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================
# FLASK-LOGIN SETUP
# =========================
login_manager = LoginManager(app)
login_manager.login_view = "login"          # redirect here if @login_required fails
login_manager.login_message = "Please log in to access your expenses."

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# MODELS
# =========================
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    expenses      = db.relationship("Expense", backref="owner", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Expense(db.Model):
    __tablename__ = "expenses"
    id         = db.Column(db.Integer, primary_key=True)
    title      = db.Column(db.String(100), nullable=False)
    amount     = db.Column(db.Float, nullable=False)
    category   = db.Column(db.String(50), nullable=False)
    date       = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # ↓ only new column added to Expense
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

# =========================
# DATE VALIDATION
# =========================
def make_mmdd_date(month_str, day_str):
    try:
        month = int(month_str)
        day   = int(day_str)
        return datetime(year=2000, month=month, day=day).date(), None
    except:
        return None, "Invalid month/day combination."

# =========================
# DASHBOARD DATA  (scoped to current_user)
# =========================
def compute_dashboard_data():
    expenses = (Expense.query
                .filter_by(user_id=current_user.id)      # ← only this user's data
                .order_by(Expense.created_at.desc())
                .all())

    total = sum(exp.amount for exp in expenses)

    category_totals = {}
    for exp in expenses:
        category_totals[exp.category] = category_totals.get(exp.category, 0) + exp.amount

    dm_query = (db.session.query(
                    extract("month", Expense.date),
                    extract("day",   Expense.date),
                    func.sum(Expense.amount))
                .filter(Expense.user_id == current_user.id)   # ← scoped
                .group_by(extract("month", Expense.date), extract("day", Expense.date))
                .order_by(extract("month", Expense.date), extract("day", Expense.date))
                .all())

    dm_totals = {f"{int(m):02d}-{int(d):02d}": float(t) for m, d, t in dm_query}

    amounts   = [exp.amount for exp in expenses]
    threshold = (statistics.mean(amounts) + 2 * statistics.stdev(amounts)) if len(amounts) > 1 else 0
    anomalies = [exp.id for exp in expenses if exp.amount > threshold]

    return expenses, total, category_totals, dm_totals, anomalies

# =========================
# AUTH ROUTES
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("register.html", error_message="Email and password required.")

        if User.query.filter_by(email=email).first():
            return render_template("register.html", error_message="Email already registered.")

        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("home"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = "remember" in request.form

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("home"))

        return render_template("login.html", error_message="Invalid email or password.")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# =========================
# EXPENSE ROUTES  (all protected)
# =========================
@app.route("/", methods=["GET", "POST"])
@login_required
def home():
    if request.method == "POST":
        title    = request.form.get("title")
        amount   = float(request.form.get("amount", 0))
        category = request.form.get("category")
        month    = request.form.get("month")
        day      = request.form.get("day")

        if not title or amount <= 0 or not category:
            expenses, total, category_totals, dm_totals, anomalies = compute_dashboard_data()
            return render_template("index.html",
                expenses=expenses, total=total,
                category_totals=category_totals, dm_totals=dm_totals,
                anomalies=anomalies, error_message="Please fill all fields correctly.")

        expense_date, err = make_mmdd_date(month, day)
        if err:
            expenses, total, category_totals, dm_totals, anomalies = compute_dashboard_data()
            return render_template("index.html",
                expenses=expenses, total=total,
                category_totals=category_totals, dm_totals=dm_totals,
                anomalies=anomalies, error_message=err)

        new_expense = Expense(
            title=title, amount=amount, category=category,
            date=expense_date, user_id=current_user.id    # ← tie to logged-in user
        )
        db.session.add(new_expense)
        db.session.commit()
        return redirect(url_for("home"))

    expenses, total, category_totals, dm_totals, anomalies = compute_dashboard_data()
    return render_template("index.html",
        expenses=expenses, total=total,
        category_totals=category_totals, dm_totals=dm_totals,
        anomalies=anomalies)


@app.route("/delete/<int:id>")
@login_required
def delete_expense(id):
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()  # ← ownership check
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_expense(id):
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()  # ← ownership check

    if request.method == "POST":
        expense.title    = request.form.get("title")
        expense.amount   = float(request.form.get("amount", 0))
        expense.category = request.form.get("category")

        month, day = request.form.get("month"), request.form.get("day")
        new_date, err = make_mmdd_date(month, day)
        if err:
            return render_template("edit.html", expense=expense, error_message=err)

        expense.date = new_date
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("edit.html", expense=expense)


@app.route("/export")
@login_required
def export_csv():
    expenses = (Expense.query
                .filter_by(user_id=current_user.id)      # ← only this user's data
                .order_by(Expense.created_at.desc())
                .all())

    def generate():
        yield ",".join(["ID", "Title", "Amount", "Category", "MM-DD"]) + "\n"
        for exp in expenses:
            yield ",".join(map(str, [exp.id, exp.title, exp.amount, exp.category,
                                     exp.date.strftime("%m-%d")])) + "\n"

    return Response(generate(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=expenses.csv"})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
