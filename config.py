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

    # pasta de upload das fotos do painel
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
