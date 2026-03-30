from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user, login_required
from app.models import Transaction, TransactionType, Category, Budget
from app import db
from datetime import datetime
from sqlalchemy import func, extract

main = Blueprint('main', __name__)


@main.route('/')
def index():
    return render_template('home.html')

@main.route('/about')
def about():
    return render_template('about.html')

@main.route('/how-to-use')
def how_to_use():
    return render_template('how_to_use.html')

@main.route('/contact')
def contact():
    return render_template('contact.html')


# ============================================================
# USER DASHBOARD
# ============================================================
@main.route('/dashboard')
@login_required
def dashboard():
    now   = datetime.now()
    month = now.month
    year  = now.year

    # ── This month transactions (current user only) ──────────
    monthly_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        extract('month', Transaction.date) == month,
        extract('year',  Transaction.date) == year
    ).order_by(Transaction.date.desc()).all()

    # ── Income this month ────────────────────────────────────
    income = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type    == TransactionType.INCOME,
        extract('month', Transaction.date) == month,
        extract('year',  Transaction.date) == year
    ).scalar()

    # ── Expenses this month ──────────────────────────────────
    expenses = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type    == TransactionType.EXPENSE,
        extract('month', Transaction.date) == month,
        extract('year',  Transaction.date) == year
    ).scalar()

    # ── Balance ──────────────────────────────────────────────
    balance = income - expenses

    # ── Recent 5 transactions ────────────────────────────────
    recent_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.date.desc()).limit(5).all()

    # ── Expenses by category (for chart) ────────────────────
    category_expenses = db.session.query(
        Category.name,
        Category.icon,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction, Transaction.category_id == Category.id)\
     .filter(
        Transaction.user_id == current_user.id,
        Transaction.type    == TransactionType.EXPENSE,
        extract('month', Transaction.date) == month,
        extract('year',  Transaction.date) == year
     ).group_by(Category.name, Category.icon)\
      .order_by(func.sum(Transaction.amount).desc())\
      .all()

    # ── Categories for modal ─────────────────────────────────
    income_categories  = Category.query.filter_by(
        type=TransactionType.INCOME
    ).all()
    expense_categories = Category.query.filter_by(
        type=TransactionType.EXPENSE
    ).all()

    # ── Chart data ───────────────────────────────────────────
    chart_labels  = [row.name         for row in category_expenses]
    chart_amounts = [float(row.total) for row in category_expenses]

    return render_template(
        'dashboard.html',
        income              = income,
        expenses            = expenses,
        balance             = balance,
        recent_transactions = recent_transactions,
        category_expenses   = category_expenses,
        income_categories   = income_categories,
        expense_categories  = expense_categories,
        chart_labels        = chart_labels,
        chart_amounts       = chart_amounts,
        current_month       = now.strftime('%B %Y'),
        currency            = current_user.currency_preference,
        now = now
    )

# ============================================================
# ADD TRANSACTION
# ============================================================
@main.route('/dashboard/add-transaction', methods=['POST'])
@login_required
def add_transaction():
    title       = request.form.get('title', '').strip()
    amount      = request.form.get('amount')
    txn_type    = request.form.get('type')
    category_id = request.form.get('category_id')
    date_str    = request.form.get('date')
    note        = request.form.get('note', '').strip()

    # ── Validations ──────────────────────────────────────────
    if not all([title, amount, txn_type, date_str]):
        flash('Please fill all required fields.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        amount   = float(amount)
        txn_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid amount or date.', 'error')
        return redirect(url_for('main.dashboard'))

    if amount <= 0:
        flash('Amount must be greater than 0.', 'error')
        return redirect(url_for('main.dashboard'))

    txn_type_enum = (
        TransactionType.INCOME
        if txn_type == 'income'
        else TransactionType.EXPENSE
    )

    # ── Save Transaction ─────────────────────────────────────
    txn = Transaction(
        title       = title,
        amount      = amount,
        type        = txn_type_enum,
        category_id = int(category_id) if category_id else None,
        date        = txn_date,
        note        = note if note else None,
        user_id     = current_user.id
    )
    db.session.add(txn)
    db.session.commit()

    flash(f'Transaction "{title}" added successfully! ✅', 'success')
    return redirect(url_for('main.dashboard'))