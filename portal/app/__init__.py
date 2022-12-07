import os

from flask import Flask
from flask_compress import Compress
from flask_login import LoginManager
from flask_mail import Mail
from flask_rq import RQ
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from config import config as Config
import logging

logging.basicConfig(level=logging.INFO)

basedir = os.path.abspath(os.path.dirname(__file__))

mail = Mail()
db = SQLAlchemy()
csrf = CSRFProtect()
compress = Compress()

# Set up Flask-Login
login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_view = "account.login"


def create_app(config):
    app = Flask(__name__)
    config_name = config

    if not isinstance(config, str):
        config_name = os.getenv("FLASK_CONFIG", "default")

    app.config.from_object(Config[config_name])
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # not using sqlalchemy event system, hence disabling it

    Config[config_name].init_app(app)

    # Set up extensions
    mail.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    compress.init_app(app)
    RQ(app)

    # Register Jinja template functions
    from .lib.utils import register_template_utils

    register_template_utils(app)

    # Configure SSL if platform supports it
    if not app.debug and not app.testing and not app.config["SSL_DISABLE"]:
        from flask_sslify import SSLify

        SSLify(app)

    # Create app blueprints
    from .blueprints.main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    from .blueprints.account import account as account_blueprint

    app.register_blueprint(account_blueprint, url_prefix="/account")

    from .blueprints.admin import admin as admin_blueprint

    app.register_blueprint(admin_blueprint, url_prefix="/admin")

    from .blueprints.apps import apps as apps_blueprint

    app.register_blueprint(apps_blueprint, url_prefix="/apps")

    return app
