# create_user.py
from getpass import getpass
from werkzeug.security import generate_password_hash

from app import app, db
from app.models import User


def main():
    print("=== Criar novo usuário ===")

    nome = input("Nome: ").strip()
    email = input("E-mail: ").strip()

    # loop para garantir senha = confirmar
    while True:
        senha = getpass("Senha: ")
        confirmar = getpass("Confirmar senha: ")

        if senha != confirmar:
            print("⚠  As senhas não conferem, tente novamente.\n")
            continue
        if not senha:
            print("⚠  A senha não pode ser vazia.\n")
            continue
        break

    # verifica se já existe e-mail
    existente = User.query.filter_by(email=email).first()
    if existente:
        print("\n❌ Já existe um usuário com esse e-mail.")
        return

    # cria o usuário com NOME + EMAIL + SENHA
    usuario = User(
        name=nome,
        email=email,
        password_hash=generate_password_hash(senha),
    )

    db.session.add(usuario)
    db.session.commit()

    print("\n✅ Usuário criado com sucesso!")
    print(f"ID: {usuario.id}")
    print(f"Nome: {usuario.name}")
    print(f"E-mail: {usuario.email}")


if __name__ == "__main__":
    # garante o contexto da aplicação
    with app.app_context():
        main()
