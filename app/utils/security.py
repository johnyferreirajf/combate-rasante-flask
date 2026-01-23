from functools import wraps
from flask import session, redirect, url_for, request, flash, current_app
from app.models import User, Employee


# =========================
# CLIENTE
# =========================
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
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None


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


# =========================
# FUNCIONÁRIOS
# =========================
def employee_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("employee_id"):
            return redirect(url_for("employee.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def get_current_employee() -> Employee | None:
    emp_id = session.get("employee_id")
    if not emp_id:
        return None
    try:
        return Employee.query.get(int(emp_id))
    except Exception:
        return None
