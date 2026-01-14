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
# Painel / Área do cliente
# =========================


@main_bp.route("/painel", methods=["GET", "POST"])
@login_required
def painel():
    """
    Painel do cliente:
      - upload de fotos
      - exibição de fotos agrupadas por data (dia/mês/ano)
      - métricas simples de exemplo
    """

    # ---------- Upload de fotos ----------
    if request.method == "POST":
        file = request.files.get("image")
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        date_str = request.form.get("taken_at", "").strip()

        if not file or file.filename == "":
            flash("Selecione uma imagem para enviar.", "error")
            return redirect(url_for("main.painel"))

        # extensão permitida
        ext = file.filename.rsplit(".", 1)[-1].lower()
        allowed = current_app.config.get(
            "ALLOWED_IMAGE_EXTENSIONS", {"jpg", "jpeg", "png", "webp"}
        )
        if ext not in allowed:
            flash("Formato de imagem não permitido.", "error")
            return redirect(url_for("main.painel"))

        # data informada (ou hoje, se der erro)
        try:
            taken_at = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            taken_at = datetime.utcnow().date()

        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)

        safe_name = secure_filename(file.filename)
        filename = f"{int(datetime.utcnow().timestamp())}_{safe_name}"
        filepath = os.path.join(upload_folder, filename)

        file.save(filepath)

        photo = Photo(
            filename=filename,
            title=title or None,
            description=description or None,
            taken_at=taken_at,
        )
        db.session.add(photo)
        db.session.commit()

        flash("Foto enviada com sucesso.", "success")
        return redirect(url_for("main.painel"))

    # ---------- Carregar fotos e agrupar por data ----------
    photos = Photo.query.order_by(Photo.taken_at.desc(), Photo.created_at.desc()).all()

    grouped = defaultdict(list)
    for p in photos:
        label = p.taken_at.strftime("%d/%m/%Y")
        grouped[label].append(p)

    photos_by_date = [
        {"label": date_label, "items": items}
        for date_label, items in sorted(grouped.items(), reverse=True)
    ]

    # Métricas de exemplo (depois você pode ligar em dados reais)
    metrics = {
        "total_aplicacoes": 3,
        "area_total": 355.50,
        "media_cobertura": 98.7,
    }

    aplicacoes_recentes = []  # placeholder

    return render_template(
        "dashboard.html",
        user=current_user,
        metrics=metrics,
        aplicacoes_recentes=aplicacoes_recentes,
        photos_by_date=photos_by_date,
    )
