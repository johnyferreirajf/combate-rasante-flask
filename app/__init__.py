import os
from flask import Flask
from .extensions import db

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # ✅ garante a pasta instance/
    os.makedirs(app.instance_path, exist_ok=True)

    # ✅ carrega config.py (se você usa)
    app.config.from_object("config.Config")

    # ✅ banco no Render (se tiver postgres)
    db_url = os.environ.get("DATABASE_URL")

    # Render às vezes vem com postgres:// e precisa ser postgresql://
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # ✅ se não tiver DATABASE_URL, usa SQLite na pasta instance/
    sqlite_db_path = os.path.join(app.instance_path, "app.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url or f"sqlite:///{sqlite_db_path}"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # ✅ IMPORTANTE: importar models antes do create_all
    with app.app_context():
        from app.models.employee import Employee
        from app.models.employee_file import EmployeeFile
        # (se tiver outros models, pode importar aqui também)
        db.create_all()

    # seus blueprints
    from app.routes.main import main_bp
    from app.routes.employee import employee_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(employee_bp)

    return app
