from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv
import os

db            = SQLAlchemy()
migrate       = Migrate()
login_manager = LoginManager()
mail          = Mail()

login_manager.login_view             = 'auth.login'
login_manager.login_message          = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))


def seed_defaults(app):
    """
    Auto-seed roles & categories if they don't exist.
    Runs every time app starts.
    """
    with app.app_context():
        from app.models import Role, RoleType, Category, TransactionType

        # ── Seed Roles ───────────────────────────────────────
        if Role.query.count() == 0:
            roles = [
                Role(name=RoleType.ADMIN, description="Full access to everything"),
                Role(name=RoleType.USER,  description="Standard user access"),
            ]
            db.session.add_all(roles)
            db.session.commit()
            print("✅ [Startup] Roles seeded successfully")
        
        # ── Seed Categories ──────────────────────────────────
        if Category.query.count() == 0:
            categories = [
                # Income
                Category(name="Salary",        type=TransactionType.INCOME,  icon="💼", is_default=True),
                Category(name="Freelance",      type=TransactionType.INCOME,  icon="💻", is_default=True),
                Category(name="Investment",     type=TransactionType.INCOME,  icon="📈", is_default=True),
                Category(name="Forex Trading",  type=TransactionType.INCOME,  icon="💹", is_default=True),
                Category(name="Other Income",   type=TransactionType.INCOME,  icon="💰", is_default=True),
                # Expense
                Category(name="Food",           type=TransactionType.EXPENSE, icon="🍔", is_default=True),
                Category(name="Transport",      type=TransactionType.EXPENSE, icon="🚗", is_default=True),
                Category(name="Shopping",       type=TransactionType.EXPENSE, icon="🛍️", is_default=True),
                Category(name="Bills",          type=TransactionType.EXPENSE, icon="📄", is_default=True),
                Category(name="Health",         type=TransactionType.EXPENSE, icon="🏥", is_default=True),
                Category(name="Education",      type=TransactionType.EXPENSE, icon="📚", is_default=True),
                Category(name="Other",          type=TransactionType.EXPENSE, icon="📦", is_default=True),
            ]
            db.session.add_all(categories)
            db.session.commit()
            print("✅ [Startup] Categories seeded successfully")


def create_app():
    load_dotenv()
    app = Flask(__name__)

    # ── App Config ───────────────────────────────────────────
    app.config['SECRET_KEY']                  = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI']     = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ── Mail Config ──────────────────────────────────────────
    app.config['MAIL_SERVER']         = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT']           = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS']        = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME']       = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD']       = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

    # ── Init Extensions ──────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # ── Register Blueprints ──────────────────────────────────
    from app.routes import main
    app.register_blueprint(main)

    from app.auth import auth_bp
    app.register_blueprint(auth_bp)

    # ── Auto Seed Defaults on Startup ────────────────────────
    seed_defaults(app)

    return app