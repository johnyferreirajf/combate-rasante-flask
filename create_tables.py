from app import create_app, db
from app.models import User, Photo, ContactMessage, Employee, EmployeeFile  # noqa: F401

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("✅ Tabelas criadas com sucesso.")
