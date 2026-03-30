"""
recreate_db.py
Recria todas as tabelas do banco com a estrutura atual dos models.
USE APENAS UMA VEZ após mudança de schema — apaga todos os dados!
"""
from app import create_app, db
from werkzeug.security import generate_password_hash
from app.models.user import User
from app.models.employee import Employee

app = create_app()

with app.app_context():
    print("⚠  Apagando todas as tabelas...")
    db.drop_all()
    print("✓  Tabelas apagadas.")

    print("🔧 Recriando tabelas com schema atualizado...")
    db.create_all()
    print("✓  Tabelas recriadas.")

    # Recriar admin cliente
    admin = User(
        name="Admin",
        email="admin@teste.com",
        password_hash=generate_password_hash("123456"),
        is_admin=True,
    )
    db.session.add(admin)

    # Recriar admin funcionário
    emp = Employee(
        name="Admin",
        username="admin123",
        password_hash=generate_password_hash("123456"),
        is_admin=True,
    )
    db.session.add(emp)
    db.session.commit()

    print("✓  Admins recriados.")
    print("✅ Banco recriado com sucesso!")
    print("")
    print("   Cliente admin: admin@teste.com / 123456")
    print("   Funcionário:   admin123 / 123456")
