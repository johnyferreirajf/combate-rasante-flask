"""
Rotas de "Em Campo" — feed público + CRUD admin de posts com fotos/vídeos.
"""
from __future__ import annotations
from typing import Optional

import io
import re
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, abort, current_app)
from app import db
from app.models.post import Post, PostMidia
from app.utils.security import login_required, admin_required, get_current_user

posts_bp = Blueprint("posts", __name__)

VIDEO_EXTS = {"mp4", "mov", "avi", "mkv", "webm", "m4v", "3gp"}
IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "gif", "bmp"}
VIDEO_MAX_BYTES = 100 * 1024 * 1024  # 100 MB


# ─── Helpers ──────────────────────────────────────────────────

def _youtube_embed(url: str) -> Optional[str]:
    patterns = [r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{11})"]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return "https://www.youtube.com/embed/{}?rel=0".format(m.group(1))
    return None


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _cloudinary_config():
    import cloudinary
    cloudinary.config(
        cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=current_app.config["CLOUDINARY_API_KEY"],
        api_secret=current_app.config["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    return cloudinary


def _processar_midias(post, ordem):
    """Processa arquivos (foto/vídeo) + URLs YouTube de um request POST."""
    use_cloud = current_app.config.get("USE_CLOUDINARY", False)

    arquivos = request.files.getlist("midias")
    for arq in arquivos:
        if not arq or not arq.filename:
            continue
        ext = _ext(arq.filename)
        if ext not in IMAGE_EXTS and ext not in VIDEO_EXTS:
            flash("Tipo não suportado: {}".format(arq.filename), "error")
            continue
        if not use_cloud:
            flash("Cloudinary não configurado.", "error")
            continue
        try:
            conteudo = arq.read()
            if ext in VIDEO_EXTS and len(conteudo) > VIDEO_MAX_BYTES:
                flash("Vídeo '{}' excede 100 MB.".format(arq.filename), "error")
                continue
            cld = _cloudinary_config()
            import cloudinary.uploader
            rtype = "video" if ext in VIDEO_EXTS else "image"
            tipo  = "video_direto" if ext in VIDEO_EXTS else "foto"
            result = cloudinary.uploader.upload(
                io.BytesIO(conteudo),
                folder="combaterasante/emcampo",
                resource_type=rtype,
                use_filename=True,
                unique_filename=True,
            )
            db.session.add(PostMidia(
                post_id=post.id, tipo=tipo,
                url=result["secure_url"], public_id=result["public_id"],
                ordem=ordem,
            ))
            ordem += 1
        except Exception as e:
            flash("Erro ao enviar '{}': {}".format(arq.filename, str(e)[:100]), "error")

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
            flash("URL inválida (só YouTube): {}".format(line), "error")

    return ordem


# ─── Página pública ────────────────────────────────────────────

@posts_bp.route("/em-campo")
def em_campo():
    page = request.args.get("page", 1, type=int)
    posts = None
    try:
        resultado = (Post.query.filter_by(ativo=True)
                     .order_by(Post.created_at.desc())
                     .paginate(page=page, per_page=10, error_out=False))
        if resultado is not None and resultado.items:
            posts = resultado
    except Exception:
        posts = None
    return render_template("em_campo.html", posts=posts)


# ─── Admin: listar + criar ──────────────────────────────────────

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
        db.session.flush()
        _processar_midias(post, ordem=0)
        db.session.commit()
        flash("Post publicado com sucesso!", "success")
        return redirect(url_for("posts.admin_emcampo"))

    try:
        posts = Post.query.order_by(Post.created_at.desc()).all()
    except Exception:
        posts = []
    return render_template("admin_emcampo.html",
                           current_user=get_current_user(),
                           posts=posts)


# ─── Admin: editar ─────────────────────────────────────────────

@posts_bp.route("/admin/emcampo/editar/<int:pid>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_emcampo_editar(pid):
    post = Post.query.get_or_404(pid)
    if request.method == "POST":
        post.titulo    = (request.form.get("titulo")    or "").strip() or post.titulo
        post.descricao = (request.form.get("descricao") or "").strip()
        post.ativo     = request.form.get("ativo") == "1"
        ordem = max((m.ordem for m in post.midias), default=-1) + 1
        _processar_midias(post, ordem=ordem)
        db.session.commit()
        flash("Post atualizado!", "success")
        return redirect(url_for("posts.admin_emcampo_editar", pid=post.id))
    return render_template("admin_emcampo_editar.html",
                           current_user=get_current_user(),
                           post=post)


# ─── Admin: excluir mídia ──────────────────────────────────────

@posts_bp.route("/admin/emcampo/midia/excluir/<int:mid>", methods=["POST"])
@login_required
@admin_required
def admin_emcampo_midia_excluir(mid):
    midia = PostMidia.query.get_or_404(mid)
    post_id = midia.post_id
    if midia.public_id and midia.tipo in ("foto", "video_direto"):
        try:
            import cloudinary.uploader
            cld = _cloudinary_config()
            rtype = "video" if midia.tipo == "video_direto" else "image"
            cloudinary.uploader.destroy(midia.public_id, resource_type=rtype)
        except Exception:
            pass
    db.session.delete(midia)
    db.session.commit()
    flash("Mídia removida.", "success")
    return redirect(url_for("posts.admin_emcampo_editar", pid=post_id))


# ─── Admin: excluir post ───────────────────────────────────────

@posts_bp.route("/admin/emcampo/excluir/<int:pid>", methods=["POST"])
@login_required
@admin_required
def admin_emcampo_excluir(pid):
    post = Post.query.get_or_404(pid)
    use_cloud = current_app.config.get("USE_CLOUDINARY", False)
    if use_cloud:
        try:
            import cloudinary.uploader
            cld = _cloudinary_config()
            for m in post.midias:
                if m.public_id and m.tipo in ("foto", "video_direto"):
                    try:
                        rtype = "video" if m.tipo == "video_direto" else "image"
                        cloudinary.uploader.destroy(m.public_id, resource_type=rtype)
                    except Exception:
                        pass
        except Exception:
            pass
    db.session.delete(post)
    db.session.commit()
    flash("Post excluído.", "success")
    return redirect(url_for("posts.admin_emcampo"))
