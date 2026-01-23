import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "devkey")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ✅ não força sqlite em lugar errado no Render
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
