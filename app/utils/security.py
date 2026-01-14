from functools import wraps
from flask import session, redirect, url_for, request, flash, current_app
from app.models import User
from app import db


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def get_current_user() -> User | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for("auth.login", next=request.path))
        admin_email = current_app.config.get("ADMIN_EMAIL")
        if not user.is_admin or (admin_email and user.email.lower() != admin_email.lower()):
            flash("Você não tem permissão para acessar esta página.", "error")
            return redirect(url_for("main.index"))
        return view(*args, **kwargs)
    return wrapped
