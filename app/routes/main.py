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
    """Proxy de download — sempre retorna o arquivo via servidor com attachment."""
    import requests as _req, re, mimetypes
    from flask import Response, stream_with_context
    from app.models.client_file import ClientFile

    user = get_current_user()
    cf   = ClientFile.query.get_or_404(file_id)
    if cf.user_id != user.id:
        abort(403)

    # ── Nome seguro para o header ────────────────────────────────────────────
    name = cf.original_filename or cf.title or "arquivo"
    ext  = (cf.file_ext or "").lower()
    if ext and not name.lower().endswith(f".{ext}"):
        name = f"{name}.{ext}"
    safe_name = re.sub(r'[\x00-\x1f"\\]', "", name).strip() or "arquivo"
    encoded   = _req.utils.quote(safe_name)

    # ── Determinar URL para baixar (original ou assinada) ────────────────────
    def _get_signed_url(original_url):
        """Gera URL autenticada via Cloudinary API (private_download_url).
        Para raw resources, result['public_id'] inclui a extensão.
        private_download_url exige pid SEM extensão + format COM extensão."""
        try:
            import time
            from app.utils.storage import _init_cloudinary
            from cloudinary.utils import private_download_url as _pdu
            _init_cloudinary()
            pid = cf.public_id or ""
            if not pid and "/upload/" in original_url:
                m = re.search(r"/upload/(?:v\d+/)?(.+)$", original_url)
                if m:
                    pid = m.group(1)
            if not pid:
                return None
            # Separar public_id da extensão (private_download_url precisa assim)
            m_ext = re.search(r"\.([^./]+)$", pid)
            file_fmt = m_ext.group(1) if m_ext else (ext or "")
            pid_clean = pid[:m_ext.start()] if m_ext else pid
            signed = _pdu(pid_clean, file_fmt, resource_type="raw",
                          expires_at=int(time.time()) + 300)
            return signed
        except Exception as e2:
            current_app.logger.warning(f"signed URL generation failed: {e2}")
            return None

    def _proxy(fetch_url, ctype):
        """Faz streaming do arquivo via servidor com headers de attachment."""
        r = _req.get(
            fetch_url, stream=True, timeout=120,
            headers={"User-Agent": "CombateRasante/1.0"},
            allow_redirects=True,
        )
        r.raise_for_status()

        # Corrigir MIME type
        ct = r.headers.get("Content-Type", "application/octet-stream")
        if ext == "pdf":
            ct = "application/pdf"
        elif "octet-stream" in ct and ext:
            guessed, _ = mimetypes.guess_type(name)
            if guessed:
                ct = guessed

        def _gen():
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk

        resp = Response(stream_with_context(_gen()), content_type=ct)
        resp.headers["Content-Disposition"] = (
            f'attachment; filename="{safe_name}"; filename*=UTF-8\'\'{encoded}'
        )
        resp.headers["Cache-Control"]        = "no-store"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        if "Content-Length" in r.headers:
            resp.headers["Content-Length"] = r.headers["Content-Length"]
        return resp

    url = cf.url or ""

    # ── Tentativa 1: URL original ─────────────────────────────────────────────
    try:
        return _proxy(url, ext)
    except _req.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 0
        current_app.logger.info(f"painel_download: original URL returned {status}, trying signed URL")
    except Exception as e:
        current_app.logger.warning(f"painel_download: original URL failed ({e}), trying signed URL")

    # ── Tentativa 2: URL assinada (para arquivos privados no Cloudinary) ──────
    signed = _get_signed_url(url)
    if signed:
        try:
            return _proxy(signed, ext)
        except Exception as e:
            current_app.logger.error(f"painel_download: signed URL also failed: {e}")

    # ── Último recurso: redirecionar (melhor que nada) ────────────────────────
    current_app.logger.error(f"painel_download: all methods failed for file {file_id}")
    return redirect(signed or url)


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



@main_bp.route("/painel/analise_aplicacao/<int:file_id>")
@login_required
def painel_analise_aplicacao(file_id):
    """Análise de aplicação KMZ — versão cliente.
    Busca o arquivo KMZ via proxy assinado e retorna JSON com tiros/track/summary."""
    import requests as _req, re, zipfile, io, json as _json

    user = get_current_user()
    from app.models.client_file import ClientFile
    cf = ClientFile.query.get_or_404(file_id)
    if cf.user_id != user.id:
        abort(403)

    fname = (cf.original_filename or "").lower()
    is_kmz = fname.endswith(".kmz")
    is_kml = fname.endswith(".kml")
    if not (is_kmz or is_kml):
        return _json.dumps({"erro": "Arquivo não é KML/KMZ"}), 400,                {"Content-Type": "application/json"}

    url = cf.url or ""

    def _fetch_raw(fetch_url):
        """Baixa o KMZ/KML via requests."""
        r = _req.get(fetch_url, timeout=60,
                     headers={"User-Agent": "CombateRasante/1.0"},
                     allow_redirects=True)
        r.raise_for_status()
        return r.content

    def _get_signed_url():
        """Gera URL autenticada via Cloudinary API (private_download_url).
        public_id do banco inclui extensão; private_download_url precisa separado."""
        try:
            import time
            from app.utils.storage import _init_cloudinary
            from cloudinary.utils import private_download_url as _pdu
            _init_cloudinary()
            pid = cf.public_id or ""
            if not pid and "/upload/" in url:
                m = re.search(r"/upload/(?:v\d+/)?(.+)$", url)
                if m:
                    pid = m.group(1)
            if not pid:
                return None
            m_ext = re.search(r"\.([^./]+)$", pid)
            fname_lower = (cf.original_filename or "").lower()
            file_fmt = m_ext.group(1) if m_ext else ("kmz" if fname_lower.endswith(".kmz") else "kml")
            pid_clean = pid[:m_ext.start()] if m_ext else pid
            signed = _pdu(pid_clean, file_fmt, resource_type="raw",
                          expires_at=int(time.time()) + 300)
            return signed
        except Exception as e2:
            current_app.logger.warning(f"painel_analise signed URL failed: {e2}")
            return None

    # ── 1. Tentar URL original ────────────────────────────────────────────────
    raw = None
    try:
        raw = _fetch_raw(url)
    except _req.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 0
        current_app.logger.info(
            f"painel_analise: original URL returned {status}, trying signed URL")
        if status in (401, 403):
            signed = _get_signed_url()
            if signed:
                try:
                    raw = _fetch_raw(signed)
                except Exception as e3:
                    return _json.dumps({"erro": f"Erro ao baixar KMZ: {e3}"}), 500,                            {"Content-Type": "application/json"}
    except Exception as e:
        return _json.dumps({"erro": f"Erro ao baixar KMZ: {e}"}), 500,                {"Content-Type": "application/json"}

    if raw is None:
        return _json.dumps({"erro": "Não foi possível baixar o arquivo"}), 500,                {"Content-Type": "application/json"}

    # ── 2. Extrair KML se for KMZ ─────────────────────────────────────────────
    if is_kmz:
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                kml_name = next((n for n in z.namelist() if n.endswith(".kml")), None)
                raw = z.read(kml_name) if kml_name else b""
        except Exception as e:
            return _json.dumps({"erro": f"Erro ao extrair KMZ: {e}"}), 500,                    {"Content-Type": "application/json"}

    # ── 3. Parsear KML ────────────────────────────────────────────────────────
    from app.routes.employee import _parse_kml_full
    result, err = _parse_kml_full(raw)
    if err:
        return _json.dumps({"erro": err}), 500, {"Content-Type": "application/json"}

    return _json.dumps(result), 200, {"Content-Type": "application/json"}


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


