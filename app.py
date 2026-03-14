import os
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///library.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "dev-secret")

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)  # demo: plaintext
    role = db.Column(db.String(10), nullable=False)  # admin | user
    name = db.Column(db.String(120), nullable=False)


class Membership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    duration_months = db.Column(db.Integer, nullable=False, default=6)
    status = db.Column(db.String(20), nullable=False, default="active")
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=False, default=lambda: date.today() + timedelta(days=180))


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    serial_no = db.Column(db.String(80), unique=True, nullable=False)
    item_type = db.Column(db.String(20), nullable=False, default="book")  # book | movie
    available = db.Column(db.Boolean, default=True)


class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    membership_id = db.Column(db.Integer, db.ForeignKey("membership.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date, nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    returned = db.Column(db.Boolean, default=False)
    fine_amount = db.Column(db.Float, default=0)
    fine_paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    membership = db.relationship("Membership", backref="issues")
    item = db.relationship("Item", backref="issues")


# --- helpers -----------------------------------------------------------------

def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_role = session.get("user_role")
            if not user_role:
                flash("Please log in first.", "error")
                return redirect(url_for("index"))
            if role and user_role != role:
                flash("You do not have access to this area.", "error")
                return redirect(url_for("index"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# --- routes ------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username, password=password, role="admin").first()
        if user:
            session["user_role"] = "admin"
            session["user_name"] = user.name
            flash("Welcome, admin!", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials", "error")
    return render_template("admin_login.html")


@app.route("/login/user", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username, password=password, role="user").first()
        if user:
            session["user_role"] = "user"
            session["user_name"] = user.name
            flash("Welcome!", "success")
            return redirect(url_for("user_dashboard"))
        flash("Invalid user credentials", "error")
    return render_template("user_login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Logged out", "success")
    return redirect(url_for("index"))


@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():
    return render_template("admin_dashboard.html")


@app.route("/user")
@login_required()
def user_dashboard():
    return render_template("user_dashboard.html")


@app.route("/maintenance")
@login_required(role="admin")
def maintenance():
    return render_template("maintenance.html")


@app.route("/maintenance/membership/add", methods=["POST"])
@login_required(role="admin")
def add_membership():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    duration = int(request.form.get("duration_months", 6))
    if not name or not email:
        flash("Name and email required", "error")
        return redirect(url_for("maintenance"))
    start = date.today()
    end = start + timedelta(days=duration * 30)
    m = Membership(name=name, email=email, duration_months=duration, start_date=start, end_date=end)
    db.session.add(m)
    db.session.commit()
    flash("Membership added", "success")
    return redirect(url_for("maintenance"))


@app.route("/maintenance/membership/update", methods=["POST"])
@login_required(role="admin")
def update_membership():
    membership_id = request.form.get("membership_id")
    extend = int(request.form.get("extend_months", 0))
    status = request.form.get("status", "active")
    membership = Membership.query.get(membership_id)
    if not membership:
        flash("Membership not found", "error")
        return redirect(url_for("maintenance"))
    if extend > 0:
        membership.end_date = membership.end_date + timedelta(days=extend * 30)
        membership.duration_months += extend
    membership.status = status
    db.session.commit()
    flash("Membership updated", "success")
    return redirect(url_for("maintenance"))


@app.route("/maintenance/item/add", methods=["POST"])
@login_required(role="admin")
def add_item():
    item_type = request.form.get("item_type", "book")
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    serial_no = request.form.get("serial_no", "").strip()
    if not title or not author or not serial_no:
        flash("All item fields are required", "error")
        return redirect(url_for("maintenance"))
    existing = Item.query.filter_by(serial_no=serial_no).first()
    if existing:
        flash("Serial already exists", "error")
        return redirect(url_for("maintenance"))
    item = Item(title=title, author=author, serial_no=serial_no, item_type=item_type, available=True)
    db.session.add(item)
    db.session.commit()
    flash("Item added", "success")
    return redirect(url_for("maintenance"))


@app.route("/maintenance/item/update", methods=["POST"])
@login_required(role="admin")
def update_item():
    serial_no = request.form.get("serial_no", "").strip()
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    available = request.form.get("available", "true") == "true"
    item = Item.query.filter_by(serial_no=serial_no).first()
    if not item:
        flash("Item not found", "error")
        return redirect(url_for("maintenance"))
    if not title or not author:
        flash("Title and author are required", "error")
        return redirect(url_for("maintenance"))
    item.title = title
    item.author = author
    item.available = available
    db.session.commit()
    flash("Item updated", "success")
    return redirect(url_for("maintenance"))


@app.route("/maintenance/user/add", methods=["POST"])
@login_required(role="admin")
def add_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    name = request.form.get("name", "").strip()
    role = request.form.get("role", "user")
    if not username or not password or not name:
        flash("All user fields required", "error")
        return redirect(url_for("maintenance"))
    if User.query.filter_by(username=username).first():
        flash("Username already exists", "error")
        return redirect(url_for("maintenance"))
    user = User(username=username, password=password, role=role, name=name)
    db.session.add(user)
    db.session.commit()
    flash("User added", "success")
    return redirect(url_for("maintenance"))


@app.route("/maintenance/user/update", methods=["POST"])
@login_required(role="admin")
def update_user():
    username = request.form.get("username", "").strip()
    user = User.query.filter_by(username=username).first()
    if not user:
        flash("User not found", "error")
        return redirect(url_for("maintenance"))
    user.name = request.form.get("name", user.name)
    user.role = request.form.get("role", user.role)
    password = request.form.get("password")
    if password:
        user.password = password
    db.session.commit()
    flash("User updated", "success")
    return redirect(url_for("maintenance"))


@app.route("/reports")
@login_required()
def reports():
    today = date.today()
    active = Issue.query.filter_by(returned=False).all()
    overdue = []
    for issue in active:
        if issue.return_date < today:
            days = (today - issue.return_date).days
            overdue.append({
                "member_name": issue.membership.name,
                "title": issue.item.title,
                "return_date": issue.return_date,
                "days_overdue": days,
            })
    memberships = Membership.query.order_by(Membership.id).all()
    books = Item.query.filter_by(item_type="book").all()
    movies = Item.query.filter_by(item_type="movie").all()
    pending = []
    active_rows = [
        {
            "member_name": i.membership.name,
            "title": i.item.title,
            "issue_date": i.issue_date,
            "return_date": i.return_date,
        }
        for i in active
    ]
    return render_template(
        "reports.html",
        active_issues=active_rows,
        overdue=overdue,
        memberships=memberships,
        books=books,
        movies=movies,
        pending=pending,
    )


@app.route("/transactions/issue", methods=["GET", "POST"])
@login_required()
def transactions_issue():
    query = request.form.get("query") if request.method == "POST" else None
    if request.method == "POST" and not query:
        flash("Enter a title or author to search.", "error")
        return redirect(url_for("transactions_issue"))

    items = Item.query
    if query:
        like = f"%{query}%"
        items = items.filter((Item.title.ilike(like)) | (Item.author.ilike(like)))
    items = items.order_by(Item.title).all()
    today = date.today()
    default_return = (today + timedelta(days=15)).isoformat()
    return render_template("transactions_issue.html", items=items, today=today.isoformat(), default_return=default_return)


@app.route("/transactions/issue/submit", methods=["POST"])
@login_required()
def issue_book():
    membership_id = request.form.get("membership_id")
    serial_no = request.form.get("selected_serial") or request.form.get("serial_no")
    issue_date_str = request.form.get("issue_date")
    return_date_str = request.form.get("return_date")
    remarks = request.form.get("remarks")

    if not membership_id or not serial_no or not issue_date_str or not return_date_str:
        flash("All fields required", "error")
        return redirect(url_for("transactions_issue"))

    issue_date = date.fromisoformat(issue_date_str)
    return_date = date.fromisoformat(return_date_str)
    if issue_date < date.today():
        flash("Issue date cannot be earlier than today", "error")
        return redirect(url_for("transactions_issue"))
    if return_date > issue_date + timedelta(days=15):
        flash("Return date cannot be more than 15 days from issue", "error")
        return redirect(url_for("transactions_issue"))

    membership = Membership.query.get(membership_id)
    item = Item.query.filter_by(serial_no=serial_no).first()
    if not membership:
        flash("Membership not found", "error")
        return redirect(url_for("transactions_issue"))
    if not item or not item.available:
        flash("Book/Movie not available", "error")
        return redirect(url_for("transactions_issue"))

    issue = Issue(
        membership_id=membership.id,
        item_id=item.id,
        issue_date=issue_date,
        return_date=return_date,
        remarks=remarks,
    )
    item.available = False
    db.session.add(issue)
    db.session.commit()
    flash("Book issued", "success")
    return redirect(url_for("transactions_issue"))


@app.route("/transactions/return", methods=["GET", "POST"])
@login_required()
def transactions_return():
    issue_details = None
    if request.method == "POST":
        serial_no = request.form.get("serial_lookup")
        if not serial_no:
            flash("Serial number required to fetch issue details", "error")
            return redirect(url_for("transactions_return"))
        issue = Issue.query.join(Item).filter(Item.serial_no == serial_no, Issue.returned == False).first()
        if not issue:
            flash("No open issue for this serial", "error")
            return redirect(url_for("transactions_return"))
        issue_details = {
            "issue_id": issue.id,
            "serial_no": serial_no,
            "title": issue.item.title,
            "author": issue.item.author,
            "issue_date": issue.issue_date.isoformat(),
            "planned_return": issue.return_date.isoformat(),
        }
    today = date.today().isoformat()
    return render_template("transactions_return.html", issue=issue_details, today=today)


@app.route("/transactions/return/submit", methods=["POST"])
@login_required()
def return_book():
    issue_id = request.form.get("issue_id")
    return_date_str = request.form.get("return_date")
    remarks = request.form.get("remarks")
    if not issue_id or not return_date_str:
        flash("Issue and return date required", "error")
        return redirect(url_for("transactions_return"))

    issue = Issue.query.get(issue_id)
    if not issue or issue.returned:
        flash("Issue not found", "error")
        return redirect(url_for("transactions_return"))

    return_date = date.fromisoformat(return_date_str)
    issue.remarks = remarks
    fine_amount = 0
    days_over = 0
    if return_date > issue.return_date:
        days_over = (return_date - issue.return_date).days
        fine_amount = days_over * 1
    issue.fine_amount = fine_amount
    issue.return_date = issue.return_date  # keep planned date for record
    db.session.commit()

    fine = {
        "issue_id": issue.id,
        "amount": fine_amount,
        "days_overdue": days_over,
        "title": issue.item.title,
        "author": issue.item.author,
        "serial_no": issue.item.serial_no,
        "issue_date": issue.issue_date,
        "planned_return": issue.return_date,
        "actual_return": return_date,
    }
    return render_template("transactions_return.html", fine=fine, today=date.today().isoformat())


@app.route("/transactions/fine/pay", methods=["POST"])
@login_required()
def pay_fine():
    issue_id = request.form.get("issue_id")
    fine_paid = request.form.get("fine_paid") == "yes"
    remarks = request.form.get("remarks")

    issue = Issue.query.get(issue_id)
    if not issue:
        flash("Issue not found", "error")
        return redirect(url_for("transactions_return"))
    if issue.fine_amount <= 0:
        flash("No fine due", "success")
    elif not fine_paid:
        flash("Fine must be paid before closing", "error")
        return redirect(url_for("transactions_return"))
    issue.fine_paid = fine_paid
    issue.remarks = remarks or issue.remarks
    issue.returned = True
    issue.item.available = True
    db.session.commit()
    flash("Return completed", "success")
    return redirect(url_for("transactions_return"))


# --- CLI helpers -------------------------------------------------------------

@app.cli.command("init-db")
def init_db():
    """Reset and seed the database."""
    db.drop_all()
    db.create_all()
    admin = User(username="admin", password="admin", role="admin", name="Admin User")
    user = User(username="user", password="user", role="user", name="Regular User")
    m1 = Membership(name="Alice", email="alice@example.com", duration_months=6)
    m2 = Membership(name="Bob", email="bob@example.com", duration_months=12)
    b1 = Item(title="Sample Book", author="Author A", serial_no="B-001", item_type="book", available=True)
    b2 = Item(title="Sample Movie", author="Director B", serial_no="M-001", item_type="movie", available=True)
    db.session.add_all([admin, user, m1, m2, b1, b2])
    db.session.commit()
    print("Database initialized with sample data")


if __name__ == "__main__":
    app.run(debug=True)
