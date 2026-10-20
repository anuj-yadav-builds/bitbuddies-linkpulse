"""The public short link: /<code>. Redirects, counts the click, checks the rules."""
from flask import current_app, redirect, render_template, request
from werkzeug.security import check_password_hash

from extensions import db
from models import Click, Url
from utils import parse_user_agent, referrer_domain, visitor_hash


def log_click(url):
    """Save one row in the clicks table. A failure here must never stop the redirect."""
    try:
        ua = request.headers.get("User-Agent", "")
        browser, os_name, device = parse_user_agent(ua)
        db.session.add(Click(
            url_id=url.id,
            ip_hash=visitor_hash(request.remote_addr, ua, current_app.config["SECRET_KEY"]),
            browser=browser,
            os_name=os_name,
            device=device,
            referrer=referrer_domain(request.headers.get("Referer")),
            src="qr" if request.args.get("src") == "qr" else None,
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Could not save click")


def add_redirect_views(app):

    @app.route("/<code>", methods=["GET", "HEAD", "POST"])
    def go(code):
        url = Url.query.filter_by(code=code.lower()).first()
        if url is None:
            return render_template("status.html", kind="notfound"), 404
        if url.disabled:
            return render_template("status.html", kind="disabled"), 403
        if url.is_expired:
            return render_template("status.html", kind="expired"), 410
        if url.click_limit:
            used = Click.query.filter_by(url_id=url.id).count()
            if used >= url.click_limit:
                return render_template("status.html", kind="limit"), 410

        if url.password_hash:
            if request.method != "POST":
                return render_template("password.html", code=url.code, error=None)
            if not check_password_hash(url.password_hash, request.form.get("password", "")):
                return render_template("password.html", code=url.code,
                                       error="Wrong password. Please try again.")
        elif request.method == "POST":
            return redirect(request.path)

        if request.method != "HEAD":
            log_click(url)

        # 302 (temporary) so the browser asks us every time and every click is counted.
        return redirect(url.original_url, code=302)
