from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)

    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    # current_user real (baseado na session)
    from app.utils.security import get_current_user

    @app.context_processor
    def inject_user():
        user = get_current_user()
        return {"current_user": user, "user": user}

    return app
