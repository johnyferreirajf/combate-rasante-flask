"""
storage.py
Camada de abstração para armazenamento de arquivos.
- Se CLOUDINARY estiver configurado: salva/serve pelo Cloudinary (permanente)
- Caso contrário: salva no disco local (desenvolvimento)

Uso:
    from app.utils.storage import storage_save, storage_url, storage_delete, storage_list

    url = storage_save(file_stream, filename, folder="funcionarios/relatorios")
    files = storage_list(folder="funcionarios")
    storage_delete(public_id)
"""

import os
import mimetypes
from flask import current_app


# ── Cloudinary ─────────────────────────────────────────────────────────────

def _cloudinary_configured():
    return current_app.config.get("USE_CLOUDINARY", False)


def _init_cloudinary():
    import cloudinary
    cloudinary.config(
        cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=current_app.config["CLOUDINARY_API_KEY"],
        api_secret=current_app.config["CLOUDINARY_API_SECRET"],
        secure=True,
    )


def storage_save(file_stream, filename: str, folder: str = "uploads") -> dict:
    """
    Salva um arquivo e retorna dict com:
      { "url": str, "public_id": str, "source": "cloudinary"|"local" }
    """
    if _cloudinary_configured():
        return _cloudinary_save(file_stream, filename, folder)
    return _local_save(file_stream, filename, folder)


def storage_url(public_id: str, source: str = "cloudinary") -> str:
    """Retorna URL pública de um arquivo já salvo."""
    if source == "cloudinary":
        import cloudinary
        _init_cloudinary()
        from cloudinary.utils import cloudinary_url
        url, _ = cloudinary_url(public_id, resource_type="raw")
        return url
    # local: public_id é o caminho relativo ao static
    return f"/static/{public_id}"


def storage_delete(public_id: str, source: str = "cloudinary") -> bool:
    """Remove um arquivo. Retorna True se ok."""
    try:
        if source == "cloudinary":
            _init_cloudinary()
            import cloudinary.uploader
            result = cloudinary.uploader.destroy(public_id, resource_type="raw")
            return result.get("result") == "ok"
        else:
            # local
            from flask import current_app
            base = current_app.config["EMP_UPLOAD_FOLDER"]
            full = os.path.join(base, public_id)
            if os.path.exists(full):
                os.remove(full)
            return True
    except Exception:
        return False


def storage_list(folder: str = "") -> list:
    """
    Lista arquivos de uma pasta.
    Retorna lista de dicts: { name, url, public_id, size, source }
    """
    if _cloudinary_configured():
        return _cloudinary_list(folder)
    return _local_list(folder)


# ── Implementação Cloudinary ────────────────────────────────────────────────

def _cloudinary_save(file_stream, filename: str, folder: str) -> dict:
    _init_cloudinary()
    import cloudinary.uploader

    # Detecta se é imagem ou arquivo genérico
    mime, _ = mimetypes.guess_type(filename)
    resource_type = "image" if (mime and mime.startswith("image")) else "raw"

    result = cloudinary.uploader.upload(
        file_stream,
        folder=folder,
        public_id=os.path.splitext(filename)[0],
        resource_type=resource_type,
        use_filename=True,
        unique_filename=True,
        overwrite=False,
    )
    return {
        "url":       result["secure_url"],
        "public_id": result["public_id"],
        "source":    "cloudinary",
    }


def _cloudinary_list(folder: str) -> list:
    _init_cloudinary()
    import cloudinary.api

    results = []
    next_cursor = None

    while True:
        params = {"type": "upload", "prefix": folder, "max_results": 100}
        if next_cursor:
            params["next_cursor"] = next_cursor

        resp = cloudinary.api.resources(**params)
        for r in resp.get("resources", []):
            results.append({
                "name":      os.path.basename(r["public_id"]),
                "url":       r["secure_url"],
                "public_id": r["public_id"],
                "size":      r.get("bytes", 0),
                "source":    "cloudinary",
            })
        next_cursor = resp.get("next_cursor")
        if not next_cursor:
            break

    return results


# ── Implementação local (desenvolvimento) ──────────────────────────────────

def _local_save(file_stream, filename: str, folder: str) -> dict:
    from flask import current_app
    base = current_app.config.get("EMP_UPLOAD_FOLDER",
           os.path.join(current_app.instance_path, "employee_uploads"))
    dest_dir = os.path.join(base, folder)
    os.makedirs(dest_dir, exist_ok=True)

    dest = os.path.join(dest_dir, filename)
    file_stream.save(dest)

    rel = os.path.relpath(dest, os.path.join(current_app.root_path, "static"))
    return {
        "url":       f"/static/{rel.replace(os.sep, '/')}",
        "public_id": rel.replace(os.sep, "/"),
        "source":    "local",
    }


def _local_list(folder: str) -> list:
    from flask import current_app
    base = current_app.config.get("EMP_UPLOAD_FOLDER",
           os.path.join(current_app.instance_path, "employee_uploads"))
    target = os.path.join(base, folder)
    if not os.path.isdir(target):
        return []

    results = []
    for fname in sorted(os.listdir(target)):
        fpath = os.path.join(target, fname)
        if os.path.isfile(fpath):
            rel = os.path.relpath(fpath, os.path.join(
                current_app.root_path, "static")).replace(os.sep, "/")
            results.append({
                "name":      fname,
                "url":       f"/static/{rel}",
                "public_id": rel,
                "size":      os.path.getsize(fpath),
                "source":    "local",
            })
    return results
