from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

from app.models import User, ContactMessage
from app import db
from app.utils.security import login_required, admin_required, get_current_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not email or not password:
            flash("Informe e-mail e senha.", "error")
            return redirect(url_for("auth.login"))

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("E-mail ou senha inválidos.", "error")
            return redirect(url_for("auth.login"))

        session["user_id"] = user.id

        # ✅ depois do login, manda pro painel certo
        next_url = request.args.get("next") or url_for("main.painel")
        return redirect(next_url)

    return render_template("login.html", current_user=get_current_user())


@auth_bp.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Você saiu da sessão com sucesso.", "success")
    return redirect(url_for("main.index"))


# ✅ Mantém compatibilidade se alguém acessar /dashboard via auth
@auth_bp.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("main.painel"))


@auth_bp.route("/admin", methods=["GET", "POST"])
@login_required
@admin_required
def admin():
    current_user_obj = get_current_user()
    created_user_email = None

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if not name:
            flash("Informe o nome do cliente.", "error")
            return redirect(url_for("auth.admin"))

        if not email:
            flash("Informe o e-mail do cliente.", "error")
            return redirect(url_for("auth.admin"))

        if not password:
            flash("Informe a senha.", "error")
            return redirect(url_for("auth.admin"))

        if len(password) < 6:
            flash("Senha deve ter pelo menos 6 caracteres.", "error")
            return redirect(url_for("auth.admin"))

        if password != confirm_password:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for("auth.admin"))

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Este e-mail já está cadastrado.", "error")
            return redirect(url_for("auth.admin"))

        new_user = User(name=name, email=email, is_admin=False)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        created_user_email = new_user.email
        flash(f"Cliente {new_user.email} criado com sucesso!", "success")
        return redirect(url_for("auth.admin"))

    return render_template(
        "admin.html",
        current_user=current_user_obj,
        created_user_email=created_user_email,
    )


# ✅ Mensagens do formulário de contato
@auth_bp.route("/admin/mensagens")
@login_required
@admin_required
def admin_mensagens():
    msgs = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template(
        "admin_mensagens.html",
        current_user=get_current_user(),
        msgs=msgs
    )
