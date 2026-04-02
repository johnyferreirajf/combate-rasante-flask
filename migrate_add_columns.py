"""
migrate_add_columns.py
Adiciona colunas novas ao banco sem apagar dados existentes.
Execute UMA VEZ via Pre-deploy Command no Railway, depois remova.
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    conn = db.engine.connect()

    # Colunas a adicionar: (tabela, coluna, tipo SQL)
    colunas = [
        ("employee_files", "cloudinary_url",       "TEXT"),
        ("employee_files", "cloudinary_public_id",  "VARCHAR(255)"),
        ("employee_files", "file_size",             "INTEGER"),
        ("sector_orders",  "id",                    None),  # tabela nova — criar_all resolve
        ("sector_orders",  "setor",                 None),
        ("sector_orders",  "posicao",               None),
    ]

    # Criar tabelas novas (sector_orders)
    db.create_all()
    print("✓ Tabelas novas criadas (se não existiam)")

    # Adicionar colunas novas nas tabelas existentes
    for tabela, coluna, tipo in colunas:
        if tipo is None:
            continue  # tabela nova já foi criada pelo create_all
        try:
            conn.execute(text(
                f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS {coluna} {tipo}"
            ))
            conn.commit()
            print(f"✓ {tabela}.{coluna} adicionada")
        except Exception as e:
            print(f"~ {tabela}.{coluna}: {e}")

    conn.close()
    print("\n✅ Migration concluída!")
