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
def _is_image(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower()
    allowed = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", {"jpg", "jpeg", "png", "webp"})
    return ext in allowed


def _scan_client_photos(user_id: int):
    """
    Lê imagens do caminho:
      app/static/fotos_clientes/<user_id>/Safra.../Mes.../Data.../imagens

    Retorna estrutura:
      themes -> safra -> mes -> data -> [fotos]
    """
    photos_root = os.path.join(current_app.static_folder, "fotos_clientes", str(user_id))

    themes = {
        "Análise de Aplicação Aérea": defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    }

    if not os.path.isdir(photos_root):
        return themes

    # Safras
    for safra_name in sorted(os.listdir(photos_root)):
        safra_path = os.path.join(photos_root, safra_name)
        if not os.path.isdir(safra_path):
            continue

        # Meses
        for mes_name in sorted(os.listdir(safra_path)):
            mes_path = os.path.join(safra_path, mes_name)
            if not os.path.isdir(mes_path):
                continue

            # Datas
            for data_name in sorted(os.listdir(mes_path), reverse=True):
                data_path = os.path.join(mes_path, data_name)
                if not os.path.isdir(data_path):
                    continue

                # Fotos dentro da data
                files = sorted(os.listdir(data_path))
                for f in files:
                    if not _is_image(f):
                        continue

                    rel_url = f"fotos_clientes/{user_id}/{safra_name}/{mes_name}/{data_name}/{f}"
                    photo = {
                        "name": os.path.splitext(f)[0],
                        "url": url_for("static", filename=rel_url),
                    }
                    themes["Análise de Aplicação Aérea"][safra_name][mes_name][data_name].append(photo)

    return themes


@main_bp.route("/painel", methods=["GET", "POST"])
@login_required
def painel():
    """
    Painel do cliente:
      - (opcional) upload de fotos
      - exibição organizada por Tema -> Safra -> Mês -> Data
    """

    # ---------- Upload (opcional) ----------
    if request.method == "POST":
        file = request.files.get("image")
        if not file or file.filename == "":
            flash("Selecione uma imagem para enviar.", "error")
            return redirect(url_for("main.painel"))

        if not _is_image(file.filename):
            flash("Formato de imagem não permitido.", "error")
            return redirect(url_for("main.painel"))

        # Você pode mudar isso depois:
        safra_name = request.form.get("safra", "Safra 2025-2026").strip() or "Safra 2025-2026"
        mes_name = request.form.get("mes", "").strip()

        # Se não vier mês, gera automático: "01 - Janeiro"
        if not mes_name:
            meses = [
                "01 - Janeiro","02 - Fevereiro","03 - Março","04 - Abril","05 - Maio","06 - Junho",
                "07 - Julho","08 - Agosto","09 - Setembro","10 - Outubro","11 - Novembro","12 - Dezembro"
            ]
            mes_name = meses[datetime.utcnow().month - 1]

        data_name = request.form.get("data", "").strip()
        if not data_name:
            data_name = datetime.utcnow().strftime("%Y-%m-%d")

        base_path = os.path.join(
            current_app.static_folder,
            "fotos_clientes",
            str(current_user.id),
            safra_name,
            mes_name,
            data_name,
        )
        os.makedirs(base_path, exist_ok=True)

        safe_name = secure_filename(file.filename)
        filename = f"{int(datetime.utcnow().timestamp())}_{safe_name}"
        filepath = os.path.join(base_path, filename)

        file.save(filepath)

        flash("Foto enviada com sucesso.", "success")
        return redirect(url_for("main.painel"))

    # ---------- Montar painel ----------
    themes = _scan_client_photos(current_user.id)

    # Se tem algo dentro ou está vazio
    has_any = False
    for theme_name, safras in themes.items():
        for safra, meses in safras.items():
            for mes, datas in meses.items():
                for data, fotos in datas.items():
                    if fotos:
                        has_any = True
                        break

    return render_template(
        "dashboard.html",
        user=current_user,
        themes=themes,
        has_any=has_any,
    )
