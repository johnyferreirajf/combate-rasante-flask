import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # chave de sessão (pode trocar depois)
    SECRET_KEY = os.environ.get("SECRET_KEY") or "combate-rasante-dev-secret"

    # banco sqlite dentro da pasta instance
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or "sqlite:///" + os.path.join(BASE_DIR, "instance", "combate.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # pasta de upload das fotos do painel (Área do Cliente)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")

    # ✅ Área de Funcionários: arquivos compartilhados (protegido por login)
    EMP_UPLOAD_FOLDER = os.path.join(BASE_DIR, "instance", "employee_uploads")

    # tipos de arquivo permitidos na área de funcionários
    EMP_ALLOWED_EXTENSIONS = {
        "pdf", "png", "jpg", "jpeg",
        "xlsx", "xls", "csv",
        "doc", "docx",
        "ppt", "pptx",
        "zip", "rar",
        "txt",
        "kml", "kmz",
    }

    # limite de upload (global)
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB
