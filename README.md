# 🚀 RepoPilot

AI-powered GitHub repository analysis, code modification, repair, and Pull Request automation.

## 🔗 Demo

[Live Demo](https://repopilotdemolink-cv6x5qntvafjxwd5ag8bzg.streamlit.app/)

## 🛠️ Tech Stack

- React + Vite
- Express.js
- PostgreSQL
- FastAPI + Python
- LangGraph
- Mistral AI
- ChromaDB
- GitHub API
- Docker & Docker Compose
- Caddy

## 🏗️ Architecture

```text
React + Vite
     ↓
Express.js
(Auth • Permissions • Audit)
     ↓
FastAPI
(LangGraph • Mistral • ChromaDB)
     ↓
GitHub Repository
```

## ✨ Features

- 🤖 AI-powered repository analysis
- 🔍 Hybrid semantic + lexical code retrieval
- 🔧 Automated code modification
- 🩹 AI-powered code repair
- 🔐 JWT + bcrypt authentication
- 🔑 AES-256-GCM encrypted GitHub tokens
- 🛡️ Prompt-injection protection
- 👥 Permission-based access control
- 📋 Audit logging
- 🐳 Docker sandbox
- 🔄 Git commit, push & Pull Request workflow

## 🔄 Workflow

```text
READ → ANALYZE → WRITE → COMMIT → PUSH → PR
```

## 📁 Project Structure

```text
RepoPilot/
├── ai-service/
├── backend/
├── frontend/
├── .env.example
├── docker-compose.yml
└── README.md
```

## 🚀 Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/Akanksha-198/RepoPilot.git
cd RepoPilot
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and add your own values:

```env
JWT_SECRET=
ENCRYPTION_KEY=
INTERNAL_API_KEY=
POSTGRES_PASSWORD=
MISTRAL_API_KEY=
```

> Never commit `.env`, API keys, passwords, or tokens to GitHub.

### 3. Start with Docker

```bash
docker compose up -d --build
```

Open:

```text
http://localhost
```

## 🌐 Free Public Demo

For a temporary free public link using Cloudflare:

```bash
cloudflared tunnel --url http://localhost:80
```

Cloudflare will generate a temporary URL:

```text
https://xxxx.trycloudflare.com
```

> Keep the Cloudflare terminal running while the public demo is active.

## 🔐 Security

RepoPilot includes:

- JWT authentication with HttpOnly cookies
- bcrypt password hashing
- CSRF protection
- Rate limiting
- Encrypted GitHub credentials
- Prompt-injection detection
- Protected `.env`, `.git`, CI workflows and secret files
- Docker isolation with restricted capabilities
- Audit logging

