from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User, Role, RoleType, AuditLog
from datetime import datetime, timezone

auth_bp = Blueprint("auth", __name__)


# ============================================================
# SIGNUP
# ============================================================
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    # ── Already logged in → redirect to home ────────────────
    if current_user.is_authenticated:
        flash("You are already logged in.", "info")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # ── Validations ──────────────────────────────────────
        if not all([full_name, username, email, password, confirm_password]):
            flash("All fields are required.", "error")
            return redirect(url_for("auth.signup"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("auth.signup"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("auth.signup"))

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
            return redirect(url_for("auth.signup"))

        if User.query.filter_by(username=username).first():
            flash("This username is already taken.", "error")
            return redirect(url_for("auth.signup"))

        # ── RBAC: Admin override check ───────────────────────
        if User.check_admin_override(email):
            role = Role.query.filter_by(name=RoleType.ADMIN).first()
        else:
            role = Role.query.filter_by(name=RoleType.USER).first()

        # ── Create User ──────────────────────────────────────
        new_user = User(
            full_name=full_name,
            username=username,
            email=email,
            password=generate_password_hash(password),
            role_id=role.id,
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/signup.html")


# ============================================================
# LOGIN
# ============================================================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # ── Already logged in → redirect to home ────────────────
    if current_user.is_authenticated:
        flash("You are already logged in.", "info")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        # ── Validations ──────────────────────────────────────
        if not all([email, password]):
            flash("Email and password are required.", "error")
            return redirect(url_for("auth.login"))

        # ── Find User ────────────────────────────────────────
        user = User.query.filter_by(email=email).first()

        # ── Check credentials ────────────────────────────────
        if not user:
            flash("No account found with this email.", "error")
            return redirect(url_for("auth.login"))

        if not check_password_hash(user.password, password):
            flash("Incorrect password. Please try again.", "error")
            return redirect(url_for("auth.login"))

        if not user.is_active:
            flash("Your account has been deactivated. Contact support.", "error")
            return redirect(url_for("auth.login"))

        # ── Login user ───────────────────────────────────────
        login_user(user, remember=remember)

        # ── Update last login ────────────────────────────────
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()

        # ── Audit log ────────────────────────────────────────
        log = AuditLog(
            user_id=user.id,
            action="User logged in",
            module="auth",
            ip_address=request.remote_addr,
        )
        db.session.add(log)
        db.session.commit()

        flash(f"Welcome back, {user.full_name.split()[0]}! 👋", "success")

        # ── Redirect to next page or home ────────────────────
        next_page = request.args.get("next")
        return redirect(next_page) if next_page else redirect(url_for("main.index"))

    return render_template("auth/login.html")


# ============================================================
# LOGOUT
# ============================================================
@auth_bp.route("/logout")
@login_required
def logout():
    # ── Audit log ────────────────────────────────────────────
    log = AuditLog(
        user_id=current_user.id,
        action="User logged out",
        module="auth",
        ip_address=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()

    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("main.index"))
