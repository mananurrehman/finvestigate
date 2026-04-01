import pytest
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import User, Role, RoleType, Category, Transaction, TransactionType
from datetime import date


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "ci-test-secret-key",
    })

    with app.app_context():
        db.create_all()
        _seed_roles()
        _seed_categories()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_in_client(app, client):
    """Creates a test user and logs them in."""
    with app.app_context():
        role = Role.query.filter_by(name=RoleType.USER).first()
        user = User(
            full_name="Test User",
            username="testuser",
            email="test@example.com",
            password=generate_password_hash("TestPass123"),
            currency_preference="PKR",
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()

    client.post("/login", data={
        "email": "test@example.com",
        "password": "TestPass123",
    }, follow_redirects=True)

    return client


def _seed_roles():
    if Role.query.first():
        return
    roles = [
        Role(name=RoleType.USER, description="Regular user"),
        Role(name=RoleType.ADMIN, description="Admin user"),
    ]
    db.session.add_all(roles)
    db.session.commit()


def _seed_categories():
    if Category.query.first():
        return
    categories = [
        Category(name="Salary", icon="💼", type=TransactionType.INCOME, is_default=True),
        Category(name="Food", icon="🍔", type=TransactionType.EXPENSE, is_default=True),
    ]
    db.session.add_all(categories)
    db.session.commit()


# ============================================================
# PUBLIC ROUTES
# ============================================================

class TestPublicRoutes:

    def test_home_page(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_about_page(self, client):
        response = client.get("/about")
        assert response.status_code == 200

    def test_how_to_use_page(self, client):
        response = client.get("/how-to-use")
        assert response.status_code == 200

    def test_contact_page(self, client):
        response = client.get("/contact")
        assert response.status_code == 200


# ============================================================
# AUTH PROTECTION
# ============================================================

class TestAuthProtection:

    def test_dashboard_requires_login(self, client):
        response = client.get("/dashboard")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_transactions_requires_login(self, client):
        response = client.get("/transactions")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_add_transaction_requires_login(self, client):
        response = client.post("/dashboard/add-transaction", data={})
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_delete_transaction_requires_login(self, client):
        response = client.post("/transactions/delete/1")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ============================================================
# DASHBOARD
# ============================================================

class TestDashboard:

    def test_dashboard_loads_for_logged_in_user(self, logged_in_client):
        response = logged_in_client.get("/dashboard")
        assert response.status_code == 200

    def test_dashboard_shows_current_month(self, logged_in_client):
        response = logged_in_client.get("/dashboard")
        assert response.status_code == 200


# ============================================================
# ADD TRANSACTION
# ============================================================

class TestAddTransaction:

    def _get_category_id(self, app, txn_type):
        with app.app_context():
            return Category.query.filter_by(type=txn_type).first().id

    def test_add_income_transaction(self, app, logged_in_client):
        category_id = self._get_category_id(app, TransactionType.INCOME)
        response = logged_in_client.post("/dashboard/add-transaction", data={
            "title": "Monthly Salary",
            "amount": "50000",
            "type": "income",
            "category_id": category_id,
            "date": "2025-01-15",
            "note": "January salary",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"added successfully" in response.data

    def test_add_expense_transaction(self, app, logged_in_client):
        category_id = self._get_category_id(app, TransactionType.EXPENSE)
        response = logged_in_client.post("/dashboard/add-transaction", data={
            "title": "Groceries",
            "amount": "2000",
            "type": "expense",
            "category_id": category_id,
            "date": "2025-01-16",
            "note": "",
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_add_transaction_missing_fields(self, logged_in_client):
        response = logged_in_client.post("/dashboard/add-transaction", data={
            "title": "",
            "amount": "",
            "type": "income",
            "date": "",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"required fields" in response.data

    def test_add_transaction_negative_amount(self, logged_in_client):
        response = logged_in_client.post("/dashboard/add-transaction", data={
            "title": "Bad Entry",
            "amount": "-500",
            "type": "expense",
            "date": "2025-01-16",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"greater than 0" in response.data

    def test_add_transaction_invalid_amount(self, logged_in_client):
        response = logged_in_client.post("/dashboard/add-transaction", data={
            "title": "Bad Entry",
            "amount": "abc",
            "type": "expense",
            "date": "2025-01-16",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"Invalid amount" in response.data


# ============================================================
# TRANSACTIONS LIST
# ============================================================

class TestTransactionsList:

    def test_transactions_page_loads(self, logged_in_client):
        response = logged_in_client.get("/transactions")
        assert response.status_code == 200

    def test_transactions_filter_by_type(self, logged_in_client):
        response = logged_in_client.get("/transactions?type=income")
        assert response.status_code == 200

    def test_transactions_search(self, logged_in_client):
        response = logged_in_client.get("/transactions?search=salary")
        assert response.status_code == 200

    def test_transactions_pagination(self, logged_in_client):
        response = logged_in_client.get("/transactions?page=1")
        assert response.status_code == 200


# ============================================================
# EDIT TRANSACTION
# ============================================================

class TestEditTransaction:

    def _create_transaction(self, app):
        with app.app_context():
            user = User.query.filter_by(email="test@example.com").first()
            category = Category.query.filter_by(type=TransactionType.EXPENSE).first()
            txn = Transaction(
                title="Old Title",
                amount=1000,
                type=TransactionType.EXPENSE,
                category_id=category.id,
                date=date(2025, 1, 10),
                user_id=user.id,
            )
            db.session.add(txn)
            db.session.commit()
            return txn.id

    def test_edit_transaction_success(self, app, logged_in_client):
        txn_id = self._create_transaction(app)
        with app.app_context():
            category_id = Category.query.filter_by(
                type=TransactionType.EXPENSE
            ).first().id

        response = logged_in_client.post(f"/transactions/edit/{txn_id}", data={
            "title": "Updated Title",
            "amount": "1500",
            "type": "expense",
            "category_id": category_id,
            "date": "2025-01-12",
            "note": "updated note",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"updated successfully" in response.data

    def test_edit_transaction_not_owned_by_user(self, app, logged_in_client):
        with app.app_context():
            role = Role.query.filter_by(name=RoleType.USER).first()
            other_user = User(
                full_name="Other User",
                username="otheruser",
                email="other@example.com",
                password=generate_password_hash("OtherPass123"),
                currency_preference="PKR",
                role_id=role.id,
            )
            db.session.add(other_user)
            db.session.commit()

            category = Category.query.filter_by(type=TransactionType.EXPENSE).first()
            txn = Transaction(
                title="Other's Transaction",
                amount=500,
                type=TransactionType.EXPENSE,
                category_id=category.id,
                date=date(2025, 1, 5),
                user_id=other_user.id,
            )
            db.session.add(txn)
            db.session.commit()
            txn_id = txn.id

        response = logged_in_client.post(f"/transactions/edit/{txn_id}", data={
            "title": "Hacked",
            "amount": "999",
            "type": "expense",
            "date": "2025-01-05",
        })
        assert response.status_code == 404


# ============================================================
# DELETE TRANSACTION
# ============================================================

class TestDeleteTransaction:

    def _create_transaction(self, app):
        with app.app_context():
            user = User.query.filter_by(email="test@example.com").first()
            category = Category.query.filter_by(type=TransactionType.EXPENSE).first()
            txn = Transaction(
                title="To Be Deleted",
                amount=300,
                type=TransactionType.EXPENSE,
                category_id=category.id,
                date=date(2025, 1, 8),
                user_id=user.id,
            )
            db.session.add(txn)
            db.session.commit()
            return txn.id

    def test_delete_transaction_success(self, app, logged_in_client):
        txn_id = self._create_transaction(app)
        response = logged_in_client.post(
            f"/transactions/delete/{txn_id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"deleted successfully" in response.data

    def test_delete_transaction_not_owned_by_user(self, app, logged_in_client):
        with app.app_context():
            role = Role.query.filter_by(name=RoleType.USER).first()
            other_user = User(
                full_name="Another User",
                username="anotheruser",
                email="another@example.com",
                password=generate_password_hash("AnotherPass123"),
                currency_preference="PKR",
                role_id=role.id,
            )
            db.session.add(other_user)
            db.session.commit()

            category = Category.query.filter_by(type=TransactionType.EXPENSE).first()
            txn = Transaction(
                title="Not Mine",
                amount=100,
                type=TransactionType.EXPENSE,
                category_id=category.id,
                date=date(2025, 1, 3),
                user_id=other_user.id,
            )
            db.session.add(txn)
            db.session.commit()
            txn_id = txn.id

        response = logged_in_client.post(f"/transactions/delete/{txn_id}")
        assert response.status_code == 404