from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from app.config import config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))


def create_app(config_name="production", test_config=None):
    app = Flask(__name__)

    # Load config class by name
    app.config.from_object(config[config_name])

    # Override with test config dict if provided (used by pytest)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app import models
    from app.routes import main
    app.register_blueprint(main)

    from app.auth import auth_bp
    app.register_blueprint(auth_bp)

    return app