
import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_key_change_me")

    # =========================
    # Email (SMTP)
    # =========================
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "1") == "1"

    # Gmail utilizado para enviar mensagens
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")

    # Senha de aplicativo do Gmail
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")

    # Email que recebe os contatos
    MAIL_RECEIVER = os.getenv(
        "MAIL_RECEIVER",
        "johnyferreira.jf@gmail.com",
    )

    # =========================
    # Database
    # =========================
    DATABASE_URL = os.getenv("DATABASE_URL")

    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace(
            "postgres://",
            "postgresql://",
            1,
        )
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///instance/app.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # =========================
    # Apple App Store Server API
    # =========================

    # Identificador do aplicativo na Apple
    APPLE_BUNDLE_ID = os.getenv(
        "APPLE_BUNDLE_ID",
        "br.com.combaterasante.app",
    )

    # Identificador do emissor da chave Apple
    APPLE_ISSUER_ID = os.getenv("APPLE_ISSUER_ID", "")

    # Identificador da chave de compras integradas
    APPLE_KEY_ID = os.getenv("APPLE_KEY_ID", "")

    # Conteudo da chave privada .p8
    # Deve ser configurada somente no servidor.
    APPLE_PRIVATE_KEY = os.getenv(
        "APPLE_PRIVATE_KEY",
        "",
    ).replace("\\n", "\n")

    # Produtos Premium cadastrados na App Store
    APPLE_PREMIUM_MONTHLY_ID = (
        "combate_rasante_premium_mensal"
    )

    APPLE_PREMIUM_ANNUAL_ID = (
        "combate_rasante_premium_anual"
    )

    # App Store Connect App ID
    APPLE_APP_ID = 6831711363

    # Ambiente oficial e ambiente de testes
    APPLE_PRODUCTION_URL = (
        "https://api.storekit.apple.com"
    )

    APPLE_SANDBOX_URL = (
        "https://api.storekit-sandbox.apple.com"
    )
