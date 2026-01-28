import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("config.Config")

    # ✅ garante BASE_DIR/instance (mesmo caminho usado no config.py da raiz)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.makedirs(os.path.join(project_root, "instance"), exist_ok=True)

    # (opcional, pode manter) garante também a instance do Flask
    os.makedirs(app.instance_path, exist_ok=True)

    # Banco
    db.init_app(app)

    # Importa modelos antes de criar tabelas
    from app import models  # noqa: F401

    # Cria as tabelas automaticamente
    with app.app_context():
        db.create_all()

    # Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.employee import employee_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp)

    # Context: current_user (cliente)
    from app.utils.security import get_current_user, get_current_employee

    @app.context_processor
    def inject_user():
        return {
            "current_user": get_current_user(),
            "user": get_current_user(),
            "current_employee": get_current_employee(),
        }

    return app
