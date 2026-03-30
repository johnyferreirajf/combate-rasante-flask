import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # ── Segurança ──────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY") or "combate-rasante-dev-secret"

    # ── Banco de dados ─────────────────────────────────────────
    # Railway injeta DATABASE_URL automaticamente quando você adiciona PostgreSQL
    # SQLite usado apenas em desenvolvimento local
    _db_url = os.environ.get("DATABASE_URL") or \
              "sqlite:///" + os.path.join(BASE_DIR, "instance", "combate.db")

    # Railway/Render às vezes entregam "postgres://" — SQLAlchemy exige "postgresql://"
    SQLALCHEMY_DATABASE_URI = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Cloudinary (armazenamento de arquivos permanente) ──────
    # Cadastre-se em cloudinary.com e copie as credenciais do dashboard
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY     = os.environ.get("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET  = os.environ.get("CLOUDINARY_API_SECRET", "")

    # Usa Cloudinary se as credenciais estiverem configuradas
    USE_CLOUDINARY = bool(
        os.environ.get("CLOUDINARY_CLOUD_NAME") and
        os.environ.get("CLOUDINARY_API_KEY") and
        os.environ.get("CLOUDINARY_API_SECRET")
    )

    # ── Upload local (fallback / desenvolvimento) ──────────────
    UPLOAD_FOLDER     = os.path.join(BASE_DIR, "app", "static", "uploads")
    EMP_UPLOAD_FOLDER = os.path.join(BASE_DIR, "instance", "employee_uploads")

    EMP_ALLOWED_EXTENSIONS = {
        "pdf", "png", "jpg", "jpeg",
        "xlsx", "xls", "csv",
        "doc", "docx",
        "ppt", "pptx",
        "zip", "rar",
        "txt", "kml", "kmz",
    }

    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB

    # ── Proxy (Railway e Render usam proxy reverso HTTPS) ──────
    PREFERRED_URL_SCHEME = os.environ.get("PREFERRED_URL_SCHEME", "https")

    # ── Admin ──────────────────────────────────────────────────
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
