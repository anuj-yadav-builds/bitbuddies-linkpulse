"""Shared helpers used by all the view files."""
from datetime import datetime, time, timedelta
from functools import wraps
from urllib.parse import urlparse

from flask import abort, current_app, flash, g, redirect, request, url_for
from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from extensions import db
from models import BlockedDomain, Campaign, Click, Url
from utils import ALIAS_RE, RESERVED, generate_code, normalize_url, safe_next, utcnow


# ---------------------------------------------------------------- login
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("user") is None:
            target = request.full_path.rstrip("?") if request.method == "GET" else None
            return redirect(url_for("login", next=safe_next(target)))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not g.user.is_admin:
            flash("Only an administrator can open that page.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------- time
def tz_offset():
    return timedelta(minutes=current_app.config["TZ_OFFSET_MINUTES"])


def local_date_text(dt):
    return (dt + tz_offset()).strftime("%Y-%m-%d") if dt else "-"


# ---------------------------------------------------------------- links
def link_status(url, clicks):
    if url.disabled:
        return "disabled"
    if url.is_expired:
        return "expired"
    if url.click_limit and clicks >= url.click_limit:
        return "limit_reached"
    return "active"


def visible_urls():
    """Admin sees every link. A normal user sees only their own."""
    query = Url.query
    if not g.user.is_admin:
        query = query.filter(Url.user_id == g.user.id)
    return query.order_by(Url.created_at.desc(), Url.id.desc()).all()


def get_visible_url_or_404(code):
    url = Url.query.filter_by(code=code.lower()).first()
    if url is None or (not g.user.is_admin and url.user_id != g.user.id):
        abort(404)
    return url


def links_as_dicts(urls):
    """The exact shape Muskan's templates expect."""
    ids = [u.id for u in urls]
    stats = {}
    if ids:
        rows = (
            db.session.query(Click.url_id, func.count(Click.id),
                             func.count(func.distinct(Click.ip_hash)))
            .filter(Click.url_id.in_(ids))
            .group_by(Click.url_id)
            .all()
        )
        stats = {url_id: (total, unique) for url_id, total, unique in rows}

    camp_ids = {u.campaign_id for u in urls if u.campaign_id}
    names = {}
    if camp_ids:
        names = {c.id: c.name for c in Campaign.query.filter(Campaign.id.in_(camp_ids)).all()}

    result = []
    for u in urls:
        total, unique = stats.get(u.id, (0, 0))
        result.append({
            "id": u.id,
            "code": u.code,
            "url": u.original_url,
            "campaign": names.get(u.campaign_id, "-"),
            "clicks": total,
            "unique": unique,
            "status": link_status(u, total),
            "expires": local_date_text(u.expires_at),
            "tags": [t for t in (u.tags or "").split(",") if t],
        })
    return result


def campaigns_as_dicts():
    query = Campaign.query
    if not g.user.is_admin:
        query = query.filter(Campaign.user_id == g.user.id)
    campaigns = query.order_by(Campaign.created_at.desc(), Campaign.id.desc()).all()
    ids = [c.id for c in campaigns]
    link_counts, click_counts = {}, {}
    if ids:
        link_counts = dict(
            db.session.query(Url.campaign_id, func.count(Url.id))
            .filter(Url.campaign_id.in_(ids)).group_by(Url.campaign_id).all()
        )
        click_counts = dict(
            db.session.query(Url.campaign_id, func.count(Click.id))
            .join(Click, Click.url_id == Url.id)
            .filter(Url.campaign_id.in_(ids)).group_by(Url.campaign_id).all()
        )
    return [
        {"id": c.id, "name": c.name,
         "links": link_counts.get(c.id, 0), "clicks": click_counts.get(c.id, 0)}
        for c in campaigns
    ]


# ---------------------------------------------------------------- analytics
def daily_counts(days, url_ids, label_format="%a"):
    """Clicks per day for the last `days` days. Missing days are filled with 0."""
    offset = tz_offset()
    today = (utcnow() + offset).date()
    first_day = today - timedelta(days=days - 1)
    since_utc = datetime.combine(first_day, time.min) - offset

    buckets = {first_day + timedelta(days=i): 0 for i in range(days)}
    if url_ids:
        rows = (
            db.session.query(Click.clicked_at)
            .filter(Click.url_id.in_(url_ids), Click.clicked_at >= since_utc)
            .all()
        )
        for (clicked_at,) in rows:
            day = (clicked_at + offset).date()
            if day in buckets:
                buckets[day] += 1
    return [d.strftime(label_format) for d in buckets], list(buckets.values())


def breakdown(column, url_id, limit=6):
    n = func.count(Click.id)
    rows = (
        db.session.query(column, n).filter(Click.url_id == url_id)
        .group_by(column).order_by(desc(n)).limit(limit).all()
    )
    return {(name or "Unknown"): count for name, count in rows}


# ---------------------------------------------------------------- creating links
def is_blocked(url):
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    for (domain,) in db.session.query(BlockedDomain.domain).all():
        if host == domain or host.endswith("." + domain):
            return True
    return False


def parse_tags(raw):
    tags = []
    for part in (raw or "").split(","):
        tag = part.strip().lower()[:20]
        if tag and tag not in tags and "," not in tag:
            tags.append(tag)
    return ",".join(tags[:8])


def unique_code():
    length = 6
    for attempt in range(10):
        code = generate_code(length)
        if code not in RESERVED and not Url.query.filter_by(code=code).first():
            return code
        if attempt >= 4:
            length = 7
    raise RuntimeError("Could not generate a unique code")


def create_link(user, url, alias="", expires="", click_limit="", password="",
                campaign_id="", tags=""):
    """Validate everything and save one link. Returns (Url, None) or (None, message)."""
    try:
        original = normalize_url(url)
    except ValueError as err:
        return None, str(err)
    if is_blocked(original):
        return None, "This website is on the blocked list."
    if urlparse(original).netloc.lower() == request.host.lower():
        return None, "You cannot shorten a LinkPulse link again."

    alias = (alias or "").strip().lower()
    if alias:
        if not ALIAS_RE.match(alias):
            return None, "Alias must be 3-30 lowercase letters, numbers, - or _."
        if alias in RESERVED:
            return None, "That alias is reserved. Please pick another."
        if Url.query.filter_by(code=alias).first():
            return None, "That alias is already taken."
        code = alias
    else:
        code = unique_code()

    expires_at = None
    if (expires or "").strip():
        try:
            day = datetime.strptime(expires.strip(), "%Y-%m-%d")
        except ValueError:
            return None, "The expiry date is not valid."
        # the link works until the end of that day (India time)
        expires_at = datetime.combine(day.date(), time(23, 59, 59)) - tz_offset()

    limit = None
    if str(click_limit or "").strip():
        try:
            limit = int(click_limit)
            if limit < 1:
                raise ValueError
        except ValueError:
            return None, "Click limit must be a whole number, 1 or more."

    campaign = None
    if str(campaign_id or "").strip():
        try:
            campaign = db.session.get(Campaign, int(campaign_id))
        except ValueError:
            campaign = None
        if campaign is None or (not user.is_admin and campaign.user_id != user.id):
            return None, "That campaign was not found."

    link = Url(
        code=code,
        original_url=original,
        user_id=user.id,
        campaign_id=campaign.id if campaign else None,
        expires_at=expires_at,
        click_limit=limit,
        password_hash=(generate_password_hash(password, method="pbkdf2:sha256")
                       if password else None),
        tags=parse_tags(tags),
    )
    db.session.add(link)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, "That alias was just taken. Please try again."
    return link, None
