import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_key_change_me")

    # =========================
    # Email (SMTP)
    # =========================
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "1") == "1"

    # Seu gmail que vai ENVIAR o email (remetente)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")

    # Senha de app do Gmail (NÃO é sua senha normal)
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")

    # Email que vai RECEBER os contatos
    MAIL_RECEIVER = os.getenv("MAIL_RECEIVER", "johnyferreira.jf@gmail.com")

    # =========================
    # Database
    # =========================
    # Se você criar um Postgres no Render, coloque a DATABASE_URL nas env vars.
    # Se não tiver, cai automaticamente pro SQLite dentro de /instance/app.db
    DATABASE_URL = os.getenv("DATABASE_URL")

    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    else:
        # cria um caminho relativo ao projeto (funciona no Render)
        SQLALCHEMY_DATABASE_URI = "sqlite:///instance/app.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
