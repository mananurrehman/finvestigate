from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User, Role, RoleType, AuditLog
from datetime import datetime, timezone

auth_bp = Blueprint('auth', __name__)  # No prefix → keeps /signup, /login clean

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([full_name, username, email, password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('auth.signup'))
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.signup'))
        if User.query.filter((User.email == email) | (User.username == username)).first():
            flash('Email or username already exists.', 'error')
            return redirect(url_for('auth.signup'))

        # RBAC: Admin override
        if User.check_admin_override(email):
            role = Role.query.filter_by(name=RoleType.ADMIN).first()
        else:
            role = Role.query.filter_by(name=RoleType.USER).first()

        new_user = User(
            full_name=full_name,
            username=username,
            email=email,
            password=generate_password_hash(password),
            role_id=role.id
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()

            # Audit log
            log = AuditLog(user_id=user.id, action='User logged in', module='auth')
            db.session.add(log)
            db.session.commit()

            flash('Logged in successfully!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))