import os
from collections import defaultdict

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from app.utils.security import login_required, get_current_user
from app import db
from app.models import ContactMessage

# ✅ Blueprint TEM que vir antes das rotas
main_bp = Blueprint("main", __name__)


# =========================
# Rotas públicas do site
# =========================

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


# ✅ FORM envia para cá (POST)
@main_bp.route("/solicitar-orcamento", methods=["POST"])
def solicitar_orcamento():
    nome = (request.form.get("nome") or "").strip()
    email = (request.form.get("email") or "").strip()
    mensagem = (request.form.get("mensagem") or "").strip()

    if not nome or not email or not mensagem:
        flash("Preencha nome, e-mail e mensagem.", "error")
        return redirect(url_for("main.contato"))

    try:
        msg = ContactMessage(nome=nome, email=email, mensagem=mensagem)
        db.session.add(msg)
        db.session.commit()
        flash("Mensagem enviada com sucesso! ✅", "success")
    except Exception as e:
        db.session.rollback()
        print("ERRO AO SALVAR MENSAGEM:", str(e))
        flash("Não foi possível registrar sua mensagem agora. Tente novamente.", "error")

    return redirect(url_for("main.contato"))


# =========================
# Painel do Cliente
# =========================

def _is_image_file(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    return ext in {"jpg", "jpeg", "png", "webp"}


def _build_tree_for_dashboard(base_dir: str):
    """
    Estrutura esperada:

    app/static/fotos_clientes/<USER_ID>/<TEMA>/<SAFRA>/<MES>/<DIA>/<ARQUIVO>

    Exemplo:
    fotos_clientes/1/AplicacaoAerea/Safra2025-2026/Janeiro/14/analise_01.jpeg
    """

    tree = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    if not os.path.isdir(base_dir):
        return {}

    for tema in os.listdir(base_dir):
        tema_path = os.path.join(base_dir, tema)
        if not os.path.isdir(tema_path):
            continue

        for safra in os.listdir(tema_path):
            safra_path = os.path.join(tema_path, safra)
            if not os.path.isdir(safra_path):
                continue

            for mes in os.listdir(safra_path):
                mes_path = os.path.join(safra_path, mes)
                if not os.path.isdir(mes_path):
                    continue

                for dia in os.listdir(mes_path):
                    dia_path = os.path.join(mes_path, dia)
                    if not os.path.isdir(dia_path):
                        continue

                    files = [
                        f for f in os.listdir(dia_path)
                        if os.path.isfile(os.path.join(dia_path, f)) and _is_image_file(f)
                    ]

                    if not files:
                        continue

                    files.sort()

                    for f in files:
                        full_path = os.path.join(dia_path, f)
                        rel_path = os.path.relpath(full_path, current_app.static_folder).replace("\\", "/")

                        tree[tema][safra][mes][dia].append({
                            "url": url_for("static", filename=rel_path),
                            "name": os.path.splitext(f)[0]
                        })

    return tree


@main_bp.route("/painel")
@main_bp.route("/dashboard")
@login_required
def painel():
    user = get_current_user()

    # Raiz das fotos (dentro de app/static)
    photos_root = os.path.join(current_app.static_folder, "fotos_clientes", str(user.id))

    tree = _build_tree_for_dashboard(photos_root)

    tema_labels = {
        "AplicacaoAerea": "Aplicação Aérea",
        "AplicacaoTerrestre": "Aplicação Terrestre",
        "Plantio": "Plantio",
        "Colheita": "Colheita",
        "Outros": "Outros",
    }

    return render_template(
        "dashboard.html",
        tree=tree,
        tema_labels=tema_labels,
        current_user=user,
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

