import os
import zipfile
import uuid
import shutil
import mimetypes
from werkzeug.utils import secure_filename

from flask import (
    Blueprint,
    render_template,
    request,
    abort,
    redirect,
    url_for,
    flash,
    session,
    current_app,
    send_file,
    send_from_directory,
)

from app import db
from app.models import Employee, EmployeeFile
from app.utils.security import employee_login_required, get_current_employee

def _human_size(size_bytes):
    if size_bytes is None:
        return "-"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"

employee_bp = Blueprint("employee", __name__, url_prefix="/funcionarios")


# ------------------------------
# Helpers (segurança de caminho)
# ------------------------------
def _ensure_upload_root() -> str:
    root = current_app.config.get("EMP_UPLOAD_FOLDER")
    if not root:
        root = os.path.join(current_app.instance_path, "employee_uploads")
    os.makedirs(root, exist_ok=True)
    return root


def _clean_relpath(relpath: str) -> str:
    """Normaliza e garante que o caminho seja relativo e seguro."""
    relpath = (relpath or "").strip().replace("\\", "/")
    relpath = relpath.lstrip("/")
    # Bloqueia path traversal
    if ".." in relpath.split("/"):
        return ""
    return relpath


def _safe_abs_path(relpath: str) -> str:
    root = _ensure_upload_root()
    relpath = _clean_relpath(relpath)
    abs_path = os.path.abspath(os.path.join(root, relpath))
    root_abs = os.path.abspath(root)
    if not abs_path.startswith(root_abs):
        return root_abs
    return abs_path


def _allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    allowed = current_app.config.get("EMP_ALLOWED_EXTENSIONS", set())
    return ext in allowed if allowed else True


def _list_folder(relpath: str):
    """Retorna (folders, files) do filesystem dentro do caminho informado."""
    relpath = _clean_relpath(relpath)
    abs_path = _safe_abs_path(relpath)

    folders = []
    files = []

    if not os.path.exists(abs_path):
        os.makedirs(abs_path, exist_ok=True)

    for name in sorted(os.listdir(abs_path)):
        full = os.path.join(abs_path, name)
        if os.path.isdir(full):
            folders.append(name)
        else:
            files.append(name)
    return folders, files


# ------------------------------
# Auth
# ------------------------------
@employee_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            flash("Informe usuário e senha.", "error")
            return redirect(url_for("employee.login"))

        emp = Employee.query.filter_by(username=username).first()
        if not emp or not emp.check_password(password):
            flash("Usuário ou senha inválidos.", "error")
            return redirect(url_for("employee.login"))

        session["employee_id"] = emp.id
        next_url = request.args.get("next") or url_for("employee.files")
        return redirect(next_url)

    return render_template("employee_login.html")


@employee_bp.route("/logout")
def logout():
    session.pop("employee_id", None)
    flash("Você saiu da Área de Funcionários.", "success")
    return redirect(url_for("main.index"))


# ------------------------------
# File manager (pastas/arquivos)
# ------------------------------
@employee_bp.route("/arquivos")
@employee_login_required
def files():
    current_employee = get_current_employee()
    relpath = request.args.get("path", "")  # pasta atual
    relpath = _clean_relpath(relpath)

    # filesystem (subpastas)
    folders, _ = _list_folder(relpath)

    # arquivos cadastrados no banco por "pasta" (guardamos o relpath em category)
    db_items = (
        EmployeeFile.query.filter_by(category=relpath)
        .order_by(EmployeeFile.uploaded_at.desc())
        .all()
    )

    # breadcrumbs
    crumbs = []
    if relpath:
        parts = relpath.split("/")
        acc = []
        for p in parts:
            acc.append(p)
            crumbs.append({"name": p, "path": "/".join(acc)})

    # monta lista única (pastas + arquivos) em estilo "explorador"
    view_items = []

    # Pastas
    for folder in folders:
        folder_rel = f"{relpath}/{folder}".strip("/")
        view_items.append(
            {
                "name": folder,
                "display": folder,
                "is_folder": True,
                "type": "Pasta",
                "size_bytes": None,
                "size_human": "-",
                "modified_ts": None,
                "modified_human": "-",
                "href": url_for("employee.files", path=folder_rel),
                "download_href": url_for("employee.download_folder", folder=folder_rel),
                "rename_folder_href": url_for("employee.rename_folder"),
                "delete_folder_href": url_for("employee.delete_folder"),
                "file_id": None,
            }
        )

    # Arquivos (do banco)
    for item in db_items:
        abs_file = _safe_abs_path(item.stored_filename)
        size_bytes = os.path.getsize(abs_file) if os.path.exists(abs_file) else None
        mtime = os.path.getmtime(abs_file) if os.path.exists(abs_file) else None

        display = item.title or item.original_filename
        ext = ""
        if "." in item.original_filename:
            ext = item.original_filename.rsplit(".", 1)[1].upper()

        view_items.append(
            {
                "name": item.original_filename,
                "display": display,
                "is_folder": False,
                "type": ext or "Arquivo",
                "size_bytes": size_bytes,
                "size_human": _human_size(size_bytes) if size_bytes is not None else "-",
                "modified_ts": int(mtime) if mtime else int(item.uploaded_at.timestamp()) if item.uploaded_at else 0,
                "modified_human": item.uploaded_at.strftime("%d/%m/%Y %H:%M") if item.uploaded_at else "-",
                "href": None,
                "download_href": url_for("employee.download", file_id=item.id),
                "delete_href": url_for("employee.delete_file", file_id=item.id),
                "rename_href": url_for("employee.rename_file", file_id=item.id),
                "file_id": item.id,
                "uploader_name": item.uploader.name if item.uploader else "-",
                "description": item.description or "",
            }
        )

    return render_template(
        "employee_files.html",
        employee=current_employee,
        current_path=relpath,
        crumbs=crumbs,
        items=view_items,
    )


@employee_bp.route("/mkdir", methods=["POST"])
@employee_login_required
def mkdir():
    base = _clean_relpath(request.form.get("path", ""))
    name = (request.form.get("name") or "").strip()

    if not name:
        flash("Informe o nome da pasta.", "error")
        return redirect(url_for("employee.files", path=base))

    # evita caracteres estranhos
    folder_name = secure_filename(name).replace("_", "-")
    if not folder_name:
        flash("Nome de pasta inválido.", "error")
        return redirect(url_for("employee.files", path=base))

    target_rel = f"{base}/{folder_name}".strip("/")
    target_abs = _safe_abs_path(target_rel)
    os.makedirs(target_abs, exist_ok=True)

    flash("Pasta criada com sucesso.", "success")
    return redirect(url_for("employee.files", path=base))


@employee_bp.route("/rename_folder", methods=["POST"])
@employee_login_required
def rename_folder():
    base = _clean_relpath(request.form.get("path", ""))
    old_name = (request.form.get("old_name") or "").strip()
    new_name = (request.form.get("new_name") or "").strip()

    if not old_name or not new_name:
        flash("Informe o nome atual e o novo nome.", "error")
        return redirect(url_for("employee.files", path=base))

    old_rel = f"{base}/{old_name}".strip("/")
    new_rel = f"{base}/{secure_filename(new_name).replace('_','-')}".strip("/")

    old_abs = _safe_abs_path(old_rel)
    new_abs = _safe_abs_path(new_rel)

    if not os.path.isdir(old_abs):
        flash("Pasta não encontrada.", "error")
        return redirect(url_for("employee.files", path=base))

    os.rename(old_abs, new_abs)

    # Atualiza itens do banco (category e stored_filename)
    # Ex: category="atividades" -> "novonome"
    old_prefix = old_rel
    new_prefix = new_rel

    affected = EmployeeFile.query.filter(EmployeeFile.category.like(f"{old_prefix}%")).all()
    for item in affected:
        # category
        if item.category == old_prefix:
            item.category = new_prefix
        elif item.category.startswith(old_prefix + "/"):
            item.category = new_prefix + item.category[len(old_prefix):]

        # stored_filename é "pasta/uuid.ext"
        if item.stored_filename.startswith(old_prefix + "/"):
            item.stored_filename = new_prefix + item.stored_filename[len(old_prefix):]

    db.session.commit()

    flash("Pasta renomeada.", "success")
    return redirect(url_for("employee.files", path=base))


@employee_bp.route("/delete_folder", methods=["POST"])
@employee_login_required
def delete_folder():
    base = _clean_relpath(request.form.get("path", ""))
    name = (request.form.get("name") or "").strip()
    if not name:
        return redirect(url_for("employee.files", path=base))

    folder_rel = f"{base}/{name}".strip("/")
    folder_abs = _safe_abs_path(folder_rel)

    if not os.path.isdir(folder_abs):
        flash("Pasta não encontrada.", "error")
        return redirect(url_for("employee.files", path=base))

    # apaga no disco
    shutil.rmtree(folder_abs, ignore_errors=True)

    # apaga registros do banco
    to_delete = EmployeeFile.query.filter(EmployeeFile.category.like(f"{folder_rel}%")).all()
    for item in to_delete:
        db.session.delete(item)
    db.session.commit()

    flash("Pasta excluída.", "success")
    return redirect(url_for("employee.files", path=base))


@employee_bp.route("/upload", methods=["POST"])
@employee_login_required
def upload():
    current_employee = get_current_employee()
    relpath = _clean_relpath(request.form.get("path", ""))  # pasta atual

    file = request.files.get("file")
    if not file or not file.filename:
        flash("Selecione um arquivo.", "error")
        return redirect(url_for("employee.files", path=relpath))

    original = secure_filename(file.filename)
    if not _allowed_file(original):
        flash("Tipo de arquivo não permitido.", "error")
        return redirect(url_for("employee.files", path=relpath))

    # salva dentro da pasta selecionada
    ext = original.rsplit(".", 1)[1].lower()
    stored = f"{uuid.uuid4().hex}.{ext}"

    # stored_filename guarda caminho relativo
    stored_rel = f"{relpath}/{stored}".strip("/")

    abs_folder = _safe_abs_path(relpath)
    os.makedirs(abs_folder, exist_ok=True)
    abs_file = _safe_abs_path(stored_rel)
    file.save(abs_file)

    title = (request.form.get("title") or "").strip() or None
    description = (request.form.get("description") or "").strip() or None

    item = EmployeeFile(
        stored_filename=stored_rel,
        original_filename=original,
        title=title,
        description=description,
        category=relpath,  # usamos category como "pasta"
        uploader_id=current_employee.id,
    )
    db.session.add(item)
    db.session.commit()

    flash("Arquivo enviado com sucesso.", "success")
    return redirect(url_for("employee.files", path=relpath))


@employee_bp.route("/rename_file/<int:file_id>", methods=["POST"])
@employee_login_required
def rename_file(file_id: int):
    relpath = _clean_relpath(request.form.get("path", ""))
    new_title = (request.form.get("new_title") or "").strip()

    item = EmployeeFile.query.get_or_404(file_id)
    if new_title:
        item.title = new_title
        db.session.commit()
        flash("Nome exibido atualizado.", "success")
    return redirect(url_for("employee.files", path=relpath))


@employee_bp.route("/delete_file/<int:file_id>", methods=["POST"])
@employee_login_required
def delete_file(file_id: int):
    relpath = _clean_relpath(request.form.get("path", ""))
    item = EmployeeFile.query.get_or_404(file_id)

    # remove do disco
    abs_file = _safe_abs_path(item.stored_filename)
    if os.path.exists(abs_file):
        os.remove(abs_file)

    db.session.delete(item)
    db.session.commit()

    flash("Arquivo excluído.", "success")
    return redirect(url_for("employee.files", path=relpath))


@employee_bp.route("/download/<int:file_id>")
@employee_login_required
def download(file_id: int):
    item = EmployeeFile.query.get_or_404(file_id)
    root = _ensure_upload_root()

    # stored_filename é caminho relativo
    return send_from_directory(
        root,
        item.stored_filename,
        as_attachment=True,
        download_name=item.original_filename,
    )


@employee_bp.route("/download_folder")
@employee_login_required
def download_folder():
    """Baixa uma pasta como .zip (download)."""
    import tempfile
    base_rel = _clean_relpath(request.args.get("folder", ""))
    if not base_rel:
        abort(400)

    folder_abs = _safe_abs_path(base_rel)
    if not os.path.isdir(folder_abs):
        abort(404)

    # Cria zip temporário
    tmpdir = tempfile.mkdtemp(prefix="cr_folder_")
    zip_name = secure_filename(os.path.basename(base_rel) or "pasta") + ".zip"
    zip_path = os.path.join(tmpdir, zip_name)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_abs):
            for fn in files:
                abs_fp = os.path.join(root, fn)
                rel_fp = os.path.relpath(abs_fp, os.path.dirname(folder_abs))
                zf.write(abs_fp, rel_fp)

    return send_file(zip_path, as_attachment=True, download_name=zip_name)



@employee_bp.route("/preview/<int:file_id>")
@employee_login_required
def preview(file_id: int):
    """Pré-visualização inline (sem download) para imagens/PDF e outros tipos suportados."""
    # Garante mimetype correto para KML/KMZ
    mimetypes.add_type("application/vnd.google-earth.kml+xml", ".kml")
    mimetypes.add_type("application/vnd.google-earth.kmz", ".kmz")
    item = EmployeeFile.query.get_or_404(file_id)

    # Caminho absoluto seguro do arquivo no disco
    abs_path = _safe_abs_path(item.stored_filename)
    if not os.path.isfile(abs_path):
        abort(404)

    guessed_mime, _ = mimetypes.guess_type(item.original_filename or item.stored_filename)
    mimetype = guessed_mime or "application/octet-stream"

    resp = send_file(abs_path, mimetype=mimetype, as_attachment=False)

    filename = item.original_filename or os.path.basename(item.stored_filename)
    resp.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return resp
