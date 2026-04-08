"""
Rotas de "Em Campo" — feed público + CRUD admin de posts com fotos/vídeos.
"""
import re
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, abort, current_app)
from app import db
from app.models.post import Post, PostMidia
from app.utils.security import login_required, admin_required, get_current_user

posts_bp = Blueprint("posts", __name__)


# ─── Helpers ──────────────────────────────────────────────────

def _youtube_embed(url: str) -> str | None:
    """Converte URL do YouTube para URL de embed."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return f"https://www.youtube.com/embed/{m.group(1)}?rel=0"
    return None


def _upload_cloudinary(file_stream, folder="combaterasante/emcampo"):
    """Faz upload para Cloudinary e retorna (url, public_id)."""
    import cloudinary, cloudinary.uploader
    cloudinary.config(
        cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=current_app.config["CLOUDINARY_API_KEY"],
        api_secret=current_app.config["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    result = cloudinary.uploader.upload(
        file_stream,
        folder=folder,
        resource_type="image",
        transformation=[{"quality": "auto", "fetch_format": "auto"}],
    )
    return result["secure_url"], result["public_id"]


# ─── Página pública: feed "Em Campo" ──────────────────────────

@posts_bp.route("/em-campo")
def em_campo():
    page = request.args.get("page", 1, type=int)
    try:
        posts = (Post.query
                 .filter_by(ativo=True)
                 .order_by(Post.created_at.desc())
                 .paginate(page=page, per_page=10, error_out=False))
        # Garante que posts.items existe (algumas versões retornam None)
        if posts is None or not hasattr(posts, "items"):
            posts = None
    except Exception:
        posts = None

    return render_template("em_campo.html", posts=posts)


# ─── Admin: listar posts + criar novo post (formulário inline) ─

@posts_bp.route("/admin/emcampo", methods=["GET", "POST"])
@login_required
@admin_required
def admin_emcampo():
    if request.method == "POST":
        titulo    = (request.form.get("titulo")   or "").strip()
        descricao = (request.form.get("descricao") or "").strip()

        if not titulo:
            flash("Informe o título do post.", "error")
            return redirect(url_for("posts.admin_emcampo"))

        post = Post(titulo=titulo, descricao=descricao)
        db.session.add(post)
        db.session.flush()   # gera post.id antes do commit

        ordem = 0

        # Fotos (múltiplas)
        fotos = request.files.getlist("fotos")
        use_cloud = current_app.config.get("USE_CLOUDINARY", False)
        for foto in fotos:
            if not foto or not foto.filename:
                continue
            if use_cloud:
                try:
                    url, pid = _upload_cloudinary(foto.stream)
                    db.session.add(PostMidia(post_id=post.id, tipo="foto",
                                            url=url, public_id=pid, ordem=ordem))
                    ordem += 1
                except Exception as e:
                    flash(f"Erro ao enviar foto: {e}", "error")

        # Vídeos YouTube (URLs em textarea, uma por linha)
        videos_raw = (request.form.get("videos") or "")
        for line in videos_raw.splitlines():
            line = line.strip()
            if not line:
                continue
            embed = _youtube_embed(line)
            if embed:
                db.session.add(PostMidia(post_id=post.id, tipo="video",
                                        url=embed, ordem=ordem))
                ordem += 1
            else:
                flash(f"URL de vídeo inválida (só YouTube): {line}", "error")

        db.session.commit()
        flash("Post publicado com sucesso!", "success")
        return redirect(url_for("posts.admin_emcampo"))

    # GET
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("admin_emcampo.html",
                           current_user=get_current_user(),
                           posts=posts)


# ─── Admin: editar post ───────────────────────────────────────

@posts_bp.route("/admin/emcampo/editar/<int:pid>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_emcampo_editar(pid):
    post = Post.query.get_or_404(pid)

    if request.method == "POST":
        post.titulo    = (request.form.get("titulo")    or "").strip() or post.titulo
        post.descricao = (request.form.get("descricao") or "").strip()
        post.ativo     = request.form.get("ativo") == "1"

        use_cloud = current_app.config.get("USE_CLOUDINARY", False)
        ordem = max((m.ordem for m in post.midias), default=-1) + 1

        # Novas fotos
        fotos = request.files.getlist("fotos")
        for foto in fotos:
            if not foto or not foto.filename:
                continue
            if use_cloud:
                try:
                    url, pid2 = _upload_cloudinary(foto.stream)
                    db.session.add(PostMidia(post_id=post.id, tipo="foto",
                                            url=url, public_id=pid2, ordem=ordem))
                    ordem += 1
                except Exception as e:
                    flash(f"Erro ao enviar foto: {e}", "error")

        # Novos vídeos
        videos_raw = (request.form.get("videos") or "")
        for line in videos_raw.splitlines():
            line = line.strip()
            if not line:
                continue
            embed = _youtube_embed(line)
            if embed:
                db.session.add(PostMidia(post_id=post.id, tipo="video",
                                        url=embed, ordem=ordem))
                ordem += 1
            else:
                flash(f"URL inválida: {line}", "error")

        db.session.commit()
        flash("Post atualizado!", "success")
        return redirect(url_for("posts.admin_emcampo_editar", pid=post.id))

    return render_template("admin_emcampo_editar.html",
                           current_user=get_current_user(),
                           post=post)


# ─── Admin: excluir mídia individual ─────────────────────────

@posts_bp.route("/admin/emcampo/midia/excluir/<int:mid>", methods=["POST"])
@login_required
@admin_required
def admin_emcampo_midia_excluir(mid):
    midia = PostMidia.query.get_or_404(mid)
    post_id = midia.post_id

    if midia.tipo == "foto" and midia.public_id:
        try:
            import cloudinary, cloudinary.uploader
            cloudinary.config(
                cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
                api_key=current_app.config["CLOUDINARY_API_KEY"],
                api_secret=current_app.config["CLOUDINARY_API_SECRET"],
                secure=True,
            )
            cloudinary.uploader.destroy(midia.public_id, resource_type="image")
        except Exception:
            pass

    db.session.delete(midia)
    db.session.commit()
    flash("Mídia removida.", "success")
    return redirect(url_for("posts.admin_emcampo_editar", pid=post_id))


# ─── Admin: excluir post inteiro ─────────────────────────────

@posts_bp.route("/admin/emcampo/excluir/<int:pid>", methods=["POST"])
@login_required
@admin_required
def admin_emcampo_excluir(pid):
    post = Post.query.get_or_404(pid)

    use_cloud = current_app.config.get("USE_CLOUDINARY", False)
    if use_cloud:
        try:
            import cloudinary, cloudinary.uploader
            cloudinary.config(
                cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
                api_key=current_app.config["CLOUDINARY_API_KEY"],
                api_secret=current_app.config["CLOUDINARY_API_SECRET"],
                secure=True,
            )
            for m in post.midias:
                if m.tipo == "foto" and m.public_id:
                    try:
                        cloudinary.uploader.destroy(m.public_id, resource_type="image")
                    except Exception:
                        pass
        except Exception:
            pass

    db.session.delete(post)
    db.session.commit()
    flash("Post excluído.", "success")
    return redirect(url_for("posts.admin_emcampo"))
