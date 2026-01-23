# create_employee.py
from getpass import getpass

from app import create_app, db
from app.models import Employee


def main():
    print("=== Criar novo funcionário ===")

    nome = input("Nome: ").strip()
    username = input("Usuário (login): ").strip()

    while True:
        senha = getpass("Senha: ")
        confirmar = getpass("Confirmar senha: ")
        if senha != confirmar:
            print("❌ Senhas não conferem. Tente novamente.")
            continue
        if len(senha) < 4:
            print("❌ Senha muito curta. Use pelo menos 4 caracteres.")
            continue
        break

    is_admin = input("É administrador? (s/N): ").strip().lower() == "s"

    if not nome or not username:
        print("❌ Nome e usuário são obrigatórios.")
        return

    if Employee.query.filter_by(username=username).first():
        print("❌ Já existe um funcionário com esse usuário.")
        return

    emp = Employee(name=nome, username=username, is_admin=is_admin)
    emp.set_password(senha)

    db.session.add(emp)
    db.session.commit()

    print("\n✅ Funcionário criado com sucesso!")
    print(f"ID: {emp.id}")
    print(f"Nome: {emp.name}")
    print(f"Usuário: {emp.username}")
    print(f"Admin: {emp.is_admin}")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        main()