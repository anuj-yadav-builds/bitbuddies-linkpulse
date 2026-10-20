"""Admin page: all links, enable/disable a link, blocked domains."""
from flask import flash, redirect, render_template, request, url_for

from extensions import db
from models import BlockedDomain, Url
from services import admin_required, get_visible_url_or_404, links_as_dicts, visible_urls
from utils import clean_domain


def add_admin_views(app):

    @app.route("/admin")
    @admin_required
    def admin():
        blocked = [b.domain for b in BlockedDomain.query.order_by(BlockedDomain.domain).all()]
        return render_template("admin.html", links=links_as_dicts(visible_urls()),
                               blocklist=blocked)

    @app.route("/links/<code>/toggle", methods=["POST"])
    @admin_required
    def toggle_link(code):
        url = get_visible_url_or_404(code)
        url.disabled = not url.disabled
        db.session.commit()
        state = "disabled" if url.disabled else "active again"
        flash(f"/{url.code} is now {state}.", "success")
        return redirect(request.referrer or url_for("admin"))

    @app.route("/admin/blocklist", methods=["POST"])
    @admin_required
    def add_blocklist():
        domain = clean_domain(request.form.get("domain", ""))
        if not domain:
            flash("Please enter a valid domain like bad-site.com", "danger")
        elif BlockedDomain.query.filter_by(domain=domain).first():
            flash("That domain is already blocked.", "info")
        else:
            db.session.add(BlockedDomain(domain=domain))
            db.session.commit()
            flash("Domain blocked.", "success")
        return redirect(url_for("admin"))
