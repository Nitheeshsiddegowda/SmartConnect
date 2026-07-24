from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash

from db import query

bp = Blueprint("auth", __name__)


@bp.route("/", methods=["GET"])
def index():
    if "user_id" in session:
        return redirect(url_for(f"{session['role']}.dashboard"))
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for(f"{session['role']}.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role")

        user = query("SELECT * FROM users WHERE username=? AND role=?",
                      (username, role), one=True)

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html", role=role)

        if not user["is_active"]:
            flash("This account has been deactivated. Contact the admin office.", "error")
            return render_template("auth/login.html", role=role)

        session.clear()
        session["user_id"] = user["id"]
        session["role"] = user["role"]
        session["full_name"] = user["full_name"]
        flash(f"Welcome back, {user['full_name']}!", "success")
        return redirect(url_for(f"{role}.dashboard"))

    role = request.args.get("role", "student")
    return render_template("auth/login.html", role=role)


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
