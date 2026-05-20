FROM python:3.12-slim

# Dependências do sistema necessárias para o Playwright/Chromium
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    # Chromium headless deps
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar apenas o Chromium do Playwright (sem Firefox/WebKit)
RUN playwright install chromium

COPY . .

EXPOSE $PORT

CMD gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
