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
