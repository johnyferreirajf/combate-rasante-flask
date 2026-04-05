import os
from werkzeug.utils import secure_filename
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

from app.models import User, Employee, ContactMessage
from app import db
from app.utils.security import login_required, admin_required, get_current_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not email or not password:
            flash("Informe e-mail e senha.", "error")
            return redirect(url_for("auth.login"))

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("E-mail ou senha inválidos.", "error")
            return redirect(url_for("auth.login"))

        session["user_id"] = user.id

        # ✅ depois do login, manda pro painel certo
        next_url = request.args.get("next") or url_for("main.painel")
        return redirect(next_url)

    return render_template("login.html", current_user=get_current_user())


@auth_bp.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Você saiu da sessão com sucesso.", "success")
    return redirect(url_for("main.index"))


# ✅ Mantém compatibilidade se alguém acessar /dashboard via auth
@auth_bp.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("main.painel"))


@auth_bp.route("/admin", methods=["GET", "POST"])
@login_required
@admin_required
def admin():
    current_user_obj = get_current_user()
    created_user_email = None

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if not name:
            flash("Informe o nome do cliente.", "error")
            return redirect(url_for("auth.admin"))

        if not email:
            flash("Informe o e-mail do cliente.", "error")
            return redirect(url_for("auth.admin"))

        if not password:
            flash("Informe a senha.", "error")
            return redirect(url_for("auth.admin"))

        if len(password) < 6:
            flash("Senha deve ter pelo menos 6 caracteres.", "error")
            return redirect(url_for("auth.admin"))

        if password != confirm_password:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for("auth.admin"))

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Este e-mail já está cadastrado.", "error")
            return redirect(url_for("auth.admin"))

        new_user = User(name=name, email=email, is_admin=False)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        created_user_email = new_user.email
        flash(f"Cliente {new_user.email} criado com sucesso!", "success")
        return redirect(url_for("auth.admin"))

    users = User.query.order_by(User.id.desc()).all()
    return render_template(
        "admin.html",
        current_user=current_user_obj,
        created_user_email=created_user_email,
        users=users,
    )



@auth_bp.route("/admin/funcionarios", methods=["GET", "POST"])
@login_required
@admin_required
def admin_funcionarios():
    current_user_obj = get_current_user()
    employees = Employee.query.order_by(Employee.created_at.desc()).all()

    if request.method == "POST":
        name     = (request.form.get("name")     or "").strip()
        username = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password")  or ""
        confirm  = request.form.get("confirm_password") or ""
        is_admin = request.form.get("is_admin") == "1"

        if not name:
            flash("Informe o nome do funcionário.", "error")
            return redirect(url_for("auth.admin_funcionarios"))

        if not username:
            flash("Informe o usuário de login.", "error")
            return redirect(url_for("auth.admin_funcionarios"))

        if not password:
            flash("Informe a senha.", "error")
            return redirect(url_for("auth.admin_funcionarios"))

        if len(password) < 4:
            flash("Senha deve ter pelo menos 4 caracteres.", "error")
            return redirect(url_for("auth.admin_funcionarios"))

        if password != confirm:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for("auth.admin_funcionarios"))

        if Employee.query.filter_by(username=username).first():
            flash("Este usuário já está cadastrado.", "error")
            return redirect(url_for("auth.admin_funcionarios"))

        emp = Employee(name=name, username=username, is_admin=is_admin)
        emp.set_password(password)
        db.session.add(emp)
        db.session.commit()

        flash(f"Funcionário '{emp.name}' criado com sucesso!", "success")
        return redirect(url_for("auth.admin_funcionarios"))

    return render_template(
        "admin_funcionarios.html",
        current_user=current_user_obj,
        employees=employees,
    )


@auth_bp.route("/admin/funcionarios/excluir/<int:emp_id>", methods=["POST"])
@login_required
@admin_required
def admin_funcionarios_excluir(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    # Não deixa excluir a si mesmo
    current = get_current_user()
    db.session.delete(emp)
    db.session.commit()
    flash(f"Funcionário '{emp.name}' removido.", "success")
    return redirect(url_for("auth.admin_funcionarios"))



@auth_bp.route("/admin/trocar-senha", methods=["GET", "POST"])
@login_required
@admin_required
def trocar_senha():
    current_user_obj = get_current_user()

    if request.method == "POST":
        senha_atual   = request.form.get("senha_atual")    or ""
        nova_senha    = request.form.get("nova_senha")     or ""
        confirmar     = request.form.get("confirmar")      or ""

        if not current_user_obj.check_password(senha_atual):
            flash("Senha atual incorreta.", "error")
            return redirect(url_for("auth.trocar_senha"))

        if len(nova_senha) < 6:
            flash("A nova senha deve ter pelo menos 6 caracteres.", "error")
            return redirect(url_for("auth.trocar_senha"))

        if nova_senha != confirmar:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for("auth.trocar_senha"))

        current_user_obj.set_password(nova_senha)
        db.session.commit()
        flash("Senha alterada com sucesso!", "success")
        return redirect(url_for("auth.trocar_senha"))

    return render_template(
        "trocar_senha.html",
        current_user=current_user_obj,
    )




# ─── Impersonation (visualizar como cliente) ──────────────────

@auth_bp.route("/admin/visualizar-como/<int:uid>")
@login_required
@admin_required
def visualizar_como(uid):
    """Admin entra no painel do cliente sem precisar da senha."""
    from app.models.user import User
    from flask import session
    user = User.query.get_or_404(uid)
    # Salvar sessão do admin para poder voltar
    session["admin_impersonating"] = True
    session["admin_real_email"]    = session.get("user_email", "")
    session["admin_real_id"]       = session.get("user_id", "")
    # Fazer "login" como o cliente
    session["user_id"]    = user.id
    session["user_email"] = user.email
    flash(f"Visualizando como {user.name or user.email}. Use o banner para voltar.", "info")
    return redirect(url_for("main.painel"))


@auth_bp.route("/admin/sair-impersonation")
def sair_impersonation():
    """Volta para a sessão do admin."""
    from flask import session
    if not session.get("admin_impersonating"):
        return redirect(url_for("main.index"))
    # Restaurar sessão do admin
    session["user_id"]    = session.pop("admin_real_id", "")
    session["user_email"] = session.pop("admin_real_email", "")
    session.pop("admin_impersonating", None)
    return redirect(url_for("auth.admin"))

# ─── Editar / Excluir Cliente ─────────────────────────────────

@auth_bp.route("/admin/clientes/editar/<int:uid>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_cliente_editar(uid):
    user = User.query.get_or_404(uid)
    current_user_obj = get_current_user()

    if request.method == "POST":
        acao  = request.form.get("acao", "dados")
        nome  = (request.form.get("name")  or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("password") or ""
        conf  = request.form.get("confirm_password") or ""

        if acao == "dados":
            if not nome:
                flash("Informe o nome.", "error")
                return redirect(url_for("auth.admin_cliente_editar", uid=uid))
            if not email:
                flash("Informe o e-mail.", "error")
                return redirect(url_for("auth.admin_cliente_editar", uid=uid))
            # Verificar e-mail duplicado em outro usuário
            dup = User.query.filter_by(email=email).first()
            if dup and dup.id != uid:
                flash("Este e-mail já está em uso.", "error")
                return redirect(url_for("auth.admin_cliente_editar", uid=uid))
            user.name  = nome
            user.email = email
            db.session.commit()
            flash("Dados atualizados!", "success")

        elif acao == "senha":
            if len(senha) < 6:
                flash("Senha deve ter pelo menos 6 caracteres.", "error")
                return redirect(url_for("auth.admin_cliente_editar", uid=uid))
            if senha != conf:
                flash("As senhas não coincidem.", "error")
                return redirect(url_for("auth.admin_cliente_editar", uid=uid))
            user.set_password(senha)
            db.session.commit()
            flash("Senha alterada!", "success")

        return redirect(url_for("auth.admin_cliente_editar", uid=uid))

    return render_template("admin_cliente_editar.html",
                           current_user=current_user_obj,
                           cliente=user)


@auth_bp.route("/admin/clientes/excluir/<int:uid>", methods=["POST"])
@login_required
@admin_required
def admin_cliente_excluir(uid):
    from app.models.client_file import ClientFile
    import cloudinary, cloudinary.uploader
    from flask import current_app

    user = User.query.get_or_404(uid)

    # Não deixa excluir o próprio admin
    admin_email = current_app.config.get("ADMIN_EMAIL", "")
    if user.email.lower() == admin_email.lower() or user.is_admin:
        flash("Não é possível excluir a conta admin.", "error")
        return redirect(url_for("auth.admin"))

    # Excluir arquivos do Cloudinary
    use_cloud = current_app.config.get("USE_CLOUDINARY", False)
    for cf in ClientFile.query.filter_by(user_id=uid).all():
        if use_cloud and cf.source == "cloudinary" and cf.public_id:
            try:
                cloudinary.config(
                    cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
                    api_key=current_app.config["CLOUDINARY_API_KEY"],
                    api_secret=current_app.config["CLOUDINARY_API_SECRET"],
                    secure=True,
                )
                rtype = "image" if cf.is_image else "raw"
                cloudinary.uploader.destroy(cf.public_id, resource_type=rtype)
            except Exception:
                pass
        db.session.delete(cf)

    nome = user.name or user.email
    db.session.delete(user)
    db.session.commit()
    flash(f"Cliente '{nome}' excluído.", "success")
    return redirect(url_for("auth.admin"))


# ─── Editar Funcionário ────────────────────────────────────────

@auth_bp.route("/admin/funcionarios/editar/<int:eid>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_funcionario_editar(eid):
    emp = Employee.query.get_or_404(eid)
    current_user_obj = get_current_user()

    if request.method == "POST":
        acao     = request.form.get("acao", "dados")
        nome     = (request.form.get("name")     or "").strip()
        username = (request.form.get("username") or "").strip().lower()
        senha    = request.form.get("password")  or ""
        conf     = request.form.get("confirm_password") or ""
        is_admin = request.form.get("is_admin") == "1"

        if acao == "dados":
            if not nome:
                flash("Informe o nome.", "error")
                return redirect(url_for("auth.admin_funcionario_editar", eid=eid))
            if not username:
                flash("Informe o usuário.", "error")
                return redirect(url_for("auth.admin_funcionario_editar", eid=eid))
            dup = Employee.query.filter_by(username=username).first()
            if dup and dup.id != eid:
                flash("Este usuário já está em uso.", "error")
                return redirect(url_for("auth.admin_funcionario_editar", eid=eid))
            emp.name     = nome
            emp.username = username
            emp.is_admin = is_admin
            db.session.commit()
            flash("Dados atualizados!", "success")

        elif acao == "senha":
            if len(senha) < 4:
                flash("Senha deve ter pelo menos 4 caracteres.", "error")
                return redirect(url_for("auth.admin_funcionario_editar", eid=eid))
            if senha != conf:
                flash("As senhas não coincidem.", "error")
                return redirect(url_for("auth.admin_funcionario_editar", eid=eid))
            emp.set_password(senha)
            db.session.commit()
            flash("Senha alterada!", "success")

        return redirect(url_for("auth.admin_funcionario_editar", eid=eid))

    return render_template("admin_funcionario_editar.html",
                           current_user=current_user_obj,
                           funcionario=emp)

# ─── Explorador de arquivos por cliente (admin) ───────────────

ADMIN_ALLOWED_EXT = {
    "png","jpg","jpeg","webp","gif",
    "pdf","kml","kmz",
    "xlsx","xls","csv",
    "doc","docx","ppt","pptx",
    "zip","txt",
}

def _admin_allowed(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ADMIN_ALLOWED_EXT

def _clean_path(path):
    path = (path or "").strip().replace("\\", "/").strip("/")
    if ".." in path.split("/"):
        return ""
    return path

def _ext(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


@auth_bp.route("/admin/arquivos")
@login_required
@admin_required
def admin_arquivos():
    from app.models.client_file import ClientFile
    current_user_obj = get_current_user()
    clientes = User.query.filter_by(is_admin=False).order_by(User.name).all()

    cliente_id = request.args.get("cliente_id", type=int)
    pasta      = _clean_path(request.args.get("path", ""))

    cliente_sel = None
    itens       = []
    subpastas   = []
    breadcrumbs = []

    if cliente_id:
        cliente_sel = User.query.get(cliente_id)
        if cliente_sel:
            if pasta:
                partes = pasta.split("/")
                acc = []
                for p in partes:
                    acc.append(p)
                    breadcrumbs.append({"name": p, "path": "/".join(acc)})

            prefixo = pasta + "/" if pasta else ""
            todas_pastas = set()
            for f in ClientFile.query.filter_by(user_id=cliente_id).all():
                fp = f.folder_path or ""
                if pasta == "":
                    if fp and "/" not in fp:
                        todas_pastas.add(fp)
                    elif fp and "/" in fp:
                        todas_pastas.add(fp.split("/")[0])
                else:
                    if fp.startswith(prefixo):
                        resto = fp[len(prefixo):]
                        if resto:
                            todas_pastas.add(resto.split("/")[0])
            subpastas = sorted(todas_pastas)

            itens = ClientFile.query.filter_by(
                user_id=cliente_id,
                folder_path=pasta
            ).filter(
                ClientFile.url != "__folder__"
            ).order_by(ClientFile.uploaded_at.desc()).all()

    return render_template(
        "admin_arquivos.html",
        current_user=current_user_obj,
        clientes=clientes,
        cliente_sel=cliente_sel,
        pasta=pasta,
        subpastas=subpastas,
        itens=itens,
        breadcrumbs=breadcrumbs,
    )


@auth_bp.route("/admin/arquivos/nova-pasta", methods=["POST"])
@login_required
@admin_required
def admin_nova_pasta():
    from app.models.client_file import ClientFile
    cliente_id  = request.form.get("cliente_id", type=int)
    pasta_atual = _clean_path(request.form.get("pasta_atual", ""))
    nome        = secure_filename((request.form.get("nome") or "").strip())

    if not nome:
        flash("Informe o nome da pasta.", "error")
        return redirect(url_for("auth.admin_arquivos", cliente_id=cliente_id, path=pasta_atual))

    nova = (pasta_atual + "/" + nome).strip("/") if pasta_atual else nome

    placeholder = ClientFile(
        user_id=cliente_id,
        original_filename=".keep",
        title=".keep",
        folder_path=nova,
        url="__folder__",
        source="folder",
        file_ext="",
    )
    db.session.add(placeholder)
    db.session.commit()

    flash(f"Pasta '{nome}' criada.", "success")
    return redirect(url_for("auth.admin_arquivos", cliente_id=cliente_id, path=nova))


@auth_bp.route("/admin/arquivos/upload", methods=["POST"])
@login_required
@admin_required
def admin_arquivo_upload():
    import cloudinary, cloudinary.uploader
    from flask import current_app
    from app.models.client_file import ClientFile

    cliente_id  = request.form.get("cliente_id", type=int)
    pasta_atual = _clean_path(request.form.get("pasta_atual", ""))
    titulo      = (request.form.get("titulo") or "").strip()
    arquivo     = request.files.get("arquivo")

    if not arquivo or not arquivo.filename:
        flash("Selecione um arquivo.", "error")
        return redirect(url_for("auth.admin_arquivos", cliente_id=cliente_id, path=pasta_atual))

    if not _admin_allowed(arquivo.filename):
        flash("Tipo de arquivo não permitido.", "error")
        return redirect(url_for("auth.admin_arquivos", cliente_id=cliente_id, path=pasta_atual))

    filename  = secure_filename(arquivo.filename)
    ext       = _ext(filename)
    titulo    = titulo or filename
    url_final = ""
    public_id = ""
    source    = "local"
    file_size = 0

    use_cloud = current_app.config.get("USE_CLOUDINARY", False)
    if use_cloud:
        try:
            cloudinary.config(
                cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
                api_key=current_app.config["CLOUDINARY_API_KEY"],
                api_secret=current_app.config["CLOUDINARY_API_SECRET"],
                secure=True,
            )
            pasta_cloud = pasta_atual.replace("/", "_") if pasta_atual else "raiz"
            folder = f"combaterasante/cliente_{cliente_id}/{pasta_cloud}"
            rtype  = "image" if ext in {"png","jpg","jpeg","webp","gif"} else "raw"

            content = arquivo.stream.read()
            file_size = len(content)
            arquivo.stream.seek(0)

            result = cloudinary.uploader.upload(
                arquivo.stream,
                folder=folder,
                resource_type=rtype,
                use_filename=True,
                unique_filename=True,
            )
            url_final = result["secure_url"]
            public_id = result["public_id"]
            source    = "cloudinary"
        except Exception as e:
            flash(f"Erro no Cloudinary: {e}", "error")
            return redirect(url_for("auth.admin_arquivos", cliente_id=cliente_id, path=pasta_atual))
    else:
        flash("Configure o Cloudinary para uploads permanentes.", "error")
        return redirect(url_for("auth.admin_arquivos", cliente_id=cliente_id, path=pasta_atual))

    cf = ClientFile(
        user_id=cliente_id,
        original_filename=filename,
        title=titulo,
        folder_path=pasta_atual,
        url=url_final,
        public_id=public_id,
        source=source,
        file_ext=ext,
        file_size=file_size,
    )
    db.session.add(cf)
    db.session.commit()

    flash(f"'{titulo}' enviado!", "success")
    return redirect(url_for("auth.admin_arquivos", cliente_id=cliente_id, path=pasta_atual))


@auth_bp.route("/admin/arquivos/excluir/<int:file_id>", methods=["POST"])
@login_required
@admin_required
def admin_arquivo_excluir(file_id):
    import cloudinary, cloudinary.uploader
    from flask import current_app
    from app.models.client_file import ClientFile

    cf         = ClientFile.query.get_or_404(file_id)
    cliente_id = cf.user_id
    pasta      = cf.folder_path or ""

    if cf.source == "cloudinary" and cf.public_id:
        try:
            cloudinary.config(
                cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
                api_key=current_app.config["CLOUDINARY_API_KEY"],
                api_secret=current_app.config["CLOUDINARY_API_SECRET"],
                secure=True,
            )
            rtype = "image" if cf.is_image else "raw"
            cloudinary.uploader.destroy(cf.public_id, resource_type=rtype)
        except Exception:
            pass

    db.session.delete(cf)
    db.session.commit()
    flash("Arquivo removido.", "success")
    return redirect(url_for("auth.admin_arquivos", cliente_id=cliente_id, path=pasta))


@auth_bp.route("/admin/arquivos/renomear/<int:file_id>", methods=["POST"])
@login_required
@admin_required
def admin_arquivo_renomear(file_id):
    from app.models.client_file import ClientFile
    cf   = ClientFile.query.get_or_404(file_id)
    novo = (request.form.get("novo_titulo") or "").strip()
    if novo:
        cf.title = novo
        db.session.commit()
        flash("Renomeado.", "success")
    return redirect(url_for("auth.admin_arquivos",
                            cliente_id=cf.user_id, path=cf.folder_path or ""))


@auth_bp.route("/admin/arquivos/excluir-pasta", methods=["POST"])
@login_required
@admin_required
def admin_pasta_excluir():
    import cloudinary, cloudinary.uploader
    from flask import current_app
    from app.models.client_file import ClientFile

    cliente_id = request.form.get("cliente_id", type=int)
    pasta      = _clean_path(request.form.get("pasta", ""))
    pasta_pai  = "/".join(pasta.split("/")[:-1]) if "/" in pasta else ""
    prefixo    = pasta + "/"
    use_cloud  = current_app.config.get("USE_CLOUDINARY", False)

    todos = ClientFile.query.filter_by(user_id=cliente_id).all()
    for cf in todos:
        fp = cf.folder_path or ""
        if fp == pasta or fp.startswith(prefixo):
            if use_cloud and cf.source == "cloudinary" and cf.public_id:
                try:
                    cloudinary.config(
                        cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
                        api_key=current_app.config["CLOUDINARY_API_KEY"],
                        api_secret=current_app.config["CLOUDINARY_API_SECRET"],
                        secure=True,
                    )
                    rtype = "image" if cf.is_image else "raw"
                    cloudinary.uploader.destroy(cf.public_id, resource_type=rtype)
                except Exception:
                    pass
            db.session.delete(cf)

    db.session.commit()
    flash(f"Pasta excluída.", "success")
    return redirect(url_for("auth.admin_arquivos", cliente_id=cliente_id, path=pasta_pai))


# ─── Backup e Restore do banco ─────────────────────────────────

@auth_bp.route("/admin/backup")
@login_required
@admin_required
def admin_backup():
    """Gera um JSON com todos os dados do banco para download."""
    import json
    import datetime
    from flask import Response
    from app.models.photo import Photo
    from app.models.employee import Employee

    data = {
        "gerado_em": datetime.datetime.utcnow().isoformat(),
        "versao": "1.0",
        "clientes": [],
        "funcionarios": [],
        "fotos": [],
    }

    for u in User.query.all():
        data["clientes"].append({
            "id":           u.id,
            "name":         u.name,
            "email":        u.email,
            "password_hash": u.password_hash,
            "is_admin":     u.is_admin,
            "created_at":   u.created_at.isoformat() if u.created_at else None,
        })

    for e in Employee.query.all():
        data["funcionarios"].append({
            "id":           e.id,
            "name":         e.name,
            "username":     e.username,
            "password_hash": e.password_hash,
            "is_admin":     e.is_admin,
            "created_at":   e.created_at.isoformat() if e.created_at else None,
        })

    for f in Photo.query.all():
        data["fotos"].append({
            "id":         f.id,
            "user_id":    f.user_id,
            "filename":   f.filename,
            "title":      f.title,
            "tema":       f.tema,
            "safra":      f.safra,
            "mes":        f.mes,
            "dia":        f.dia,
            "url":        f.url,
            "public_id":  f.public_id,
            "source":     f.source,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        })

    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    filename = f"backup_combaterasante_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    return Response(
        json_str,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@auth_bp.route("/admin/restore", methods=["GET", "POST"])
@login_required
@admin_required
def admin_restore():
    """Restaura dados a partir de um arquivo JSON de backup."""
    import json
    from app.models.photo import Photo
    from app.models.employee import Employee
    from werkzeug.security import generate_password_hash

    current_user_obj = get_current_user()
    resultado = None

    if request.method == "POST":
        arquivo = request.files.get("backup_file")

        if not arquivo or not arquivo.filename.endswith(".json"):
            flash("Selecione um arquivo .json de backup.", "error")
            return redirect(url_for("auth.admin_restore"))

        try:
            data = json.loads(arquivo.read().decode("utf-8"))
        except Exception:
            flash("Arquivo inválido ou corrompido.", "error")
            return redirect(url_for("auth.admin_restore"))

        stats = {"clientes": 0, "funcionarios": 0, "fotos": 0, "erros": 0}

        # ── Restaurar clientes ──
        for c in data.get("clientes", []):
            try:
                existing = User.query.filter_by(email=c["email"]).first()
                if existing:
                    # Atualiza dados mas mantém registro existente
                    existing.name         = c.get("name", existing.name)
                    existing.password_hash = c.get("password_hash", existing.password_hash)
                    existing.is_admin     = c.get("is_admin", existing.is_admin)
                else:
                    u = User(
                        name=c["name"],
                        email=c["email"],
                        password_hash=c["password_hash"],
                        is_admin=c.get("is_admin", False),
                    )
                    db.session.add(u)
                stats["clientes"] += 1
            except Exception:
                stats["erros"] += 1

        db.session.flush()  # garante que os IDs dos clientes existam antes das fotos

        # ── Restaurar funcionários ──
        for e in data.get("funcionarios", []):
            try:
                existing = Employee.query.filter_by(username=e["username"]).first()
                if existing:
                    existing.name          = e.get("name", existing.name)
                    existing.password_hash = e.get("password_hash", existing.password_hash)
                    existing.is_admin      = e.get("is_admin", existing.is_admin)
                else:
                    emp = Employee(
                        name=e["name"],
                        username=e["username"],
                        password_hash=e["password_hash"],
                        is_admin=e.get("is_admin", False),
                    )
                    db.session.add(emp)
                stats["funcionarios"] += 1
            except Exception:
                stats["erros"] += 1

        # ── Restaurar fotos (vínculos com Cloudinary) ──
        for f in data.get("fotos", []):
            try:
                # Buscar o user pelo email original não é possível sem ele
                # Usa o user_id direto — funciona se o banco foi recriado com recreate_db.py
                existing = Photo.query.filter_by(
                    url=f.get("url", ""),
                ).first()
                if not existing and f.get("url"):
                    foto = Photo(
                        user_id=f["user_id"],
                        filename=f.get("filename", ""),
                        title=f.get("title"),
                        tema=f.get("tema", "outros"),
                        safra=f.get("safra", ""),
                        mes=f.get("mes", ""),
                        dia=f.get("dia", ""),
                        url=f.get("url", ""),
                        public_id=f.get("public_id"),
                        source=f.get("source", "cloudinary"),
                    )
                    db.session.add(foto)
                    stats["fotos"] += 1
            except Exception:
                stats["erros"] += 1

        try:
            db.session.commit()
            resultado = stats
            flash(
                f"Restaurado: {stats['clientes']} clientes, "
                f"{stats['funcionarios']} funcionários, "
                f"{stats['fotos']} fotos. "
                f"Erros: {stats['erros']}",
                "success" if stats["erros"] == 0 else "error"
            )
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao salvar no banco: {e}", "error")

    return render_template(
        "admin_backup.html",
        current_user=current_user_obj,
        resultado=resultado,
    )



# ─── Gerenciar Setores da Equipe ──────────────────────────────

@auth_bp.route("/admin/equipe/setor/renomear", methods=["POST"])
@login_required
@admin_required
def admin_setor_renomear():
    from app.models.team_member import TeamMember
    nome_antigo = (request.form.get("nome_antigo") or "").strip()
    nome_novo   = (request.form.get("nome_novo")   or "").strip()

    if not nome_antigo or not nome_novo:
        flash("Preencha os dois campos.", "error")
        return redirect(url_for("auth.admin_equipe"))

    membros = TeamMember.query.filter_by(setor=nome_antigo).all()
    for m in membros:
        m.setor = nome_novo
    db.session.commit()
    flash(f"Setor renomeado para '{nome_novo}'.", "success")
    return redirect(url_for("auth.admin_equipe"))


@auth_bp.route("/admin/equipe/setor/excluir", methods=["POST"])
@login_required
@admin_required
def admin_setor_excluir():
    from app.models.team_member import TeamMember
    nome = (request.form.get("nome") or "").strip()

    if not nome:
        flash("Setor inválido.", "error")
        return redirect(url_for("auth.admin_equipe"))

    count = TeamMember.query.filter_by(setor=nome).count()
    if count > 0:
        flash(f"Não é possível excluir '{nome}' — ainda tem {count} membro(s). Mova ou exclua os membros primeiro.", "error")
        return redirect(url_for("auth.admin_equipe"))

    flash(f"Setor '{nome}' removido.", "success")
    return redirect(url_for("auth.admin_equipe"))


@auth_bp.route("/admin/equipe/setor/mover", methods=["POST"])
@login_required
@admin_required
def admin_setor_mover():
    from app.models.sector_order import SectorOrder
    setor     = (request.form.get("setor")     or "").strip()
    direcao   = request.form.get("direcao", "cima")  # "cima" ou "baixo"

    _garantir_setor_no_banco(setor)

    todos = SectorOrder.query.order_by(SectorOrder.posicao).all()
    idx   = next((i for i, r in enumerate(todos) if r.setor == setor), None)

    if idx is None:
        flash("Setor não encontrado.", "error")
        return redirect(url_for("auth.admin_equipe"))

    # Trocar posição com o vizinho
    if direcao == "cima" and idx > 0:
        vizinho = todos[idx - 1]
        todos[idx].posicao, vizinho.posicao = vizinho.posicao, todos[idx].posicao
    elif direcao == "baixo" and idx < len(todos) - 1:
        vizinho = todos[idx + 1]
        todos[idx].posicao, vizinho.posicao = vizinho.posicao, todos[idx].posicao

    db.session.commit()
    return redirect(url_for("auth.admin_equipe"))

# ─── Gerenciar Equipe ─────────────────────────────────────────

# Ordem preferencial dos setores
def _get_ordem_setores():
    """Retorna dict {setor: posicao} do banco."""
    from app.models.sector_order import SectorOrder
    rows = SectorOrder.query.order_by(SectorOrder.posicao).all()
    return {r.setor: r.posicao for r in rows}

def _sort_key_setor(membro):
    from app.models.sector_order import SectorOrder
    row = SectorOrder.query.filter_by(setor=membro.setor).first()
    return row.posicao if row else 999

def _garantir_setor_no_banco(setor):
    """Cria registro de ordem se não existir."""
    from app.models.sector_order import SectorOrder
    from app import db as _db
    if not SectorOrder.query.filter_by(setor=setor).first():
        max_pos = _db.session.query(_db.func.max(SectorOrder.posicao)).scalar() or 0
        _db.session.add(SectorOrder(setor=setor, posicao=max_pos + 10))
        _db.session.commit()


@auth_bp.route("/admin/equipe", methods=["GET", "POST"])
@login_required
@admin_required
def admin_equipe():
    from app.models.team_member import TeamMember
    current_user_obj = get_current_user()
    todos = TeamMember.query.order_by(TeamMember.ordem).all()
    # Garantir que todos os setores existam no banco de ordem
    for m in todos:
        _garantir_setor_no_banco(m.setor)
    todos.sort(key=lambda m: (_sort_key_setor(m), m.ordem))

    from collections import OrderedDict
    setores = OrderedDict()
    for m in todos:
        if m.setor not in setores:
            setores[m.setor] = []
        if not m.nome.startswith("__setor__"):
            setores[m.setor].append(m)
    
    # Incluir setores vazios (só placeholder) também
    from app.models.sector_order import SectorOrder
    for so in SectorOrder.query.order_by(SectorOrder.posicao).all():
        if so.setor not in setores:
            setores[so.setor] = []

    if request.method == "POST":

        # ── Criar novo setor (placeholder) ──
        if request.form.get("criar_setor"):
            nome_setor = (request.form.get("nome_setor") or "").strip()
            if not nome_setor:
                flash("Informe o nome do setor.", "error")
                return redirect(url_for("auth.admin_equipe"))
            # Verifica se já existe
            existing = TeamMember.query.filter_by(setor=nome_setor).first()
            if existing:
                flash(f"Setor '{nome_setor}' já existe.", "error")
                return redirect(url_for("auth.admin_equipe"))
            # Cria membro placeholder oculto para materializar o setor
            placeholder = TeamMember(
                nome=f"__setor__{nome_setor}",
                cargo="—", setor=nome_setor,
                ativo=False, ordem=999
            )
            db.session.add(placeholder)
            db.session.commit()
            _garantir_setor_no_banco(nome_setor)
            flash(f"Setor '{nome_setor}' criado! Adicione membros a ele.", "success")
            return redirect(url_for("auth.admin_equipe"))

        # ── Adicionar novo membro ──
        nome      = (request.form.get("nome")      or "").strip()
        cargo     = (request.form.get("cargo")     or "").strip()
        setor     = (request.form.get("setor")     or "").strip()
        tags      = (request.form.get("tags")      or "").strip()
        descricao = (request.form.get("descricao") or "").strip()
        ordem     = request.form.get("ordem", 99, type=int)

        if not nome or not cargo or not setor:
            flash("Nome, cargo e setor são obrigatórios.", "error")
            return redirect(url_for("auth.admin_equipe"))

        membro = TeamMember(nome=nome, cargo=cargo, setor=setor,
                            tags=tags, descricao=descricao, ordem=ordem)
        db.session.add(membro)
        db.session.commit()
        _garantir_setor_no_banco(setor)
        flash(f"'{nome}' adicionado à equipe!", "success")
        return redirect(url_for("auth.admin_equipe"))

    return render_template("admin_equipe.html",
                           current_user=current_user_obj,
                           membros=todos,
                           setores=setores)


@auth_bp.route("/admin/equipe/editar/<int:mid>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_equipe_editar(mid):
    import cloudinary, cloudinary.uploader
    from flask import current_app
    from app.models.team_member import TeamMember

    membro = TeamMember.query.get_or_404(mid)
    current_user_obj = get_current_user()

    if request.method == "POST":
        acao = request.form.get("acao", "salvar")

        if acao == "foto":
            foto = request.files.get("foto")
            if foto and foto.filename:
                use_cloud = current_app.config.get("USE_CLOUDINARY", False)
                if use_cloud:
                    try:
                        cloudinary.config(
                            cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
                            api_key=current_app.config["CLOUDINARY_API_KEY"],
                            api_secret=current_app.config["CLOUDINARY_API_SECRET"],
                            secure=True,
                        )
                        # Remover foto antiga se existir
                        if membro.foto_public_id:
                            try:
                                cloudinary.uploader.destroy(membro.foto_public_id,
                                                            resource_type="image")
                            except Exception:
                                pass

                        result = cloudinary.uploader.upload(
                            foto,
                            folder="combaterasante/equipe",
                            resource_type="image",
                            transformation=[
                                {"width": 400, "height": 400,
                                 "crop": "fill", "gravity": "face"}
                            ],
                            use_filename=True,
                            unique_filename=True,
                        )
                        membro.foto_url = result["secure_url"]
                        membro.foto_public_id = result["public_id"]
                        db.session.commit()
                        flash("Foto atualizada!", "success")
                    except Exception as e:
                        flash(f"Erro ao enviar foto: {e}", "error")
                else:
                    flash("Configure o Cloudinary para upload de fotos.", "error")
            return redirect(url_for("auth.admin_equipe_editar", mid=mid))

        elif acao == "remover_foto":
            use_cloud = current_app.config.get("USE_CLOUDINARY", False)
            if use_cloud and membro.foto_public_id:
                try:
                    cloudinary.config(
                        cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
                        api_key=current_app.config["CLOUDINARY_API_KEY"],
                        api_secret=current_app.config["CLOUDINARY_API_SECRET"],
                        secure=True,
                    )
                    cloudinary.uploader.destroy(membro.foto_public_id,
                                                resource_type="image")
                except Exception:
                    pass
            membro.foto_url = ""
            membro.foto_public_id = ""
            db.session.commit()
            flash("Foto removida.", "success")
            return redirect(url_for("auth.admin_equipe_editar", mid=mid))

        else:  # salvar dados
            membro.nome      = (request.form.get("nome")      or "").strip()
            membro.cargo     = (request.form.get("cargo")     or "").strip()
            membro.setor     = (request.form.get("setor")     or "").strip()
            membro.tags      = (request.form.get("tags")      or "").strip()
            membro.descricao = (request.form.get("descricao") or "").strip()
            membro.ordem     = request.form.get("ordem", membro.ordem, type=int)
            membro.ativo     = request.form.get("ativo") == "1"
            db.session.commit()
            flash("Membro atualizado!", "success")
            return redirect(url_for("auth.admin_equipe"))

    return render_template("admin_equipe_editar.html",
                           current_user=current_user_obj,
                           membro=membro)


@auth_bp.route("/admin/equipe/excluir/<int:mid>", methods=["POST"])
@login_required
@admin_required
def admin_equipe_excluir(mid):
    import cloudinary, cloudinary.uploader
    from flask import current_app
    from app.models.team_member import TeamMember

    membro = TeamMember.query.get_or_404(mid)
    use_cloud = current_app.config.get("USE_CLOUDINARY", False)
    if use_cloud and membro.foto_public_id:
        try:
            cloudinary.config(
                cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
                api_key=current_app.config["CLOUDINARY_API_KEY"],
                api_secret=current_app.config["CLOUDINARY_API_SECRET"],
                secure=True,
            )
            cloudinary.uploader.destroy(membro.foto_public_id, resource_type="image")
        except Exception:
            pass

    db.session.delete(membro)
    db.session.commit()
    flash(f"'{membro.nome}' removido da equipe.", "success")
    return redirect(url_for("auth.admin_equipe"))


@auth_bp.route("/admin/logs")
@login_required
@admin_required
def admin_logs():
    from app.models.action_log import ActionLog
    logs = ActionLog.query.order_by(ActionLog.created_at.desc()).limit(200).all()
    return render_template("admin_logs.html",
                           current_user=get_current_user(),
                           logs=logs)

# ✅ Mensagens do formulário de contato
@auth_bp.route("/admin/mensagens")
@login_required
@admin_required
def admin_mensagens():
    msgs = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template(
        "admin_mensagens.html",
        current_user=get_current_user(),
        msgs=msgs
    )


@auth_bp.route("/admin/mensagens/excluir/<int:mid>", methods=["POST"])
@login_required
@admin_required
def admin_mensagem_excluir(mid):
    msg = ContactMessage.query.get_or_404(mid)
    db.session.delete(msg)
    db.session.commit()
    flash("Mensagem excluída.", "success")
    return redirect(url_for("auth.admin_mensagens"))
