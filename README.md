# RepoPilot

React (Vite) -> Express (auth, Postgres, audit, permissions) -> FastAPI (LangGraph agent, ChromaDB, Git tools).

Setup: copy your existing `app/` folder into `ai-service/app/` and your dependency list into `ai-service/requirements.txt`,
then `cp .env.example .env`, fill it in and run `docker compose up -d --build`. Open http://localhost.
See the chat instructions for the full step-by-step guide.
