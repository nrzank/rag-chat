# Project status

Update this after every completed step. It is the first thing an agent picking
up the work should read.

Updated: 2026-10-18

## In short

Backend and frontend both work, including background processing through a job
queue. The full cycle has not been verified: there is no working OpenAI key, so
indexing and answer generation fail with a 401. Everything else — CRUD,
statuses, the queue with its retries, streaming, error handling — was checked
in the browser.

## Done

| Area | State |
|---|---|
| Project layout, uv, Python 3.12 | Done |
| Configuration (pydantic-settings) | Done, validates chunking parameters |
| PostgreSQL + async SQLAlchemy 2.0 | Done |
| Alembic | Done, 3 migrations applied |
| Documents domain | Done: models, repositories, service |
| PDF / DOCX / TXT parsing | Done |
| Chunking with overlap | Done, infinite-loop bug fixed |
| OpenAI client | Done: batched embeddings, chat, streaming |
| Qdrant client | Done: collection, upsert, search, delete |
| Document indexing | Done, idempotent |
| Chat domain | Done: conversations, messages, sources |
| RAG retrieval and prompt building | Done |
| Answer streaming over SSE | Done: sources / token / done / error events |
| Typed errors | Done, one `{code, message, params}` shape |
| Job queue | Done: LISTEN/NOTIFY, leases, retries with backoff, dedupe |
| Background indexing | Done: `process` returns 202, the worker does the work |
| Linter and formatter (ruff) | Done, passes clean |
| CI | Done: GitHub Actions, two jobs — backend and frontend |
| CORS | Done, origin from settings |
| Frontend | Done: documents, conversations, streaming, sources |
| Backend tests | 37: property-based over the chunker, functional over the document, chat and queue services |
| Frontend tests | 5 over SSE parsing (vitest) |
| Dockerfile + docker-compose | Done: multi-stage, non-root, healthcheck, worker service |

## Database schema

| Table | Purpose |
|---|---|
| `documents` | Uploaded files and their processing status |
| `chunks` | Text chunks, each pointing at a Qdrant point |
| `conversations` | Dialogues |
| `messages` | Turns, with sources in JSONB |
| `worker_jobs` | Background job queue |

Every table inherits `id`, `created_at` and `updated_at` from `Base`.

## Next

1. Run the full cycle with a working OpenAI key: upload → indexing → question →
   streamed answer with sources
2. Screenshots of the UI and a demo of the streaming in the README

## Known debt

Deliberate trade-offs, not bugs. Touch only when explicitly asked.

- One worker, with no per-kind concurrency budget. Fine for a single job kind;
  separate pools would be needed as it grows.
- No dead-letter storage: an exhausted job is deleted, and the only trace left
  is the document status and the logs.
- Migrations do not run on container start. Deliberate: several replicas would
  race. Run them as a separate deployment step.
- `app/chat/ports.py` imports `SearchHit` from `core.qdrant`. Strict DDD would
  want a domain type and an adapter — that would be a twin class with no
  differences.
- No upload size limit.
- Token usage is not tracked anywhere.
- Uploading a file through the UI was not verified in a browser: a hidden
  `input[type=file]` cannot be driven by automation. It was tested through the API.
- The `api` container is stopped: port 8001 clashed with the local uvicorn.
  Development needs the local server with hot reload. Bring it back with
  `docker compose up -d --build api`.

## How to check everything still works

```bash
docker compose up -d db qdrant
cd backend && uv run alembic upgrade head
cd backend && uv run pytest -q          # 37 passed
cd backend && uv run ruff check .       # All checks passed
cd backend && uv run uvicorn main:app --reload --port 8001
cd backend && uv run python -m workers.runner   # in another terminal

cd frontend && npm install
cd frontend && npx vitest run           # 5 passed
cd frontend && npm run dev              # http://localhost:5173
```
