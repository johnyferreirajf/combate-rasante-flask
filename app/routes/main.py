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
    from app.models.team_member import TeamMember
    membros_db = TeamMember.query.filter_by(ativo=True).order_by(
        TeamMember.setor, TeamMember.ordem
    ).all()
    # Agrupar por setor
    setores = {}
    for m in membros_db:
        setores.setdefault(m.setor, []).append(m)
    return render_template("equipe.html", setores=setores)


@main_bp.route("/eventos")
def eventos():
    return render_template("eventos.html")


@main_bp.app_errorhandler(404)
def not_found(_error):
    return render_template("not_found.html"), 404


ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _build_dashboard_tree():
    """Busca no banco os arquivos do cliente logado (ClientFile), organizados por pasta."""
    from app.models.client_file import ClientFile
    user = get_current_user()
    if not user:
        return {}

    arquivos = ClientFile.query.filter_by(user_id=user.id).filter(
        ClientFile.url != "__folder__"
    ).order_by(ClientFile.folder_path, ClientFile.original_filename).all()

    # Monta árvore: pasta_raiz -> subpasta -> ... -> [arquivos]
    tree = {}
    for arq in arquivos:
        pasta = arq.folder_path or ""
        partes = pasta.split("/") if pasta else []

        node = tree
        for parte in partes:
            node.setdefault(parte, {})
            node = node[parte]

        node.setdefault("__files__", [])
        node["__files__"].append({
            "name": arq.display_name,
            "url":  arq.url,
            "id":   arq.id,
            "ext":  arq.file_ext or "",
            "size": arq.size_human,
        })

    return tree
