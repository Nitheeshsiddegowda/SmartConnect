"""
utils/auth_helpers.py
----------------------
Lightweight session-based auth (no Flask-Login dependency needed).
On login we store user id/role/name in the Flask session cookie
(signed & tamper-proof by Flask's secret key).
"""
from functools import wraps
from flask import session, redirect, url_for, flash, g

from db import query


def current_user():
    if "user_id" not in session:
        return None
    if getattr(g, "_user_cache", None):
        return g._user_cache
    user = query("SELECT * FROM users WHERE id=?", (session["user_id"],), one=True)
    g._user_cache = user
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "error")
                return redirect(url_for("auth.login"))
            if session.get("role") not in roles:
                flash("You don't have access to that page.", "error")
                return redirect(url_for(f"{session.get('role')}.dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator
