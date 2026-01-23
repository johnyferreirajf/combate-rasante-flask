from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash


def main():
    app = create_app()

    with app.app_context():
        print("=== Redefinir senha de usuário ===\n")

        email = input("E-mail do usuário: ").strip().lower()
        new_password = input("Nova senha: ").strip()
        confirm = input("Confirmar nova senha: ").strip()

        if new_password != confirm:
            print("\nAs senhas não conferem. Tente novamente.")
            return

        user = User.query.filter_by(email=email).first()
        if not user:
            print("\nNenhum usuário encontrado com esse e-mail.")
            return

        if hasattr(User, "password_hash"):
            user.password_hash = generate_password_hash(new_password)
        elif hasattr(User, "password"):
            user.password = generate_password_hash(new_password)

        db.session.commit()

        print(f"\nSenha atualizada com sucesso para o usuário ID {user.id}.")


if __name__ == "__main__":
    main()
