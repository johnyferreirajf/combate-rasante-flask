import os
from collections import defaultdict

from flask import abort, Blueprint, render_template, request, redirect, url_for, flash, current_app, Response, stream_with_context

from app import db
from app.models import ContactMessage
from app.utils.security import login_required, get_current_user

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    ultimo_titulo = None
    ultimo_data   = None
    ultimo_thumb  = None
    try:
        from app.models.post import Post
        post = (Post.query
                .filter_by(ativo=True)
                .order_by(Post.created_at.desc())
                .first())
        if post:
            ultimo_titulo = post.titulo
            ultimo_data   = post.created_at.strftime("%d/%m/%Y")
            # Tentar foto primeiro
            foto = next((m for m in post.midias if m.tipo == "foto"), None)
            if foto:
                ultimo_thumb = foto.url
            else:
                # Vídeo direto do Cloudinary (tipo="vid") — gerar thumbnail
                vid = next((m for m in post.midias if m.tipo == "vid"), None)
                if vid and vid.url:
                    ultimo_thumb = vid.url.replace(
                        "/video/upload/", "/video/upload/f_jpg,so_0/"
                    ).rsplit(".", 1)[0] + ".jpg"
    except Exception:
        pass
    return render_template("home_stream.html",
                           ultimo_titulo=ultimo_titulo,
                           ultimo_data=ultimo_data,
                           ultimo_thumb=ultimo_thumb)


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
    from app.models.sector_order import SectorOrder
    from collections import OrderedDict

    # Buscar ordem dos setores do banco (igual ao admin)
    ordem_db = {r.setor: r.posicao for r in SectorOrder.query.order_by(SectorOrder.posicao).all()}

    membros_db = TeamMember.query.filter_by(ativo=True).filter(
        ~TeamMember.nome.startswith("__setor__")
    ).order_by(TeamMember.ordem).all()

    membros_db.sort(key=lambda m: (ordem_db.get(m.setor, 999), m.ordem))

    setores = OrderedDict()
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


@main_bp.route("/painel/trocar-senha", methods=["GET", "POST"])
@login_required
def painel_trocar_senha():
    user = get_current_user()
    if request.method == "POST":
        atual    = request.form.get("senha_atual")    or ""
        nova     = request.form.get("nova_senha")     or ""
        confirma = request.form.get("confirmar")      or ""

        if not user.check_password(atual):
            flash("Senha atual incorreta.", "error")
            return redirect(url_for("main.painel_trocar_senha"))
        if len(nova) < 6:
            flash("A nova senha deve ter pelo menos 6 caracteres.", "error")
            return redirect(url_for("main.painel_trocar_senha"))
        if nova != confirma:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for("main.painel_trocar_senha"))

        user.set_password(nova)
        from app import db
        db.session.commit()
        flash("Senha alterada com sucesso!", "success")
        return redirect(url_for("main.painel_trocar_senha"))

    return render_template("painel_trocar_senha.html", current_user=user)


@main_bp.route("/painel/download/<int:file_id>")
@login_required
def painel_download(file_id):
    """Proxy de download — baixa via servidor e força Content-Disposition: attachment."""
    import urllib.request
    import re
    from flask import make_response, stream_with_context, Response
    from app.models.client_file import ClientFile

    user = get_current_user()
    cf = ClientFile.query.get_or_404(file_id)

    if cf.user_id != user.id:
        abort(403)

    # Montar nome do arquivo para download
    name = cf.original_filename or cf.title or "arquivo"
    ext  = (cf.file_ext or "").lower()
    if ext and not name.lower().endswith(f".{ext}"):
        name = f"{name}.{ext}"
    # Remover caracteres problemáticos para headers HTTP
    safe_name = re.sub(r'[\x00-\x1f"\\]', "", name).strip() or "arquivo"

    try:
        req = urllib.request.Request(
            cf.url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "*/*",
            }
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "application/octet-stream")

        r = make_response(data)
        r.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{urllib.request.quote(safe_name)}"
        r.headers["Content-Type"] = ctype
        r.headers["Content-Length"] = str(len(data))
        r.headers["Cache-Control"] = "no-store"
        r.headers["X-Content-Type-Options"] = "nosniff"
        return r

    except Exception as e:
        current_app.logger.error(f"painel_download error: {e}")
        # Último recurso: redirecionar direto para a URL
        return redirect(cf.url)



@main_bp.route("/painel/download-pasta")
@login_required
def painel_download_pasta():
    """Baixa todos os arquivos de uma pasta como ZIP."""
    import zipfile, tempfile, urllib.request as _ur
    from flask import make_response
    from app.models.client_file import ClientFile

    user = get_current_user()
    pasta = (request.args.get("path") or "").strip("/")

    # Buscar arquivos da pasta e subpastas
    prefixo = pasta + "/" if pasta else ""
    todos = ClientFile.query.filter_by(user_id=user.id).filter(
        ClientFile.url != "__folder__"
    ).all()

    itens = [f for f in todos if
             f.folder_path == pasta or
             (pasta == "" and not f.folder_path) or
             (f.folder_path or "").startswith(prefixo)]

    if not itens:
        flash("Nenhum arquivo encontrado nesta pasta.", "error")
        return redirect(url_for("main.painel"))

    zip_name = (pasta.split("/")[-1] if pasta else "arquivos") + ".zip"
    tmpdir   = tempfile.mkdtemp()
    zip_path = f"{tmpdir}/{zip_name}"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for cf in itens:
            filename = cf.original_filename or cf.title or "arquivo"
            ext = cf.file_ext or ""
            if ext and not filename.lower().endswith(f".{ext.lower()}"):
                filename = f"{filename}.{ext}"

            # Subcaminho relativo à pasta selecionada
            fp = cf.folder_path or ""
            if pasta and fp.startswith(pasta):
                rel = fp[len(pasta):].strip("/")
            else:
                rel = fp
            arc_name = f"{rel}/{filename}".strip("/") if rel else filename

            try:
                req = _ur.Request(cf.url, headers={"User-Agent": "Mozilla/5.0"})
                with _ur.urlopen(req, timeout=20) as resp:
                    zf.writestr(arc_name, resp.read())
            except Exception:
                pass

    with open(zip_path, "rb") as f:
        data = f.read()

    r = make_response(data)
    r.headers["Content-Disposition"] = f"attachment; filename=\"{zip_name}\""
    r.headers["Content-Type"] = "application/zip"
    r.headers["Content-Length"] = str(len(data))
    return r


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

@main_bp.route("/api/chatbot", methods=["POST"])
def chatbot_api():
    """Endpoint do chatbot — usa Claude API para autenticados, menu guiado para visitantes."""
    import json
    from flask import jsonify
    from app.utils.security import get_current_user, get_current_employee

    data = request.get_json(silent=True) or {}
    mensagem  = (data.get("mensagem") or "").strip()
    historico = data.get("historico") or []  # lista de {role, content}

    if not mensagem:
        return jsonify({"erro": "Mensagem vazia"}), 400

    usuario   = get_current_user()
    funcionario = get_current_employee()
    autenticado = bool(usuario or funcionario)

    if not autenticado:
        # Visitante: resposta simples sem IA (segurança e custo)
        return jsonify({"resposta": None, "visitante": True})

    # Usuário autenticado: chama Claude API
    try:
        import requests as _req

        SYSTEM_PROMPT = """Você é o assistente virtual da Combate Rasante Aviação Agrícola.
Responda APENAS sobre aviação agrícola, agricultura, agronegócio, defensivos, pulverização aérea,
manutenção de aeronaves agrícolas, segurança de voo agrícola, GPS e tecnologia no campo,
culturas agrícolas (soja, milho, cana-de-açúcar, café, algodão etc.), pragas e doenças,
e temas diretamente relacionados.

Se a pergunta NÃO for sobre esses temas, responda educadamente que você foi treinado
apenas para temas de aviação agrícola e agronegócio, e convide o usuário a perguntar
algo relacionado.

Seja objetivo, técnico quando necessário, e sempre em português brasileiro.
Máximo de 3 parágrafos por resposta."""

        mensagens_api = []
        for h in historico[-8:]:  # máx 8 mensagens de contexto
            if h.get("role") in ("user", "assistant") and h.get("content"):
                mensagens_api.append({"role": h["role"], "content": h["content"]})
        mensagens_api.append({"role": "user", "content": mensagem})

        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return jsonify({"resposta": "Assistente temporariamente indisponível. A chave de API não está configurada.", "visitante": False})

        resp = _req.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 600,
                "system": SYSTEM_PROMPT,
                "messages": mensagens_api,
            },
            timeout=25,
        )
        resp.raise_for_status()
        dados = resp.json()
        texto = dados["content"][0]["text"]
        return jsonify({"resposta": texto, "visitante": False})

    except Exception as e:
        erro_msg = str(e)[:200]
        import os, logging
        logging.error("Chatbot erro: %s", erro_msg)
        return jsonify({"resposta": "Desculpe, ocorreu um erro ao processar sua pergunta. Tente novamente em instantes.", "visitante": False})




# ── Análise de Aplicação (cliente) ──────────────────────────────────────────

@main_bp.route("/painel/analise_aplicacao/<int:file_id>")
@login_required
def painel_analise_aplicacao(file_id):
    """Baixa KMZ/KML do cliente e retorna tiros como JSON para a animação."""
    import urllib.request as _ur
    import zipfile, io, re, json as _json, math
    import xml.etree.ElementTree as ET
    from app.models.client_file import ClientFile

    user = get_current_user()
    cf = ClientFile.query.get_or_404(file_id)
    if cf.user_id != user.id:
        abort(403)

    ext = (cf.file_ext or "").lower().lstrip(".")
    if ext not in ("kml", "kmz"):
        return _json.dumps({"erro": "Arquivo não é KML/KMZ"}), 400, {"Content-Type": "application/json"}

    # Download
    try:
        req = _ur.Request(cf.url, headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except Exception as e:
        return _json.dumps({"erro": str(e)}), 500, {"Content-Type": "application/json"}

    # KMZ → KML
    if ext == "kmz":
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                kml_name = next((n for n in z.namelist() if n.endswith(".kml")), None)
                raw = z.read(kml_name) if kml_name else b""
        except Exception as e:
            return _json.dumps({"erro": "Erro ao extrair KMZ: " + str(e)}), 500, {"Content-Type": "application/json"}

    # Parse KML
    try:
        root = ET.fromstring(raw)
    except Exception as e:
        return _json.dumps({"erro": "KML inválido: " + str(e)}), 500, {"Content-Type": "application/json"}

    tag = root.tag
    ns_uri = tag[1:tag.index("}")] if tag.startswith("{") else ""
    def findall(el, path):
        return el.findall(".//{%s}%s" % (ns_uri, path)) if ns_uri else el.findall(".//" + path)
    def findone(el, path):
        return el.find(".//{%s}%s" % (ns_uri, path)) if ns_uri else el.find(".//" + path)

    tiros = []
    for pm in findall(root, "Placemark"):
        ne = findone(pm, "name")
        name = (ne.text or "").strip() if ne is not None else ""
        m = re.match(r"Tiro\s+(\d+)", name, re.IGNORECASE)
        if not m:
            continue
        poly = findone(pm, "Polygon")
        if poly is None:
            continue
        ce = findone(poly, "coordinates")
        if ce is None:
            continue
        pts = []
        for tok in (ce.text or "").strip().split():
            parts = tok.split(",")
            if len(parts) >= 2:
                try:
                    pts.append([float(parts[1]), float(parts[0])])
                except ValueError:
                    pass
        if len(pts) < 3:
            continue
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
        lat_c = sum(lats) / len(lats)
        lon_c = sum(lons) / len(lons)
        lat_m = (max(lats) - min(lats)) * 111000
        lon_m = (max(lons) - min(lons)) * 111000 * abs(math.cos(math.radians(lat_c)))
        if lon_m > lat_m:
            entry, exit_pt = [lat_c, min(lons)], [lat_c, max(lons)]
        else:
            entry, exit_pt = [min(lats), lon_c], [max(lats), lon_c]
        tiros.append({"num": int(m.group(1)), "name": name, "polygon": pts,
                      "centroid": [lat_c, lon_c], "entry": entry, "exit": exit_pt})

    tiros.sort(key=lambda x: x["num"])
    return _json.dumps({"tiros": tiros}), 200, {"Content-Type": "application/json"}
