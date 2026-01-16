import os
from datetime import datetime
from collections import defaultdict

from flask import (
    Blueprint,
    render_template,
    current_app,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import Photo


main_bp = Blueprint("main", __name__)


# =========================
# Rotas públicas do site
# =========================
@main_bp.route("/")
def index():
    return render_template("home.html")


@main_bp.route("/servicos")
def servicos():
    return render_template("servicos.html")


@main_bp.route("/tecnologia")
def tecnologia():
    return render_template("tecnologia.html")


@main_bp.route("/contato", methods=["GET", "POST"])
def contato():
    if request.method == "POST":
        flash("Mensagem recebida! Em breve entraremos em contato.", "success")
        return redirect(url_for("main.contato"))

    return render_template("contato.html")


# =========================
# Painel / Área do cliente
# =========================
@main_bp.route("/painel", methods=["GET", "POST"])
@login_required
def painel():
    """
    Painel do cliente:
      - Exibe as análises do usuário por pastas:
        TEMA -> SAFRA -> MÊS -> DIA -> FOTOS
      Caminho:
        app/static/fotos_clientes/<user_id>/<tema>/<safra>/<mes>/<dia>/arquivos
    """

    # ----- Pasta raíz do cliente -----
    client_root = os.path.join(
        current_app.static_folder,
        "fotos_clientes",
        str(current_user.id)
    )

    allowed_ext = {"jpg", "jpeg", "png", "webp"}  # ✅ pega .jpeg sim

    # Estrutura final:
    # {
    #   "AplicacaoAerea": {
    #       "Safra 2025-2026": {
    #           "Janeiro": {
    #               "15": [ {name,url}, ... ]
    #           }
    #       }
    #   }
    # }
    tree = {}

    if os.path.isdir(client_root):
        temas = sorted(
            [d for d in os.listdir(client_root) if os.path.isdir(os.path.join(client_root, d))],
            key=lambda x: x.lower()
        )

        for tema in temas:
            tema_path = os.path.join(client_root, tema)

            safras = sorted(
                [d for d in os.listdir(tema_path) if os.path.isdir(os.path.join(tema_path, d))],
                key=lambda x: x.lower()
            )

            for safra in safras:
                safra_path = os.path.join(tema_path, safra)

                meses = sorted(
                    [d for d in os.listdir(safra_path) if os.path.isdir(os.path.join(safra_path, d))],
                    key=lambda x: x.lower()
                )

                for mes in meses:
                    mes_path = os.path.join(safra_path, mes)

                    dias = sorted(
                        [d for d in os.listdir(mes_path) if os.path.isdir(os.path.join(mes_path, d))],
                        key=lambda x: x.lower()
                    )

                    for dia in dias:
                        dia_path = os.path.join(mes_path, dia)

                        files = []
                        for f in sorted(os.listdir(dia_path), key=lambda x: x.lower()):
                            full = os.path.join(dia_path, f)
                            if not os.path.isfile(full):
                                continue

                            ext = f.rsplit(".", 1)[-1].lower()
                            if ext not in allowed_ext:
                                continue

                            rel_path = os.path.relpath(full, current_app.static_folder).replace("\\", "/")
                            files.append({
                                "name": f,
                                "url": url_for("static", filename=rel_path)
                            })

                        if files:
                            tree.setdefault(tema, {}).setdefault(safra, {}).setdefault(mes, {})[dia] = files

    # Um "nome bonito" para o tema (opcional)
    tema_labels = {
        "AplicacaoAerea": "Aplicação Aérea",
        "AplicacaoTerrestre": "Aplicação Terrestre",
        "Drone": "Drone",
    }

    return render_template(
        "dashboard.html",
        user=current_user,
        tree=tree,
        tema_labels=tema_labels
    )
