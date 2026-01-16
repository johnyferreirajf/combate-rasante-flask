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

# O blueprint com o NOME que o app espera: main_bp
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
# Helpers (Painel)
# =========================

def _is_image_file(filename: str) -> bool:
    allowed = current_app.config.get(
        "ALLOWED_IMAGE_EXTENSIONS", {"jpg", "jpeg", "png", "webp"}
    )
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in allowed


def _safe_int(val: str):
    try:
        return int(val)
    except Exception:
        return 999999


def load_photos_hierarchy(user_id: int):
    """
    Lê o padrão de pastas:
      app/static/fotos_clientes/<user_id>/<TEMA>/<SAFRA>/<MES>/<DIA>/<arquivos>

    Retorna um dicionário:
      data[tema][safra][mes][dia] = [ {name, url}... ]
    """
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    base_root = os.path.join(current_app.static_folder, "fotos_clientes", str(user_id))
    if not os.path.isdir(base_root):
        return data  # vazio

    # Tema
    for tema in sorted(os.listdir(base_root)):
        tema_path = os.path.join(base_root, tema)
        if not os.path.isdir(tema_path):
            continue

        # Safra
        for safra in sorted(os.listdir(tema_path)):
            safra_path = os.path.join(tema_path, safra)
            if not os.path.isdir(safra_path):
                continue

            # Mês
            for mes in sorted(os.listdir(safra_path)):
                mes_path = os.path.join(safra_path, mes)
                if not os.path.isdir(mes_path):
                    continue

                # Dia
                dias = [d for d in os.listdir(mes_path) if os.path.isdir(os.path.join(mes_path, d))]
                dias_sorted = sorted(dias, key=_safe_int)

                for dia in dias_sorted:
                    dia_path = os.path.join(mes_path, dia)

                    # arquivos de imagem dentro do dia
                    files = []
                    for fname in sorted(os.listdir(dia_path)):
                        fpath = os.path.join(dia_path, fname)
                        if os.path.isfile(fpath) and _is_image_file(fname):
                            rel = f"fotos_clientes/{user_id}/{tema}/{safra}/{mes}/{dia}/{fname}"
                            files.append({
                                "name": os.path.splitext(fname)[0],
                                "url": url_for("static", filename=rel),
                            })

                    if files:
                        data[tema][safra][mes][dia] = files

    return data


def count_all_photos(data_hierarchy) -> int:
    total = 0
    for tema, safra_dict in data_hierarchy.items():
        for safra, mes_dict in safra_dict.items():
            for mes, dia_dict in mes_dict.items():
                for dia, photos in dia_dict.items():
                    total += len(photos)
    return total


# =========================
# Painel / Área do cliente
# =========================

@main_bp.route("/painel", methods=["GET", "POST"])
@login_required
def painel():
    """
    Painel do cliente:
      - exibição de fotos agrupadas por TEMA / SAFRA / MÊS / DIA
      - (upload pode ser feito depois com um form específico)
    """

    # ✅ Carrega as fotos no novo padrão de pastas
    photos_tree = load_photos_hierarchy(current_user.id)
    total_photos = count_all_photos(photos_tree)

    return render_template(
        "dashboard.html",
        user=current_user,
        photos_tree=photos_tree,
        total_photos=total_photos,
    )
