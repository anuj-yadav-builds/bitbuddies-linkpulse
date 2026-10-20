"""Dashboard, links list, new link, link details and analytics."""
from flask import flash, g, jsonify, redirect, render_template, request, url_for

from models import Click, Url
from services import (breakdown, campaigns_as_dicts, create_link, daily_counts,
                      get_visible_url_or_404, is_blocked, links_as_dicts, login_required,
                      visible_urls)
from utils import RESERVED


def add_link_views(app):

    @app.route("/")
    @login_required
    def dashboard():
        urls = visible_urls()
        links = links_as_dicts(urls)
        labels, values = daily_counts(7, [u.id for u in urls])
        stats = {
            "links": len(links),
            "clicks": sum(l["clicks"] for l in links),
            "active": len([l for l in links if l["status"] == "active"]),
            "alerts": len([l for l in links if l["status"] != "active"]),
            "daily_labels": labels,
            "daily_values": values,
        }
        return render_template("dashboard.html", links=links,
                               campaigns=campaigns_as_dicts(), stats=stats)

    @app.route("/links")
    @login_required
    def links():
        return render_template("links.html", links=links_as_dicts(visible_urls()))

    @app.route("/links/new", methods=["GET", "POST"])
    @login_required
    def new_link():
        if request.method == "POST":
            link, error = create_link(
                g.user,
                url=request.form.get("url", ""),
                alias=request.form.get("alias", ""),
                expires=request.form.get("expires", ""),
                click_limit=request.form.get("click_limit", ""),
                password=request.form.get("password", ""),
                campaign_id=request.form.get("campaign", ""),
                tags=request.form.get("tags", ""),
            )
            if error:
                flash(error, "danger")
                return redirect(url_for("new_link"))
            flash("Link created.", "success")
            return redirect(url_for("link_detail", code=link.code))
        return render_template("new_link.html", campaigns=campaigns_as_dicts())

    @app.route("/api/check-alias")
    def check_alias():
        if not g.user:
            return jsonify(available=False, message="Please sign in first"), 401
        alias = request.args.get("alias", "").strip().lower()
        if alias in RESERVED:
            return jsonify(available=False, message="This alias is reserved")
        if Url.query.filter_by(code=alias).first():
            return jsonify(available=False, message="Alias already taken")
        return jsonify(available=True, message="Alias is available")

    @app.route("/api/check-url")
    def check_url():
        if not g.user:
            return jsonify(safe=False, message="Please sign in first"), 401
        url = request.args.get("url", "")
        if is_blocked(url if "://" in url else "https://" + url):
            return jsonify(safe=False, message="This website is on the blocked list.")
        return jsonify(safe=True, message="OK")

    @app.route("/links/<code>")
    @login_required
    def link_detail(code):
        url = get_visible_url_or_404(code)
        return render_template("link_detail.html", link=links_as_dicts([url])[0])

    @app.route("/links/<code>/analytics")
    @login_required
    def analytics(code):
        url = get_visible_url_or_404(code)
        labels, values = daily_counts(14, [url.id], label_format="%d %b")
        stats = {
            "daily_labels": labels,
            "daily_values": values,
            "devices": breakdown(Click.device, url.id),
            "browsers": breakdown(Click.browser, url.id),
            "referrers": breakdown(Click.referrer, url.id),
        }
        return render_template("analytics.html", link=links_as_dicts([url])[0], stats=stats)

