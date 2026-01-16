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
# Helpers (Tema / Safra / Mês)
# =========================

MESES_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def calcular_safra(dt):
    """
    Safra padrão:
      - Jul a Dez: safra = ano/ano+1
      - Jan a Jun: safra = ano-1/ano
    Pasta usa hífen porque Windows não aceita "/"
    """
    if dt.month >= 7:
        return f"Safra {dt.year}-{dt.year + 1}"
    return f"Safra {dt.year - 1}-{dt.year}"


def nome_mes(dt):
    return MESES_PT.get(dt.month, str(dt.month))


def carregar_painel_arquivos_por_pastas(user_id):
    """
    Lê as fotos organizadas assim:
    static/fotos_clientes/<user_id>/<Tema>/<Safra>/<Mes>/<Data>/arquivos...

    Retorna:
    painel[tema][safra][mes] = [
      {"date": "YYYY-MM-DD", "photos": [{"name":..., "url":...}, ...]},
      ...
    ]
    """

    base_dir = os.path.join(current_app.static_folder, "fotos_clientes", str(user_id))
    painel = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    if not os.path.exists(base_dir):
        return painel

    # Tema
    temas = sorted(
        [t for t in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, t))]
    )

    for tema in temas:
        tema_path = os.path.join(base_dir, tema)

        # Safra
        safras = sorted(
            [s for s in os.listdir(tema_path) if os.path.isdir(os.path.join(tema_path, s))]
        )

        for safra in safras:
            safra_path = os.path.join(tema_path, safra)

            # Mês
            meses = sorted(
                [m for m in os.listdir(safra_path) if os.path.isdir(os.path.join(safra_path, m))]
            )

            for mes in meses:
                mes_path = os.path.join(safra_path, mes)

                # Datas
                datas = sorted(
                    [d for d in os.listdir(mes_path) if os.path.isdir(os.path.join(mes_path, d))],
                    reverse=True
                )

                for data in datas:
                    data_path = os.path.join(mes_path, data)

                    fotos = []
                    for f in sorted(os.listdir(data_path)):
                        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                            url = f"/static/fotos_clientes/{user_id}/{tema}/{safra}/{mes}/{data}/{f}"
                            fotos.append({"name": f, "url": url})

                    if fotos:
                        painel[tema][safra][mes].append({
                            "date": data,
                            "photos": fotos
                        })

    return painel


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
      - exibição organizada por:
          Tema -> Safra -> Mês -> Data -> Fotos
    """

    # ---------- Upload de fotos ----------
    if request.method == "POST":
        file = request.files.get("image")
        date_str = request.form.get("taken_at", "").strip()

        if not file or file.filename == "":
            flash("Selecione uma imagem para enviar.", "error")
            return redirect(url_for("main.painel"))

        ext = file.filename.rsplit(".", 1)[-1].lower()
        allowed = current_app.config.get(
            "ALLOWED_IMAGE_EXTENSIONS", {"jpg", "jpeg", "png", "webp"}
        )
        if ext not in allowed:
            flash("Formato de imagem não permitido.", "error")
            return redirect(url_for("main.painel"))

        # data informada (ou hoje, se der erro)
        try:
            taken_at = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            taken_at = datetime.utcnow()

        # ✅ Tema fixo por enquanto (você pode criar outros depois)
        tema = "AplicacaoAerea"

        safra = calcular_safra(taken_at)
        mes = nome_mes(taken_at)
        data_folder = taken_at.strftime("%Y-%m-%d")

        # ✅ Pasta destino:
        # static/fotos_clientes/<id>/<tema>/<safra>/<mes>/<data>/
        dest_dir = os.path.join(
            current_app.static_folder,
            "fotos_clientes",
            str(current_user.id),
            tema,
            safra,
            mes,
            data_folder,
        )
        os.makedirs(dest_dir, exist_ok=True)

        safe_name = secure_filename(file.filename)
        filename = f"{int(datetime.utcnow().timestamp())}_{safe_name}"
        filepath = os.path.join(dest_dir, filename)

        file.save(filepath)

        flash("Análise enviada com sucesso!", "success")
        return redirect(url_for("main.painel"))

    # ---------- Carregar painel organizado ----------
    painel = carregar_painel_arquivos_por_pastas(current_user.id)

    # Métricas (placeholder)
    metrics = {
        "total_aplicacoes": 3,
        "area_total": 355.50,
        "media_cobertura": 98.7,
    }

    aplicacoes_recentes = []

    return render_template(
        "dashboard.html",
        user=current_user,
        metrics=metrics,
        aplicacoes_recentes=aplicacoes_recentes,
        painel=painel,
    )
