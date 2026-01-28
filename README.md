# Combate Rasante (Flask)

Projeto Flask pronto para subir no GitHub e fazer deploy no Render.

## Estrutura (principal)
- `app/` -> aplicação Flask (factory + blueprints)
- `wsgi.py` -> entrypoint para Gunicorn/Render
- `requirements.txt` -> dependências (inclui `gunicorn` e `psycopg2-binary`)
- `Procfile` -> comando web padrão (compatível com Render/Heroku)
- `render.yaml` -> configuração opcional (Infra as Code) para Render
- `instance/` -> **não** vai para o Git (SQLite/uploads) — criado automaticamente em runtime

## Rodar local (Windows / CMD)
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set FLASK_ENV=development
python run.py
```

Acesse: http://127.0.0.1:5000

## Deploy no Render (Web Service)
1. Suba este repositório para o GitHub (sem `.venv/`, sem `.git/` dentro do ZIP, sem banco).
2. No Render: **New > Web Service > Connect GitHub repo**
3. Configure:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app`
4. Em **Environment Variables**, adicione:
   - `SECRET_KEY` (qualquer string forte)
   - (Opcional) `DATABASE_URL` se você for usar Postgres no Render

### Postgres no Render
Se você criar um banco Postgres no Render, copie a connection string para `DATABASE_URL`.
Este projeto já faz o ajuste automático de `postgres://` -> `postgresql://` quando necessário.

## Observações importantes
- O SQLite dentro de `instance/` funciona para testes, mas no Render ele é **efêmero** (reinícios podem perder dados).
- Para produção, prefira Postgres (Render Database) com `DATABASE_URL`.
