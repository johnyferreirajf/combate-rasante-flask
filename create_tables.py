from app import create_app, db
from app.models import User, Photo  # importe todos os models que tiver

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Tabelas criadas com sucesso.")
