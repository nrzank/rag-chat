# RAG Chat

RAG chatbot: upload documents, chunk & embed them, search via Qdrant,
stream LLM answers with retrieved context. Portfolio / pet project.

## Stack

- **Backend:** FastAPI + SQLAlchemy 2.0 async + asyncpg + PostgreSQL 17
- **Vector DB:** Qdrant v1.12
- **LLM:** OpenAI (gpt-4o-mini chat, text-embedding-3-small embeddings)
- **Streaming:** SSE via sse-starlette
- **Document parsing:** pypdf, python-docx
- **Config:** pydantic-settings, `.env` in repo root
- **Package manager:** uv, Python 3.12
- **Frontend:** React + TypeScript (planned)

## Layout

```
backend/
├── api/v1/          # FastAPI routers
├── app/             # services (chat, documents)
├── core/            # config, database, qdrant client
├── migrations/      # Alembic
└── workers/tasks/   # background jobs (chunking, embedding)
frontend/            # React app (planned)
docker-compose.yml   # PostgreSQL + Qdrant
```

## Running locally

```bash
docker compose up -d
cd backend && uv run uvicorn app.main:app --reload
```

## Workflow

Solo project. Work on `main`. No branches, no PRs.
Never commit `.env` or real API keys.
