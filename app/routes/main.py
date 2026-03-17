import os
from collections import defaultdict

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from app import db
from app.models import ContactMessage
from app.utils.security import login_required, get_current_user

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("home_stream.html")


@main_bp.route("/servicos")
def servicos():
    return render_template("servicos.html")


@main_bp.route("/tecnologia")
def tecnologia():
    return render_template("tecnologia.html")


@main_bp.route("/contato", methods=["GET"])
def contato():
    return render_template("contato.html")


@main_bp.route("/solicitar-orcamento", methods=["POST"])
def solicitar_orcamento():
    nome = (request.form.get("nome") or "").strip()
    email = (request.form.get("email") or "").strip()
    telefone = (request.form.get("telefone") or "").strip()
    mensagem = (request.form.get("mensagem") or "").strip()

    if not nome or not email or not mensagem:
        flash("Preencha nome, e-mail e mensagem.", "error")
        return redirect(url_for("main.contato"))

    mensagem_final = mensagem
    if telefone:
        mensagem_final = f"Telefone: {telefone}\n\n{mensagem}"

    contato = ContactMessage(nome=nome, email=email, mensagem=mensagem_final)
    db.session.add(contato)
    db.session.commit()

    flash("Mensagem enviada com sucesso!", "success")
    return redirect(url_for("main.contato"))


@main_bp.route("/painel")
@login_required
def painel():
    tree = _build_dashboard_tree()
    tema_labels = {
        "aplicacoes": "Aplicações",
        "mapas": "Mapas",
        "relatorios": "Relatórios",
        "fotos": "Fotos",
        "outros": "Outros",
    }
    return render_template(
        "dashboard.html",
        current_user=get_current_user(),
        tree=tree,
        tema_labels=tema_labels,
    )


@main_bp.route("/atividades")
def atividades():
    return render_template("atividades.html")


@main_bp.route("/clientes")
def clientes():
    return render_template("clientes.html")


@main_bp.route("/parcerias")
def parcerias():
    return render_template("parcerias.html")


@main_bp.route("/equipe")
def equipe():
    return render_template("equipe.html")


@main_bp.route("/eventos")
def eventos():
    return render_template("eventos.html")


@main_bp.app_errorhandler(404)
def not_found(_error):
    return render_template("not_found.html"), 404


ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _build_dashboard_tree():
    """Lê app/static/uploads no padrão tema/safra/mes/dia/arquivo."""
    uploads_root = current_app.config.get("UPLOAD_FOLDER")
    if not uploads_root or not os.path.isdir(uploads_root):
        return {}

    tree = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    for root, _dirs, files in os.walk(uploads_root):
        rel_root = os.path.relpath(root, uploads_root)
        if rel_root == ".":
            continue

        parts = [p for p in rel_root.replace("\\", "/").split("/") if p]
        tema = parts[0] if len(parts) > 0 else "outros"
        safra = parts[1] if len(parts) > 1 else "Sem safra"
        mes = parts[2] if len(parts) > 2 else "Sem mês"
        dia = parts[3] if len(parts) > 3 else "Sem dia"

        for filename in sorted(files):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                continue

            rel_file = os.path.join(rel_root, filename).replace("\\", "/")
            url = url_for("static", filename=f"uploads/{rel_file}")
            tree[tema][safra][mes][dia].append({"name": filename, "url": url})

    # ordena internamente mantendo dicts simples para o template
    ordered_tree = {}
    for tema in sorted(tree.keys()):
        ordered_tree[tema] = {}
        for safra in sorted(tree[tema].keys()):
            ordered_tree[tema][safra] = {}
            for mes in sorted(tree[tema][safra].keys()):
                ordered_tree[tema][safra][mes] = {}
                for dia in sorted(tree[tema][safra][mes].keys()):
                    ordered_tree[tema][safra][mes][dia] = tree[tema][safra][mes][dia]
    return ordered_tree
