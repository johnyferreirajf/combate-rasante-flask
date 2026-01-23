from app import create_app, db
from app.models import User


def main():
    app = create_app()

    with app.app_context():
        print("=== Usuários cadastrados ===\n")
        users = User.query.order_by(User.id).all()

        if not users:
            print("Nenhum usuário encontrado.")
            return

        for u in users:
            # tenta pegar campos comuns
            nome = getattr(u, "name", None) or getattr(u, "full_name", None) or getattr(u, "nome", "")
            email = getattr(u, "email", None) or getattr(u, "username", "")
            print(f"ID: {u.id} | Nome: {nome} | Email: {email}")


if __name__ == "__main__":
    main()
