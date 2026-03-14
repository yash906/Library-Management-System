# Library Management System

A web-based Library Management System built with Flask and SQLite. It supports issuing and returning books/movies, membership management, fine calculation, and reporting — with role-based access for Admin and User accounts.

### Testing Credentials

| Role  | Username | Password |
|-------|----------|----------|
| Admin | admin    | admin    |
| User  | user     | user     |

## Features

### Transactions
- **Book Availability** — Search by title or author, view availability, and select items to issue
- **Issue Book** — Issue a book/movie to a member with auto-calculated return date (15 days)
- **Return Book** — Return an issued item with fine auto-calculated for overdue returns (Rs 1/day)
- **Pay Fine** — View and pay outstanding fines before completing a return

### Maintenance (Admin only)
- **Add Membership** — Create memberships with 6-month, 1-year, or 2-year durations
- **Update Membership** — Extend or cancel existing memberships
- **Add Book/Movie** — Add items with auto-generated serial numbers (category + type coded)
- **Update Book/Movie** — Edit item details or withdraw items from circulation
- **User Management** — Create new users or update existing accounts (Admin/User roles)

### Reports
- Active Issues
- Memberships
- Books / Movies inventory
- Overdue Returns (with fine amounts)
- Pending Requests

## Tech Stack

- **Backend:** Python 3, Flask, Flask-SQLAlchemy
- **Database:** SQLite
- **Frontend:** Jinja2 templates, vanilla CSS, vanilla JavaScript
- **Auth:** Session-based with role-based access control (Admin / User)

## Project Structure

```
Library Management System/
├── app.py                  # Flask application (models, routes, helpers)
├── requirements.txt        # Python dependencies
├── static/
│   └── style.css           # Application stylesheet
├── templates/
│   ├── base.html           # Base layout template
│   ├── index.html          # Landing page
│   ├── admin_login.html    # Admin login form
│   ├── user_login.html     # User login form
│   ├── admin_dashboard.html
│   ├── user_dashboard.html
│   ├── transactions.html         # Transactions sidebar layout
│   ├── transactions_available.html
│   ├── transactions_issue.html
│   ├── transactions_return.html
│   ├── transactions_fine.html
│   ├── transactions_fine_pay.html
│   ├── maintenance.html          # Maintenance sidebar layout
│   ├── membership_add.html
│   ├── membership_update.html
│   ├── item_add.html
│   ├── item_update.html
│   ├── user_manage.html
│   ├── reports.html              # Reports sidebar layout
│   ├── report_active_issues.html
│   ├── report_books.html
│   ├── report_memberships.html
│   ├── report_movies.html
│   ├── report_overdue.html
│   └── report_pending.html
└── instance/
    └── library.db          # SQLite database (auto-generated)
```

## Setup

### Prerequisites
- Python 3.10+

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd "Library Management System"

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
python app.py
```

The app starts at `http://127.0.0.1:5000`.

On first run, the database is automatically created and seeded with sample data.

### Default Credentials

| Role  | Username | Password |
|-------|----------|----------|
| Admin | admin    | admin    |
| User  | user     | user     |

### Reset Database

To reset the database with fresh seed data:

```bash
flask init-db
```

## Access Control

| Module       | Admin | User |
|-------------|-------|------|
| Maintenance | Yes   | No   |
| Transactions| Yes   | Yes  |
| Reports     | Yes   | Yes  |

## Serial Number Format

Serial numbers are auto-generated based on category and type:

- **Category codes:** SC (Science), EC (Economics), FC (Fiction), CH (Children), PD (Personal Development)
- **Type codes:** B (Book), M (Movie)
- **Format:** `{Category}{Type}{6-digit number}` — e.g., `FCB000001` (Fiction Book #1)
