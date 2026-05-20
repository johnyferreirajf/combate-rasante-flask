FROM python:3.12-slim

WORKDIR /app

# Apenas o essencial para psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright instala o Chromium com APENAS as deps necessárias
# (muito menor que apt-get install manual)
RUN playwright install --with-deps chromium \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE $PORT

CMD gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
