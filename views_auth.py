"""Register, login and logout pages."""
import re
import secrets

from flask import current_app, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import User
from utils import safe_next

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def add_auth_views(app):

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if g.user:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            name = request.form.get("name", "").strip()[:80]
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            problem = None
            if not name:
                problem = "Please enter your name."
            elif not EMAIL_RE.match(email) or len(email) > 120:
                problem = "Please enter a valid email."
            elif len(password) < 6:
                problem = "Password must be at least 6 characters."
            elif User.query.filter_by(email=email).first():
                problem = "That email is already registered. Please sign in."
            if problem:
                flash(problem, "danger")
                return render_template("register.html")

            admin_email = current_app.config["ADMIN_EMAIL"]
            if admin_email:
                role = "admin" if email == admin_email else "user"
            else:
                role = "admin" if User.query.count() == 0 else "user"

            db.session.add(User(
                name=name, email=email, role=role,
                password_hash=generate_password_hash(password, method="pbkdf2:sha256"),
            ))
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("That email is already registered. Please sign in.", "danger")
                return render_template("register.html")
            flash("Account created. Please sign in.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.user:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                admin_email = current_app.config["ADMIN_EMAIL"]
                if admin_email and email == admin_email and not user.is_admin:
                    user.role = "admin"
                    db.session.commit()
                session.clear()
                session["uid"] = user.id
                session["_csrf"] = secrets.token_hex(16)
                return redirect(safe_next(request.args.get("next")) or url_for("dashboard"))
            flash("Wrong email or password.", "danger")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))
