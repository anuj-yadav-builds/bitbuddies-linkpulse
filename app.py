import hmac
import secrets

from flask import Flask, abort, g, jsonify, render_template, request, session
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Render puts our app behind a proxy; this makes https links and visitor IPs correct.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)

    from models import User

    # ---------- who is logged in, and the CSRF safety token ----------
    def csrf_token():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_hex(16)
        return session["_csrf"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def load_user():
        g.user = None
        user_id = session.get("uid")
        if user_id:
            try:
                g.user = db.session.get(User, user_id)
            except Exception:
                db.session.rollback()

    @app.before_request
    def check_csrf():
        if request.method == "POST":
            sent = request.form.get("csrf_token", "")
            expected = session.get("_csrf", "")
            if not expected or not hmac.compare_digest(sent, expected):
                abort(400)

    @app.context_processor
    def inject_user():
        return {"user": g.get("user")}

    # ---------- pages ----------
    # Every page function keeps the same name that Muskan's templates use in url_for().
    from views_admin import add_admin_views
    from views_auth import add_auth_views
    from views_campaigns import add_campaign_views
    from views_import import add_import_views
    from views_links import add_link_views
    from views_redirect import add_redirect_views

    add_auth_views(app)
    add_link_views(app)
    add_campaign_views(app)
    add_import_views(app)
    add_admin_views(app)
    add_redirect_views(app)  # keep last: it catches /<code>

    # Create the tables on first start (safe to run again and again).
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            app.logger.exception("Could not create tables. Check your DB_* settings.")

    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify(status="ok", database="connected")
        except Exception as err:
            return jsonify(status="error", database="not connected", detail=str(err)[:200]), 500

    # ---------- errors ----------
    @app.errorhandler(404)
    def not_found(_err):
        return render_template("status.html", kind="notfound"), 404

    @app.errorhandler(400)
    def bad_request(_err):
        return ("Your session expired or the form was not valid. "
                "Go back, refresh the page and try again."), 400

    @app.errorhandler(413)
    def too_big(_err):
        return "That file is too large (maximum 1 MB).", 413

    @app.errorhandler(500)
    def server_error(_err):
        db.session.rollback()
        return "Something went wrong on the server. Please try again.", 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
