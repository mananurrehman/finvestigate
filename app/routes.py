from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from app.models import Transaction, TransactionType, Category, Budget
from app import db
from datetime import datetime
from sqlalchemy import func, extract, or_

main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("home.html")


@main.route("/about")
def about():
    return render_template("about.html")


@main.route("/how-to-use")
def how_to_use():
    return render_template("how_to_use.html")


@main.route("/contact")
def contact():
    return render_template("contact.html")


# ============================================================
# USER DASHBOARD
# ============================================================
@main.route("/dashboard")
@login_required
def dashboard():
    now = datetime.now()
    month = now.month
    year = now.year

    monthly_transactions = (
        Transaction.query.filter(
            Transaction.user_id == current_user.id,
            extract("month", Transaction.date) == month,
            extract("year", Transaction.date) == year,
        )
        .order_by(Transaction.date.desc())
        .all()
    )

    income = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.type == TransactionType.INCOME,
            extract("month", Transaction.date) == month,
            extract("year", Transaction.date) == year,
        )
        .scalar()
    )

    expenses = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.type == TransactionType.EXPENSE,
            extract("month", Transaction.date) == month,
            extract("year", Transaction.date) == year,
        )
        .scalar()
    )

    balance = income - expenses

    recent_transactions = (
        Transaction.query.filter(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.desc())
        .limit(5)
        .all()
    )

    category_expenses = (
        db.session.query(
            Category.name, Category.icon, func.sum(Transaction.amount).label("total")
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.type == TransactionType.EXPENSE,
            extract("month", Transaction.date) == month,
            extract("year", Transaction.date) == year,
        )
        .group_by(Category.name, Category.icon)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    income_categories = Category.query.filter_by(type=TransactionType.INCOME).all()
    expense_categories = Category.query.filter_by(type=TransactionType.EXPENSE).all()

    chart_labels = [row.name for row in category_expenses]
    chart_amounts = [float(row.total) for row in category_expenses]

    return render_template(
        "dashboard.html",
        income=income,
        expenses=expenses,
        balance=balance,
        recent_transactions=recent_transactions,
        category_expenses=category_expenses,
        income_categories=income_categories,
        expense_categories=expense_categories,
        chart_labels=chart_labels,
        chart_amounts=chart_amounts,
        current_month=now.strftime("%B %Y"),
        currency=current_user.currency_preference,
        now=now,
    )


# ============================================================
# ADD TRANSACTION
# ============================================================
@main.route("/dashboard/add-transaction", methods=["POST"])
@login_required
def add_transaction():
    title = request.form.get("title", "").strip()
    amount = request.form.get("amount")
    txn_type = request.form.get("type")
    category_id = request.form.get("category_id")
    date_str = request.form.get("date")
    note = request.form.get("note", "").strip()

    if not all([title, amount, txn_type, date_str]):
        flash("Please fill all required fields.", "error")
        return redirect(url_for("main.dashboard"))

    try:
        amount = float(amount)
        txn_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid amount or date.", "error")
        return redirect(url_for("main.dashboard"))

    if amount <= 0:
        flash("Amount must be greater than 0.", "error")
        return redirect(url_for("main.dashboard"))

    txn_type_enum = (
        TransactionType.INCOME if txn_type == "income" else TransactionType.EXPENSE
    )

    txn = Transaction(
        title=title,
        amount=amount,
        type=txn_type_enum,
        category_id=int(category_id) if category_id else None,
        date=txn_date,
        note=note if note else None,
        user_id=current_user.id,
    )
    db.session.add(txn)
    db.session.commit()

    flash(f'Transaction "{title}" added successfully! ✅', "success")
    return redirect(url_for("main.transactions"))


# ============================================================
# TRANSACTIONS LIST
# ============================================================
@main.route("/transactions")
@login_required
def transactions():
    page = request.args.get("page", 1, type=int)
    per_page = 10

    # ── Filters ──────────────────────────────────────────────
    filter_type = request.args.get("type", "all")
    filter_category = request.args.get("category", "all")
    filter_month = request.args.get("month", "all")
    search_query = request.args.get("search", "").strip()

    # ── Base Query ───────────────────────────────────────────
    query = Transaction.query.filter(Transaction.user_id == current_user.id)

    # ── Apply Filters ────────────────────────────────────────
    if filter_type == "income":
        query = query.filter(Transaction.type == TransactionType.INCOME)
    elif filter_type == "expense":
        query = query.filter(Transaction.type == TransactionType.EXPENSE)

    if filter_category != "all":
        query = query.filter(Transaction.category_id == int(filter_category))

    if filter_month != "all":
        try:
            month_date = datetime.strptime(filter_month, "%Y-%m")
            query = query.filter(
                extract("month", Transaction.date) == month_date.month,
                extract("year", Transaction.date) == month_date.year,
            )
        except ValueError:
            pass

    if search_query:
        query = query.filter(
            or_(
                Transaction.title.ilike(f"%{search_query}%"),
                Transaction.note.ilike(f"%{search_query}%"),
            )
        )

    # ── Summary (filtered) ───────────────────────────────────
    filtered_income = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == TransactionType.INCOME,
    )
    filtered_expense = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == TransactionType.EXPENSE,
    )

    # Apply same filters to summary
    if filter_month != "all":
        try:
            month_date = datetime.strptime(filter_month, "%Y-%m")
            filtered_income = filtered_income.filter(
                extract("month", Transaction.date) == month_date.month,
                extract("year", Transaction.date) == month_date.year,
            )
            filtered_expense = filtered_expense.filter(
                extract("month", Transaction.date) == month_date.month,
                extract("year", Transaction.date) == month_date.year,
            )
        except ValueError:
            pass

    total_income = filtered_income.scalar()
    total_expenses = filtered_expense.scalar()

    # ── Paginate ─────────────────────────────────────────────
    paginated = query.order_by(
        Transaction.date.desc(), Transaction.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    # ── Categories for filter dropdown & modal ───────────────
    all_categories = Category.query.all()
    income_categories = Category.query.filter_by(type=TransactionType.INCOME).all()
    expense_categories = Category.query.filter_by(type=TransactionType.EXPENSE).all()

    # ── Available months (for filter) ────────────────────────
    months = (
        db.session.query(func.to_char(Transaction.date, "YYYY-MM").label("month"))
        .filter(Transaction.user_id == current_user.id)
        .distinct()
        .order_by(func.to_char(Transaction.date, "YYYY-MM").desc())
        .all()
    )

    return render_template(
        "transactions.html",
        transactions=paginated,
        total_income=total_income,
        total_expenses=total_expenses,
        all_categories=all_categories,
        income_categories=income_categories,
        expense_categories=expense_categories,
        filter_type=filter_type,
        filter_category=filter_category,
        filter_month=filter_month,
        search_query=search_query,
        currency=current_user.currency_preference,
        months=months,
        now=datetime.now(),
    )


# ============================================================
# EDIT TRANSACTION
# ============================================================
@main.route("/transactions/edit/<int:txn_id>", methods=["POST"])
@login_required
def edit_transaction(txn_id):
    txn = Transaction.query.filter_by(id=txn_id, user_id=current_user.id).first_or_404()

    title = request.form.get("title", "").strip()
    amount = request.form.get("amount")
    txn_type = request.form.get("type")
    category_id = request.form.get("category_id")
    date_str = request.form.get("date")
    note = request.form.get("note", "").strip()

    if not all([title, amount, txn_type, date_str]):
        flash("Please fill all required fields.", "error")
        return redirect(url_for("main.transactions"))

    try:
        amount = float(amount)
        txn_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid amount or date.", "error")
        return redirect(url_for("main.transactions"))

    if amount <= 0:
        flash("Amount must be greater than 0.", "error")
        return redirect(url_for("main.transactions"))

    txn.title = title
    txn.amount = amount
    txn.type = (
        TransactionType.INCOME if txn_type == "income" else TransactionType.EXPENSE
    )
    txn.category_id = int(category_id) if category_id else None
    txn.date = txn_date
    txn.note = note if note else None
    txn.updated_at = datetime.now()

    db.session.commit()
    flash(f'Transaction "{title}" updated successfully! ✅', "success")
    return redirect(url_for("main.transactions"))


# ============================================================
# DELETE TRANSACTION
# ============================================================
@main.route("/transactions/delete/<int:txn_id>", methods=["POST"])
@login_required
def delete_transaction(txn_id):
    txn = Transaction.query.filter_by(id=txn_id, user_id=current_user.id).first_or_404()

    title = txn.title
    db.session.delete(txn)
    db.session.commit()

    flash(f'Transaction "{title}" deleted successfully!', "success")
    return redirect(url_for("main.transactions"))
