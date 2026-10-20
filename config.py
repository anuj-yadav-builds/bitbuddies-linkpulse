import os

from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()


def _is_true(name):
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def build_db_uri():
    # Only for quick lite testing, e.g. DATABASE_URL=sqlite:///lite.db
    override = os.getenv("DATABASE_URL", "").strip()
    if override:
        return override

    return URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "linkpulse"),
        query={"charset": "utf8mb4"},
    )


def build_engine_options(uri):
    if str(uri).startswith("sqlite"):
        return {}

    # Cloud databases close idle connections. These two lines stop
    # the "MySQL server has gone away" error.
    options = {"pool_pre_ping": True, "pool_recycle": 280}

    ssl_ca = os.getenv("DB_SSL_CA", "").strip()
    if ssl_ca:
        # Strict mode: path to the CA certificate file downloaded from Aiven
        options["connect_args"] = {"ssl": {"ca": ssl_ca}}
    elif _is_true("DB_SSL"):
        # Encrypted connection (what Aiven needs), no certificate file required
        options["connect_args"] = {"ssl": {"check_hostname": False}}
    return options


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    # The account with this email becomes the admin. If it is empty, the very
    # first person who registers becomes the admin.
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("BASE_URL", "").strip().startswith("https://")
    MAX_CONTENT_LENGTH = 1024 * 1024  # CSV uploads are limited to 1 MB
    SQLALCHEMY_DATABASE_URI = build_db_uri()
    SQLALCHEMY_ENGINE_OPTIONS = build_engine_options(SQLALCHEMY_DATABASE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BASE_URL = os.getenv("BASE_URL", "").strip().rstrip("/")
    TZ_OFFSET_MINUTES = int(os.getenv("TZ_OFFSET_MINUTES", "330"))
