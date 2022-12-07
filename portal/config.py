import os
import urllib.parse


basedir = os.path.abspath(os.path.dirname(__file__))

if os.path.exists("config.env"):
    print("Importing environment from .env file")
    for line in open("config.env"):
        var = line.strip().split("=")
        if len(var) == 2:
            os.environ[var[0]] = var[1].replace('"', "")


class Config:
    APP_NAME = os.environ.get("APP_NAME", "Topiaas")
    if os.environ.get("SECRET_KEY"):
        SECRET_KEY = os.environ.get("SECRET_KEY")
    else:
        SECRET_KEY = "SECRET_KEY_ENV_VAR_NOT_SET"
        print("SECRET KEY ENV VAR NOT SET! SHOULD NOT SEE IN PRODUCTION")
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Email
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.sendgrid.net")
    MAIL_PORT = os.environ.get("MAIL_PORT", 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", True)
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", False)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")

    # Database
    DATABASE_USER = os.environ.get("DATABASE_USER")
    DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD")
    DATABASE_SERVICE_NAME = os.environ.get("DATABASE_SERVICE_NAME")
    DATABASE_PORT = os.environ.get("DATABASE_PORT", 5432)
    DEFAULT_DATABASE_URI = f"postgres://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_SERVICE_NAME}:{DATABASE_PORT}/postgresdb"

    # Analytics
    GOOGLE_ANALYTICS_ID = os.environ.get("GOOGLE_ANALYTICS_ID", "")
    SEGMENT_API_KEY = os.environ.get("SEGMENT_API_KEY", "")

    # Admin account
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "flask-base-admin@example.com")
    EMAIL_SUBJECT_PREFIX = "[{}]".format(APP_NAME)
    EMAIL_SENDER = "{app_name} Admin <{email}>".format(
        app_name=APP_NAME, email=MAIL_USERNAME
    )

    REDIS_URL = os.getenv("REDISTOGO_URL", "http://redis:6379")

    RAYGUN_APIKEY = os.environ.get("RAYGUN_APIKEY")

    # Parse the REDIS_URL to set RQ config variables
    urllib.parse.uses_netloc.append("redis")
    url = urllib.parse.urlparse(REDIS_URL)

    RQ_DEFAULT_HOST = url.hostname
    RQ_DEFAULT_PORT = url.port
    RQ_DEFAULT_PASSWORD = url.password
    RQ_DEFAULT_DB = 0

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    ASSETS_DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DEV_DATABASE_URL", Config.DEFAULT_DATABASE_URI
    )

    @classmethod
    def init_app(cls, app):
        print(
            "THIS APP IS IN DEBUG MODE. \
                YOU SHOULD NOT SEE THIS IN PRODUCTION."
        )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL", Config.DEFAULT_DATABASE_URI
    )
    WTF_CSRF_ENABLED = False

    @classmethod
    def init_app(cls, app):
        print(
            "THIS APP IS IN TESTING MODE.  \
                YOU SHOULD NOT SEE THIS IN PRODUCTION."
        )


class ProductionConfig(Config):
    DEBUG = False
    USE_RELOADER = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", Config.DEFAULT_DATABASE_URI
    )
    SSL_DISABLE = os.environ.get("SSL_DISABLE", "True") == "True"

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        assert os.environ.get("SECRET_KEY"), "SECRET_KEY IS NOT SET!"


class UnixConfig(ProductionConfig):
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # Log to syslog
        import logging
        from logging.handlers import SysLogHandler

        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
    "unix": UnixConfig,
}
