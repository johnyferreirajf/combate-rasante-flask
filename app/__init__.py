import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

db = SQLAlchemy()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("config.Config")

    # garante BASE_DIR/instance (onde o config.py da raiz aponta)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.makedirs(os.path.join(project_root, "instance"), exist_ok=True)

    # (opcional) garante também a instance do Flask
    os.makedirs(app.instance_path, exist_ok=True)

    # Banco
    db.init_app(app)

    # Importa modelos antes de criar tabelas (necessário para db.create_all enxergar tudo)
    from app import models  # noqa: F401

    # Importa models diretamente
    from app.models.user import User
    from app.models.employee import Employee

    # Cria as tabelas e cria admin padrão (se não existir)
    with app.app_context():
        db.create_all()

        # Admin cliente padrão
        if not User.query.filter_by(email="admin@teste.com").first():
            admin_user = User(
                name="Admin",
                email="admin@teste.com",
                password_hash=generate_password_hash("123456"),
                is_admin=True,
            )
            db.session.add(admin_user)
            db.session.commit()

        # Admin funcionário padrão
        if not Employee.query.filter_by(username="admin123").first():
            admin_employee = Employee(
   		 name="Admin",
   		 username="admin123",
   		 password_hash=generate_password_hash("123456"),
  		 is_admin=True,
		)

            db.session.add(admin_employee)
            db.session.commit()

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
