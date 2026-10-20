from extensions import db
from utils import utcnow


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")  # "user" or "admin"
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    @property
    def is_admin(self):
        return self.role == "admin"


class Campaign(db.Model):
    __tablename__ = "campaigns"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Url(db.Model):
    __tablename__ = "urls"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    original_url = db.Column(db.String(2048), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    click_limit = db.Column(db.Integer, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    disabled = db.Column(db.Boolean, nullable=False, default=False)
    tags = db.Column(db.String(255), nullable=False, default="")  # "sale,social"

    @property
    def is_expired(self):
        return self.expires_at is not None and utcnow() >= self.expires_at


class Click(db.Model):
    __tablename__ = "clicks"

    id = db.Column(db.Integer, primary_key=True)
    url_id = db.Column(
        db.Integer, db.ForeignKey("urls.id", ondelete="CASCADE"), nullable=False
    )
    clicked_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    ip_hash = db.Column(db.String(64))
    browser = db.Column(db.String(40))
    os_name = db.Column(db.String(40))
    device = db.Column(db.String(20))
    referrer = db.Column(db.String(255))
    src = db.Column(db.String(10))  # "qr" when the QR code was scanned

    __table_args__ = (db.Index("ix_clicks_url_time", "url_id", "clicked_at"),)


class BlockedDomain(db.Model):
    __tablename__ = "blocked_domains"

    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(120), unique=True, nullable=False)
