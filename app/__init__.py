from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # Banco
    db.init_app(app)

    # Importa modelos antes de criar tabelas (necessário para db.create_all enxergar tudo)
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