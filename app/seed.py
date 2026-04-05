import sys
import os

# Add root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import Role, RoleType, Category, TransactionType


def seed():
    app = create_app()
    with app.app_context():

        # ── Seed Roles ──────────────────────────────────────
        if not Role.query.first():
            roles = [
                Role(name=RoleType.ADMIN, description="Full access to everything"),
                Role(name=RoleType.USER, description="Standard user access"),
            ]
            db.session.add_all(roles)
            db.session.commit()
            print("✅ Roles seeded")
        else:
            print("⏭️  Roles already exist, skipping...")

        # ── Seed Default Categories ─────────────────────────
        if not Category.query.first():
            categories = [
                # Income
                Category(
                    name="Salary",
                    type=TransactionType.INCOME,
                    icon="💼",
                    is_default=True,
                ),
                Category(
                    name="Freelance",
                    type=TransactionType.INCOME,
                    icon="💻",
                    is_default=True,
                ),
                Category(
                    name="Investment",
                    type=TransactionType.INCOME,
                    icon="📈",
                    is_default=True,
                ),
                Category(
                    name="Forex Trading",
                    type=TransactionType.INCOME,
                    icon="💹",
                    is_default=True,
                ),
                Category(
                    name="Other Income",
                    type=TransactionType.INCOME,
                    icon="💰",
                    is_default=True,
                ),
                # Expense
                Category(
                    name="Food",
                    type=TransactionType.EXPENSE,
                    icon="🍔",
                    is_default=True,
                ),
                Category(
                    name="Transport",
                    type=TransactionType.EXPENSE,
                    icon="🚗",
                    is_default=True,
                ),
                Category(
                    name="Shopping",
                    type=TransactionType.EXPENSE,
                    icon="🛍️",
                    is_default=True,
                ),
                Category(
                    name="Bills",
                    type=TransactionType.EXPENSE,
                    icon="📄",
                    is_default=True,
                ),
                Category(
                    name="Health",
                    type=TransactionType.EXPENSE,
                    icon="🏥",
                    is_default=True,
                ),
                Category(
                    name="Education",
                    type=TransactionType.EXPENSE,
                    icon="📚",
                    is_default=True,
                ),
                Category(
                    name="Other",
                    type=TransactionType.EXPENSE,
                    icon="📦",
                    is_default=True,
                ),
            ]
            db.session.add_all(categories)
            db.session.commit()
            print("✅ Default categories seeded")
        else:
            print("⏭️  Categories already exist, skipping...")

        print("🎉 Seeding complete!")


if __name__ == "__main__":
    seed()
