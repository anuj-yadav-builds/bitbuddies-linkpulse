import hashlib
import re
import secrets
import string
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import render_template
from jinja2 import TemplateNotFound

# Codes are always lowercase. MySQL treats "Abc" and "abc" as the same
# value, so keeping everything lowercase avoids confusing clashes.
ALPHABET = string.ascii_lowercase + string.digits
ALIAS_RE = re.compile(r"^[a-z0-9_-]{3,30}$")
# Words that are real pages of the site. They can never be used as a short code.
RESERVED = {
    "login", "logout", "register", "dashboard", "links", "new", "campaigns",
    "import", "admin", "api", "static", "preview", "health", "analytics",
    "favicon.ico", "robots.txt",
}


def utcnow():
    """Current UTC time (without timezone info, which is what MySQL stores)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_code(length=6):
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def normalize_url(raw):
    """Clean the link the user typed. Raises ValueError with a friendly message."""
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Please enter a link.")
    if len(raw) > 2048:
        raise ValueError("That link is too long (maximum 2048 characters).")
    if re.search(r"\s", raw):
        raise ValueError("A link cannot contain spaces.")
    if not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", raw):
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw) and "." not in raw.split("/")[0]:
            raise ValueError("Only http:// and https:// links are allowed.")
        raw = "https://" + raw

    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http:// and https:// links are allowed.")
    try:
        host = parsed.hostname
        parsed.port  # raises ValueError if the port is not a number
    except ValueError:
        raise ValueError("That does not look like a valid link.")
    if not host or "." not in host or parsed.username:
        raise ValueError("That does not look like a valid link.")
    return raw


def parse_user_agent(ua):
    """Very small User-Agent reader: returns (browser, os_name, device)."""
    if not ua:
        return "Unknown", "Unknown", "Unknown"
    low = ua.lower()

    bot_words = ("bot", "crawl", "spider", "slurp", "preview", "whatsapp",
                 "facebookexternalhit", "curl", "python-urllib", "wget")
    if any(w in low for w in bot_words):
        return "Bot", "Bot", "Bot"

    # Order matters: Edge and Opera also say "Chrome", Chrome also says "Safari".
    if "edg/" in low or "edge/" in low:
        browser = "Edge"
    elif "opr/" in low or "opera" in low:
        browser = "Opera"
    elif "samsungbrowser" in low:
        browser = "Samsung Internet"
    elif "firefox" in low or "fxios" in low:
        browser = "Firefox"
    elif "chrome" in low or "crios" in low:
        browser = "Chrome"
    elif "safari" in low:
        browser = "Safari"
    elif "msie" in low or "trident" in low:
        browser = "Internet Explorer"
    else:
        browser = "Other"

    if "windows" in low:
        os_name = "Windows"
    elif "android" in low:
        os_name = "Android"
    elif "iphone" in low or "ipad" in low or "ipod" in low:
        os_name = "iOS"
    elif "mac os x" in low or "macintosh" in low:
        os_name = "macOS"
    elif "cros" in low:
        os_name = "ChromeOS"
    elif "linux" in low:
        os_name = "Linux"
    else:
        os_name = "Other"

    if "ipad" in low or "tablet" in low or ("android" in low and "mobile" not in low):
        device = "Tablet"
    elif "mobi" in low or "iphone" in low or "android" in low:
        device = "Mobile"
    else:
        device = "Desktop"

    return browser, os_name, device


def referrer_domain(referrer):
    if not referrer:
        return "Direct"
    host = urlparse(referrer).hostname
    if not host:
        return "Direct"
    if host.startswith("www."):
        host = host[4:]
    return host[:255]


def visitor_hash(ip, ua, secret):
    """Anonymous visitor id. We never store the real IP address."""
    return hashlib.sha256(f"{secret}|{ip}|{ua}".encode("utf-8")).hexdigest()


def safe_next(target):
    """Only allow redirects to a page inside our own site."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


def clean_domain(raw):
    """'https://www.Bad-Site.com/x' -> 'bad-site.com'. Returns '' if it is not a domain."""
    raw = (raw or "").strip().lower()
    if "://" in raw:
        raw = urlparse(raw).hostname or ""
    raw = raw.split("/")[0].split(":")[0]
    if raw.startswith("www."):
        raw = raw[4:]
    if re.match(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$", raw):
        return raw
    return ""


def render_or_text(template, fallback_text, status=200, **context):
    """Show the frontend template; if Muskan's file is not added yet, show plain text."""
    try:
        return render_template(template, **context), status
    except TemplateNotFound:
        return fallback_text, status
