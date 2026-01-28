# COMBATE RASANTE Aviação Agrícola - Flask

Este projeto é a versão em Flask + HTML/CSS/JS puro da aplicação original em React (Lovable),
para o site **COMBATE RASANTE Aviação Agrícola**.

## Estrutura

```
combate_rasante_flask/
  app/
    __init__.py
    config.py
    models/
      __init__.py
      user.py
    routes/
      __init__.py
      main.py
      auth.py
    utils/
      __init__.py
      security.py
    templates/
      layout.html
      home.html
      contato.html
      login.html
      dashboard.html
      admin.html
      not_found.html
      partials/
        navbar.html
        footer.html
    static/
      css/
        main.css
      js/
        main.js
      img/
        hero-aviation.jpg
        aircraft-fleet.jpg
        technology-gps.jpg
        sugarcane-field.jpg
  run.py
  requirements.txt
  .env.example
```

## Como rodar

1. Crie e ative um ambiente virtual (opcional, mas recomendado):

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate   # Windows
   ```

2. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Crie o arquivo `.env` com base no `.env.example` e ajuste os valores.

4. Inicialize o banco de dados:

   ```bash
   flask --app run db init
   flask --app run db migrate -m "create users table"
   flask --app run db upgrade
   ```

   Opcionalmente, crie manualmente um usuário administrador no banco, definindo `is_admin = True`
   e o e-mail igual ao `ADMIN_EMAIL` configurado.

5. Execute a aplicação:

   ```bash
   flask --app run run
   ```

   A aplicação estará disponível em `http://127.0.0.1:5000`.

## Observações

- Todo o CSS e JS estão em arquivos externos, sem scripts inline, permitindo uso de CSP estrita.
- A autenticação foi reimplementada em Flask com SQLite/SQLAlchemy, inspirada no fluxo original com Supabase.
- O painel do cliente usa dados estáticos de exemplo; é possível integrar com seu banco real no futuro.
