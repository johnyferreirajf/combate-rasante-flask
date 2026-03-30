# Deploy no Railway — Passo a Passo

## 1. Criar conta e projeto no Railway

1. Acesse https://railway.app e crie sua conta (pode usar o GitHub)
2. Clique em **"New Project"**
3. Escolha **"Deploy from GitHub repo"**
4. Selecione o repositório do projeto

---

## 2. Adicionar PostgreSQL (banco permanente)

1. No projeto Railway, clique em **"+ New"**
2. Escolha **"Database" → "PostgreSQL"**
3. O Railway cria o banco e injeta `DATABASE_URL` automaticamente no serviço
4. **Não precisa configurar nada** — o código já lê `DATABASE_URL` do ambiente

---

## 3. Configurar variáveis de ambiente

No Railway, vá em **"Variables"** do seu serviço web e adicione:

```
SECRET_KEY          = (gere uma chave aleatória em https://djecrety.ir)
ADMIN_EMAIL         = seuemail@exemplo.com
PREFERRED_URL_SCHEME = https

# Cloudinary (para arquivos e fotos permanentes)
CLOUDINARY_CLOUD_NAME = (do seu painel Cloudinary)
CLOUDINARY_API_KEY    = (do seu painel Cloudinary)
CLOUDINARY_API_SECRET = (do seu painel Cloudinary)
```

> `DATABASE_URL` é injetado automaticamente pelo Railway — não precisa adicionar.

---

## 4. Configurar Cloudinary (gratuito, 25GB)

1. Acesse https://cloudinary.com e crie conta gratuita
2. No Dashboard, copie: **Cloud Name**, **API Key**, **API Secret**
3. Cole nas variáveis de ambiente do Railway (passo 3)

---

## 5. Fazer o deploy

1. Faça push do código para o GitHub
2. O Railway detecta automaticamente e faz o deploy
3. Acesse a URL gerada (ex: `seu-projeto.up.railway.app`)

---

## 6. Após o primeiro deploy

O sistema cria automaticamente:
- Conta admin cliente: `admin@teste.com` / `123456`
- Conta admin funcionário: `admin123` / `123456`

**IMPORTANTE: Troque essas senhas imediatamente pelo painel `/admin`**

---

## Estrutura de variáveis obrigatórias no Railway

| Variável | Obrigatória | Descrição |
|---|---|---|
| `SECRET_KEY` | ✅ Sim | Chave de segurança da sessão |
| `ADMIN_EMAIL` | ✅ Sim | E-mail do administrador |
| `DATABASE_URL` | Auto | Injetado pelo PostgreSQL do Railway |
| `CLOUDINARY_CLOUD_NAME` | Para arquivos | Painel Cloudinary |
| `CLOUDINARY_API_KEY` | Para arquivos | Painel Cloudinary |
| `CLOUDINARY_API_SECRET` | Para arquivos | Painel Cloudinary |
| `PREFERRED_URL_SCHEME` | ✅ Sim | Sempre `https` |

---

## Criando contas após o deploy

### Cliente (Área do Cliente)
Acesse `/admin` no site logado como admin.

### Funcionário
Acesse `/admin` → clique em **"Funcionários"** no menu superior.

