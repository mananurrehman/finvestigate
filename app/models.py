import os
from app import db
from datetime import datetime, timezone
from enum import Enum as PyEnum
from flask_login import UserMixin

# ============================================================
# ENUMS
# ============================================================


class RoleType(PyEnum):
    ADMIN = "admin"
    USER = "user"


class TransactionType(PyEnum):
    INCOME = "income"
    EXPENSE = "expense"


# ============================================================
# TABLE 1: ROLES
# ============================================================


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Enum(RoleType), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    users = db.relationship("User", back_populates="role", lazy=True)

    def __repr__(self):
        return f"<Role {self.name}>"


# ============================================================
# TABLE 2: USERS
# ============================================================


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)  # unique = one owner
    password = db.Column(db.String(255), nullable=False)  # always hashed
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    currency_preference = db.Column(db.String(3), default="PKR", nullable=False)

    # RBAC
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("Role", back_populates="users")

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    transactions = db.relationship(
        "Transaction", back_populates="user", lazy=True, cascade="all, delete-orphan"
    )
    budgets = db.relationship(
        "Budget", back_populates="user", lazy=True, cascade="all, delete-orphan"
    )
    audit_logs = db.relationship(
        "AuditLog", back_populates="user", lazy=True, cascade="all, delete-orphan"
    )

    # ── RBAC Helper Properties ──────────────────────────────
    @property
    def is_admin(self):
        return self.role.name == RoleType.ADMIN

    @property
    def is_user(self):
        return self.role.name == RoleType.USER

    # ── Admin Check (called during registration) ────────────
    @staticmethod
    def check_admin_override(email: str) -> bool:
        """
        Called during signup only.
        Reads ADMIN_EMAIL from .env
        Never hardcoded. Never exposed.
        """
        admin_email = os.getenv("ADMIN_EMAIL", "")
        return email.strip().lower() == admin_email.strip().lower()

    def __repr__(self):
        return f"<User {self.username} | Role: {self.role.name}>"


# ============================================================
# TABLE 3: CATEGORIES
# ============================================================


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Enum(TransactionType), nullable=False)
    icon = db.Column(db.String(10), nullable=True)
    is_default = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    transactions = db.relationship("Transaction", back_populates="category", lazy=True)

    def __repr__(self):
        return f"<Category {self.name} | {self.type}>"


# ============================================================
# TABLE 4: TRANSACTIONS
# ============================================================


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    type = db.Column(db.Enum(TransactionType), nullable=False)
    note = db.Column(db.Text, nullable=True)
    date = db.Column(
        db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date()
    )

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", back_populates="transactions")
    category = db.relationship("Category", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction {self.title} | {self.type} | {self.amount}>"


# ============================================================
# TABLE 5: BUDGETS
# ============================================================


class Budget(db.Model):
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    alert_at = db.Column(db.Integer, default=80)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="budgets")

    def __repr__(self):
        return f"<Budget {self.title} | {self.month}/{self.year} | {self.amount}>"


# ============================================================
# TABLE 6: AUDIT LOGS
# ============================================================


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(200), nullable=False)
    module = db.Column(db.String(100), nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} | User: {self.user_id}>"
