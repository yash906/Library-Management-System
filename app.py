import os
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///library.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "dev-secret")

db = SQLAlchemy(app)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # admin | user
    name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")


class Membership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    contact_number = db.Column(db.String(20), nullable=False, default="")
    contact_address = db.Column(db.String(300), nullable=False, default="")
    aadhar_card_no = db.Column(db.String(20), nullable=False, default="")
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=False)
    duration_months = db.Column(db.Integer, nullable=False, default=6)
    status = db.Column(db.String(20), nullable=False, default="active")


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    serial_no = db.Column(db.String(80), unique=True, nullable=False)
    item_type = db.Column(db.String(20), nullable=False, default="book")  # book | movie
    category = db.Column(db.String(100), nullable=False, default="General")
    available = db.Column(db.Boolean, default=True)


class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    membership_id = db.Column(db.Integer, db.ForeignKey("membership.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date, nullable=False)
    actual_return_date = db.Column(db.Date, nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    returned = db.Column(db.Boolean, default=False)
    fine_amount = db.Column(db.Float, default=0)
    fine_paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    membership = db.relationship("Membership", backref="issues")
    item = db.relationship("Item", backref="issues")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# Category code mapping
CATEGORIES = {
    "Science": "SC",
    "Economics": "EC",
    "Fiction": "FC",
    "Children": "CH",
    "Personal Development": "PD",
}

CATEGORY_NAMES = list(CATEGORIES.keys())


def generate_serial_no(category, item_type):
    """Generate serial number like FCB000001, SCM000002, etc."""
    prefix = CATEGORIES.get(category, "XX")
    type_code = "B" if item_type == "book" else "M"
    pattern = f"{prefix}{type_code}%"
    last_item = (
        Item.query.filter(Item.serial_no.like(pattern))
        .order_by(Item.serial_no.desc())
        .first()
    )
    if last_item:
        last_num = int(last_item.serial_no[3:])
        next_num = last_num + 1
    else:
        next_num = 1
    return f"{prefix}{type_code}{next_num:06d}"


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

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
            session["user_id"] = user.id
            flash("Welcome, admin!", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials.", "error")
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
            session["user_id"] = user.id
            flash("Welcome!", "success")
            return redirect(url_for("user_dashboard"))
        flash("Invalid user credentials.", "error")
    return render_template("user_login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Dashboards
# ---------------------------------------------------------------------------

@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():
    return render_template("admin_dashboard.html")


@app.route("/user")
@login_required()
def user_dashboard():
    return render_template("user_dashboard.html")


# ---------------------------------------------------------------------------
# Maintenance (admin only)
# ---------------------------------------------------------------------------

@app.route("/maintenance")
@login_required(role="admin")
def maintenance():
    return render_template("maintenance.html", active_tab="home")


# -- Add Membership --------------------------------------------------------

@app.route("/maintenance/membership/add", methods=["GET", "POST"])
@login_required(role="admin")
def add_membership():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        contact_number = request.form.get("contact_number", "").strip()
        contact_address = request.form.get("contact_address", "").strip()
        aadhar = request.form.get("aadhar_card_no", "").strip()
        duration = int(request.form.get("duration_months", 6))
        start_date_str = request.form.get("start_date", "")

        if not name or not contact_number or not contact_address or not aadhar:
            flash("All fields are mandatory.", "error")
            return redirect(url_for("add_membership"))

        start = date.fromisoformat(start_date_str) if start_date_str else date.today()
        end = start + timedelta(days=duration * 30)
        m = Membership(
            name=name,
            contact_number=contact_number,
            contact_address=contact_address,
            aadhar_card_no=aadhar,
            start_date=start,
            end_date=end,
            duration_months=duration,
        )
        db.session.add(m)
        db.session.commit()
        flash(f"Membership #{m.id} created successfully.", "success")
        return redirect(url_for("add_membership"))
    return render_template("membership_add.html", today=date.today().isoformat(), active_tab="add_membership")


# -- Update Membership -----------------------------------------------------

@app.route("/maintenance/membership/update", methods=["GET", "POST"])
@login_required(role="admin")
def update_membership():
    membership = None
    if request.method == "POST":
        action = request.form.get("action")

        if action == "fetch":
            mid = request.form.get("membership_id")
            membership = Membership.query.get(mid)
            if not membership:
                flash("Membership not found.", "error")
                return redirect(url_for("update_membership"))
            return render_template("membership_update.html", membership=membership, active_tab="update_membership")

        if action == "update":
            mid = request.form.get("membership_id")
            membership = Membership.query.get(mid)
            if not membership:
                flash("Membership not found.", "error")
                return redirect(url_for("update_membership"))
            extend = int(request.form.get("extend_months", 0))
            cancel = request.form.get("cancel_membership")
            if cancel == "yes":
                membership.status = "cancelled"
                db.session.commit()
                flash("Membership cancelled.", "success")
                return redirect(url_for("update_membership"))
            if extend > 0:
                membership.end_date = membership.end_date + timedelta(days=extend * 30)
                membership.duration_months += extend
            db.session.commit()
            flash("Membership updated.", "success")
            return redirect(url_for("update_membership"))

    return render_template("membership_update.html", membership=None, active_tab="update_membership")


# -- Add Book/Movie --------------------------------------------------------

@app.route("/maintenance/item/add", methods=["GET", "POST"])
@login_required(role="admin")
def add_item():
    if request.method == "POST":
        item_type = request.form.get("item_type", "book")
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        category = request.form.get("category", "").strip()

        if not title or not author or not category:
            flash("All fields are mandatory.", "error")
            return redirect(url_for("add_item"))

        if category not in CATEGORIES:
            flash("Invalid category.", "error")
            return redirect(url_for("add_item"))

        serial_no = generate_serial_no(category, item_type)

        item = Item(
            title=title,
            author=author,
            serial_no=serial_no,
            item_type=item_type,
            category=category,
            available=True,
        )
        db.session.add(item)
        db.session.commit()
        flash(f"{item_type.title()} '{title}' added with serial no {serial_no}.", "success")
        return redirect(url_for("add_item"))

    return render_template("item_add.html", categories=CATEGORY_NAMES, active_tab="add_item")


# -- Update Book/Movie ----------------------------------------------------

@app.route("/maintenance/item/update", methods=["GET", "POST"])
@login_required(role="admin")
def update_item():
    item = None
    if request.method == "POST":
        action = request.form.get("action")

        if action == "fetch":
            serial_no = request.form.get("serial_no", "").strip()
            item = Item.query.filter_by(serial_no=serial_no).first()
            if not item:
                flash("Item not found.", "error")
                return redirect(url_for("update_item"))
            return render_template("item_update.html", item=item, categories=CATEGORY_NAMES, active_tab="update_item")

        if action == "update":
            serial_no = request.form.get("serial_no", "").strip()
            item = Item.query.filter_by(serial_no=serial_no).first()
            if not item:
                flash("Item not found.", "error")
                return redirect(url_for("update_item"))
            title = request.form.get("title", "").strip()
            author = request.form.get("author", "").strip()
            category = request.form.get("category", "").strip()
            item_type = request.form.get("item_type", item.item_type)
            status = request.form.get("status")

            if not title or not author or not category:
                flash("All fields are mandatory.", "error")
                return render_template("item_update.html", item=item, categories=CATEGORY_NAMES, active_tab="update_item")

            item.title = title
            item.author = author
            item.category = category
            item.item_type = item_type
            if status == "withdrawn":
                item.available = False
            db.session.commit()
            flash("Item updated.", "success")
            return redirect(url_for("update_item"))

    return render_template("item_update.html", item=None, categories=CATEGORY_NAMES, active_tab="update_item")


# -- User Management -------------------------------------------------------

@app.route("/maintenance/user", methods=["GET", "POST"])
@login_required(role="admin")
def manage_user():
    target_user = None
    if request.method == "POST":
        action = request.form.get("action")
        user_type = request.form.get("user_type", "new")

        if user_type == "new" or action == "add":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            name = request.form.get("name", "").strip()
            role = request.form.get("role", "user")
            if not username or not password or not name:
                flash("All fields are required for a new user.", "error")
                return redirect(url_for("manage_user"))
            if User.query.filter_by(username=username).first():
                flash("Username already exists.", "error")
                return redirect(url_for("manage_user"))
            user = User(username=username, password=password, role=role, name=name)
            db.session.add(user)
            db.session.commit()
            flash(f"User '{username}' created.", "success")
            return redirect(url_for("manage_user"))

        if action == "fetch":
            username = request.form.get("username", "").strip()
            target_user = User.query.filter_by(username=username).first()
            if not target_user:
                flash("User not found.", "error")
                return redirect(url_for("manage_user"))
            return render_template("user_manage.html", target_user=target_user, active_tab="manage_user")

        if action == "update":
            user_id = request.form.get("user_id")
            target_user = User.query.get(user_id)
            if not target_user:
                flash("User not found.", "error")
                return redirect(url_for("manage_user"))
            name = request.form.get("name", "").strip()
            if not name:
                flash("Name is mandatory.", "error")
                return render_template("user_manage.html", target_user=target_user, active_tab="manage_user")
            target_user.name = name
            target_user.role = request.form.get("role", target_user.role)
            target_user.status = request.form.get("status", target_user.status)
            password = request.form.get("password", "")
            if password:
                target_user.password = password
            db.session.commit()
            flash("User updated.", "success")
            return redirect(url_for("manage_user"))

    return render_template("user_manage.html", target_user=None, active_tab="manage_user")


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@app.route("/reports")
@login_required()
def reports():
    return render_template("reports.html", active_tab="home")


@app.route("/reports/active-issues")
@login_required()
def report_active_issues():
    active = Issue.query.filter_by(returned=False).all()
    rows = [
        {
            "member_name": i.membership.name,
            "membership_id": i.membership.id,
            "title": i.item.title,
            "serial_no": i.item.serial_no,
            "issue_date": i.issue_date,
            "return_date": i.return_date,
        }
        for i in active
    ]
    return render_template("report_active_issues.html", issues=rows, active_tab="active_issues")


@app.route("/reports/memberships")
@login_required()
def report_memberships():
    memberships = Membership.query.order_by(Membership.id).all()
    return render_template("report_memberships.html", memberships=memberships, active_tab="memberships")


@app.route("/reports/books")
@login_required()
def report_books():
    books = Item.query.filter_by(item_type="book").order_by(Item.title).all()
    return render_template("report_books.html", books=books, active_tab="books")


@app.route("/reports/movies")
@login_required()
def report_movies():
    movies = Item.query.filter_by(item_type="movie").order_by(Item.title).all()
    return render_template("report_movies.html", movies=movies, active_tab="movies")


@app.route("/reports/overdue")
@login_required()
def report_overdue():
    today = date.today()
    active = Issue.query.filter_by(returned=False).all()
    overdue = []
    for issue in active:
        if issue.return_date < today:
            days = (today - issue.return_date).days
            fine = days * 1.0
            overdue.append({
                "member_name": issue.membership.name,
                "title": issue.item.title,
                "serial_no": issue.item.serial_no,
                "return_date": issue.return_date,
                "days_overdue": days,
                "fine": fine,
            })
    return render_template("report_overdue.html", overdue=overdue, active_tab="overdue")


@app.route("/reports/pending")
@login_required()
def report_pending():
    pending = Issue.query.filter_by(returned=False).order_by(Issue.created_at.desc()).all()
    rows = [
        {
            "member_name": i.membership.name,
            "title": i.item.title,
            "serial_no": i.item.serial_no,
            "issue_date": i.issue_date,
            "return_date": i.return_date,
        }
        for i in pending
    ]
    return render_template("report_pending.html", pending=rows, active_tab="pending")


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@app.route("/transactions")
@login_required()
def transactions():
    return render_template("transactions.html", active_tab="home")


# -- Book Available (search) -----------------------------------------------

@app.route("/transactions/available", methods=["GET", "POST"])
@login_required()
def book_available():
    all_titles = [i.title for i in Item.query.order_by(Item.title).all()]
    all_authors = sorted(set(i.author for i in Item.query.all()))
    items = []
    selected_title = ""
    selected_author = ""
    if request.method == "POST":
        selected_title = request.form.get("book_name", "").strip()
        selected_author = request.form.get("author", "").strip()
        if not selected_title and not selected_author:
            flash("Please select at least a Book Name or an Author before searching.", "error")
            return render_template(
                "transactions_available.html",
                items=items,
                all_titles=all_titles,
                all_authors=all_authors,
                selected_title=selected_title,
                selected_author=selected_author,
                searched=False,
                active_tab="available",
            )
        query = Item.query
        if selected_title:
            query = query.filter(Item.title.ilike(f"%{selected_title}%"))
        if selected_author:
            query = query.filter(Item.author.ilike(f"%{selected_author}%"))
        items = query.order_by(Item.title).all()
    return render_template(
        "transactions_available.html",
        items=items,
        all_titles=all_titles,
        all_authors=all_authors,
        selected_title=selected_title,
        selected_author=selected_author,
        searched=request.method == "POST",
        active_tab="available",
    )


# -- Issue Book ------------------------------------------------------------

@app.route("/transactions/issue", methods=["GET", "POST"])
@login_required()
def transactions_issue():
    serial_no = request.args.get("serial_no", "")
    item = None
    if serial_no:
        item = Item.query.filter_by(serial_no=serial_no).first()
    today = date.today()
    default_return = (today + timedelta(days=15)).isoformat()
    memberships = Membership.query.filter_by(status="active").all()
    available_items = Item.query.filter_by(available=True).order_by(Item.title).all()
    return render_template(
        "transactions_issue.html",
        item=item,
        today=today.isoformat(),
        default_return=default_return,
        memberships=memberships,
        available_items=available_items,
        active_tab="issue",
    )


@app.route("/transactions/issue/submit", methods=["POST"])
@login_required()
def issue_book():
    membership_id = request.form.get("membership_id")
    serial_no = request.form.get("serial_no", "").strip()
    issue_date_str = request.form.get("issue_date")
    return_date_str = request.form.get("return_date")
    remarks = request.form.get("remarks", "")

    if not membership_id or not serial_no or not issue_date_str or not return_date_str:
        flash("All fields are required. Please fill in every field.", "error")
        return redirect(url_for("transactions_issue"))

    issue_date = date.fromisoformat(issue_date_str)
    return_date = date.fromisoformat(return_date_str)
    today = date.today()

    if issue_date < today:
        flash("Issue date cannot be earlier than today.", "error")
        return redirect(url_for("transactions_issue", serial_no=serial_no))

    if return_date > issue_date + timedelta(days=15):
        flash("Return date cannot be more than 15 days from issue date.", "error")
        return redirect(url_for("transactions_issue", serial_no=serial_no))

    if return_date < issue_date:
        flash("Return date cannot be before issue date.", "error")
        return redirect(url_for("transactions_issue", serial_no=serial_no))

    membership = Membership.query.get(membership_id)
    item = Item.query.filter_by(serial_no=serial_no).first()

    if not membership:
        flash("Membership not found.", "error")
        return redirect(url_for("transactions_issue"))
    if membership.status != "active":
        flash("Membership is not active.", "error")
        return redirect(url_for("transactions_issue"))
    if not item:
        flash("Book/Movie not found.", "error")
        return redirect(url_for("transactions_issue"))
    if not item.available:
        flash("This item is currently not available.", "error")
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
    flash(f"'{item.title}' issued successfully to {membership.name}.", "success")
    return redirect(url_for("transactions_issue"))


# -- Return Book -----------------------------------------------------------

@app.route("/transactions/return", methods=["GET", "POST"])
@login_required()
def transactions_return():
    # Get all active (unreturned) issues for dropdowns
    active_issues = Issue.query.filter_by(returned=False).all()
    issued_books = []
    for iss in active_issues:
        issued_books.append({
            "serial_no": iss.item.serial_no,
            "title": iss.item.title,
            "author": iss.item.author,
            "issue_date": iss.issue_date.isoformat(),
            "return_date": iss.return_date.isoformat(),
            "issue_id": iss.id,
        })
    today = date.today().isoformat()
    return render_template(
        "transactions_return.html",
        issued_books=issued_books,
        today=today,
        active_tab="return",
    )


@app.route("/transactions/return/submit", methods=["POST"])
@login_required()
def return_book():
    issue_id = request.form.get("issue_id")
    return_date_str = request.form.get("return_date")
    remarks = request.form.get("remarks", "")

    if not issue_id or not return_date_str:
        flash("All required fields must be filled.", "error")
        return redirect(url_for("transactions_return"))

    issue = Issue.query.get(issue_id)
    if not issue or issue.returned:
        flash("Issue not found or already returned.", "error")
        return redirect(url_for("transactions_return"))

    actual_return = date.fromisoformat(return_date_str)
    fine_amount = 0.0
    days_over = 0
    if actual_return > issue.return_date:
        days_over = (actual_return - issue.return_date).days
        fine_amount = days_over * 1.0

    issue.actual_return_date = actual_return
    issue.fine_amount = fine_amount
    if remarks:
        issue.remarks = remarks
    db.session.commit()

    # Always redirect to Pay Fine page
    fine = {
        "issue_id": issue.id,
        "title": issue.item.title,
        "author": issue.item.author,
        "serial_no": issue.item.serial_no,
        "issue_date": issue.issue_date.isoformat(),
        "return_date": issue.return_date.isoformat(),
        "actual_return": actual_return.isoformat(),
        "fine_amount": fine_amount,
        "days_overdue": days_over,
        "member_name": issue.membership.name,
    }
    return render_template("transactions_fine.html", fine=fine, active_tab="fine")


# -- Fine Payment ----------------------------------------------------------

@app.route("/transactions/fine", methods=["GET", "POST"])
@login_required()
def transactions_fine():
    issue_details = None
    if request.method == "POST":
        action = request.form.get("action")

        if action == "fetch":
            book_name = request.form.get("book_name", "").strip()
            serial_no = request.form.get("serial_no", "").strip()

            if not serial_no:
                flash("Serial number is required.", "error")
                return redirect(url_for("transactions_fine"))

            query = Issue.query.join(Item).filter(Issue.returned == False)
            if serial_no:
                query = query.filter(Item.serial_no == serial_no)
            if book_name:
                query = query.filter(Item.title.ilike(f"%{book_name}%"))

            issue = query.first()
            if not issue:
                flash("No open issue found for this book.", "error")
                return redirect(url_for("transactions_fine"))

            today = date.today()
            actual_return = today
            fine_amount = 0.0
            if actual_return > issue.return_date:
                days_over = (actual_return - issue.return_date).days
                fine_amount = days_over * 1.0

            issue_details = {
                "issue_id": issue.id,
                "serial_no": issue.item.serial_no,
                "title": issue.item.title,
                "author": issue.item.author,
                "issue_date": issue.issue_date.isoformat(),
                "return_date": issue.return_date.isoformat(),
                "actual_return_date": today.isoformat(),
                "fine_amount": fine_amount,
                "member_name": issue.membership.name,
            }

    today = date.today().isoformat()
    return render_template(
        "transactions_fine_pay.html",
        issue=issue_details,
        today=today,
        active_tab="fine",
    )


@app.route("/transactions/fine/pay", methods=["POST"])
@login_required()
def pay_fine():
    issue_id = request.form.get("issue_id")
    fine_paid = request.form.get("fine_paid") == "yes"
    remarks = request.form.get("remarks", "")
    actual_return_str = request.form.get("actual_return_date", "")

    issue = Issue.query.get(issue_id)
    if not issue:
        flash("Issue not found.", "error")
        return redirect(url_for("transactions_return"))

    # Set actual return date if provided from standalone Pay Fine form
    if actual_return_str and not issue.actual_return_date:
        actual_return = date.fromisoformat(actual_return_str)
        issue.actual_return_date = actual_return
        fine_amount = 0.0
        if actual_return > issue.return_date:
            days_over = (actual_return - issue.return_date).days
            fine_amount = days_over * 1.0
        issue.fine_amount = fine_amount
        db.session.commit()

    if issue.fine_amount > 0 and not fine_paid:
        flash("Fine must be paid before completing the return.", "error")
        fine = {
            "issue_id": issue.id,
            "title": issue.item.title,
            "author": issue.item.author,
            "serial_no": issue.item.serial_no,
            "issue_date": issue.issue_date.isoformat(),
            "return_date": issue.return_date.isoformat(),
            "actual_return": issue.actual_return_date.isoformat() if issue.actual_return_date else "",
            "fine_amount": issue.fine_amount,
            "days_overdue": (issue.actual_return_date - issue.return_date).days if issue.actual_return_date else 0,
            "member_name": issue.membership.name,
        }
        return render_template("transactions_fine.html", fine=fine, active_tab="fine")

    issue.fine_paid = True if issue.fine_amount > 0 else False
    issue.returned = True
    issue.item.available = True
    if remarks:
        issue.remarks = remarks
    db.session.commit()
    flash("Book returned successfully. Transaction completed.", "success")
    return redirect(url_for("transactions"))


# ---------------------------------------------------------------------------
# AJAX helpers
# ---------------------------------------------------------------------------

@app.route("/api/item/<serial_no>")
@login_required()
def api_get_item(serial_no):
    item = Item.query.filter_by(serial_no=serial_no).first()
    if not item:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "title": item.title,
        "author": item.author,
        "serial_no": item.serial_no,
        "item_type": item.item_type,
        "available": item.available,
    })


@app.route("/api/issue/<serial_no>")
@login_required()
def api_get_issue(serial_no):
    """Get active issue details by item serial number."""
    issue = Issue.query.join(Item).filter(
        Item.serial_no == serial_no, Issue.returned == False
    ).first()
    if not issue:
        return jsonify({"error": "No active issue found"}), 404
    return jsonify({
        "issue_id": issue.id,
        "title": issue.item.title,
        "author": issue.item.author,
        "serial_no": issue.item.serial_no,
        "issue_date": issue.issue_date.isoformat(),
        "return_date": issue.return_date.isoformat(),
        "member_name": issue.membership.name,
    })


@app.route("/api/membership/<int:mid>")
@login_required()
def api_get_membership(mid):
    m = Membership.query.get(mid)
    if not m:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "id": m.id,
        "name": m.name,
        "contact_number": m.contact_number,
        "contact_address": m.contact_address,
        "aadhar_card_no": m.aadhar_card_no,
        "start_date": m.start_date.isoformat(),
        "end_date": m.end_date.isoformat(),
        "duration_months": m.duration_months,
        "status": m.status,
    })


# ---------------------------------------------------------------------------
# Seed / Init
# ---------------------------------------------------------------------------

@app.cli.command("init-db")
def init_db_cmd():
    """Reset and seed the database."""
    _seed_db()


def _seed_db():
    db.drop_all()
    db.create_all()
    admin = User(username="admin", password="admin", role="admin", name="Admin User")
    user = User(username="user", password="user", role="user", name="Regular User")
    m1 = Membership(
        name="Alice Johnson", contact_number="9876543210",
        contact_address="123 Main St", aadhar_card_no="1234-5678-9012",
        start_date=date.today(), end_date=date.today() + timedelta(days=180),
        duration_months=6,
    )
    m2 = Membership(
        name="Bob Smith", contact_number="9876543211",
        contact_address="456 Oak Ave", aadhar_card_no="2345-6789-0123",
        start_date=date.today(), end_date=date.today() + timedelta(days=365),
        duration_months=12,
    )
    b1 = Item(title="The Great Gatsby", author="F. Scott Fitzgerald", serial_no="FCB000001", item_type="book", category="Fiction")
    b2 = Item(title="To Kill a Mockingbird", author="Harper Lee", serial_no="FCB000002", item_type="book", category="Fiction")
    b3 = Item(title="A Brief History of Time", author="Stephen Hawking", serial_no="SCB000001", item_type="book", category="Science")
    b4 = Item(title="The Catcher in the Rye", author="J.D. Salinger", serial_no="FCB000003", item_type="book", category="Fiction")
    b5 = Item(title="Freakonomics", author="Steven Levitt", serial_no="ECB000001", item_type="book", category="Economics")
    b6 = Item(title="Charlie and the Chocolate Factory", author="Roald Dahl", serial_no="CHB000001", item_type="book", category="Children")
    b7 = Item(title="The 7 Habits of Highly Effective People", author="Stephen Covey", serial_no="PDB000001", item_type="book", category="Personal Development")
    mv1 = Item(title="Inception", author="Christopher Nolan", serial_no="SCM000001", item_type="movie", category="Science")
    mv2 = Item(title="The Dark Knight", author="Christopher Nolan", serial_no="FCM000001", item_type="movie", category="Fiction")
    db.session.add_all([admin, user, m1, m2, b1, b2, b3, b4, b5, b6, b7, mv1, mv2])
    db.session.commit()
    print("Database initialized with sample data.")


with app.app_context():
    db.create_all()
    if not User.query.first():
        _seed_db()


if __name__ == "__main__":
    app.run(debug=True)
