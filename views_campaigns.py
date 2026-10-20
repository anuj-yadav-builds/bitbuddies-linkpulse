"""Campaigns page."""
from flask import flash, g, redirect, render_template, request, url_for

from extensions import db
from models import Campaign
from services import campaigns_as_dicts, login_required


def add_campaign_views(app):

    @app.route("/campaigns")
    @login_required
    def campaigns():
        return render_template("campaigns.html", campaigns=campaigns_as_dicts())

    @app.route("/campaigns/new", methods=["POST"])
    @login_required
    def new_campaign():
        name = request.form.get("name", "").strip()[:80]
        if not name:
            flash("Please enter a campaign name.", "danger")
        else:
            db.session.add(Campaign(name=name, user_id=g.user.id))
            db.session.commit()
            flash("Campaign created.", "success")
        return redirect(url_for("campaigns"))
