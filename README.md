# RAG Chat

[![CI](https://github.com/nrzank/rag-chat/actions/workflows/ci.yml/badge.svg)](https://github.com/nrzank/rag-chat/actions/workflows/ci.yml)

A chatbot that answers questions about your own documents. Upload a PDF, DOCX
or TXT file — the service splits it into chunks, builds embeddings and stores
them in a vector database. Ask a question in natural language and the answer
streams back, with links to the chunks it was built from.

Pet project. The goal was to build a production-shaped RAG service end to end:
from file upload to a streamed answer, with layered architecture, migrations,
typed errors, a background queue and tests.

## Features

- Upload and parse PDF, DOCX and TXT
- Chunking with overlap
- Batched embedding generation (OpenAI)
- Vector search through Qdrant with a per-document filter
- Answers streamed over Server-Sent Events
- Conversation history that keeps the sources of every answer
- Idempotent re-indexing: processing a document twice does not duplicate data
- Background processing on a PostgreSQL `LISTEN/NOTIFY` queue with leases,
  retries and exponential backoff

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Pydantic v2, sse-starlette |
| Data | PostgreSQL 17, SQLAlchemy 2.0 (async), asyncpg, Alembic |
| Vectors | Qdrant |
| LLM | OpenAI SDK — gpt-4o-mini, text-embedding-3-small |
| Parsing | pypdf, python-docx |
| Frontend | React 19, TypeScript, Vite, Tailwind |
| Tooling | uv, ruff, pytest, Hypothesis, vitest, Docker Compose |

## Quick start

You need Docker and [uv](https://docs.astral.sh/uv/).

1. Create the env files:

```bash
cp .env.example backend/.env
```

Put a real `OPENAI_API_KEY` into `backend/.env`. Docker Compose reads its own
`.env` from the repo root, so put the same key there too.

2. Start the infrastructure:

```bash
docker compose up -d db qdrant
```

3. Apply migrations:

```bash
cd backend && uv run alembic upgrade head
```

4. Start the API:

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8001
```

5. Start the worker in another terminal — it does the document processing:

```bash
cd backend && uv run python -m workers.runner
```

6. Start the frontend:

```bash
cd frontend && npm install && npm run dev
```

The UI is at http://localhost:5173, Swagger at http://localhost:8001/docs.

Everything in containers instead:

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
```

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/documents/` | Upload a file |
| `POST` | `/api/v1/documents/{id}/process` | Enqueue for indexing, returns `202` |
| `GET` | `/api/v1/documents/` | List documents |
| `GET` | `/api/v1/documents/{id}` | Get one document |
| `DELETE` | `/api/v1/documents/{id}` | Delete the document, its chunks and vectors |
| `POST` | `/api/v1/conversations/` | Create a conversation |
| `GET` | `/api/v1/conversations/` | List conversations |
| `GET` | `/api/v1/conversations/{id}` | Conversation with its message history |
| `DELETE` | `/api/v1/conversations/{id}` | Delete a conversation |
| `POST` | `/api/v1/conversations/{id}/ask` | Ask a question, answer streams back over SSE |

### Document processing

`POST /documents/{id}/process` enqueues a job and returns `202` immediately with
status `queued`. The document then moves through `queued → processing →
ready | failed`; the UI polls until the status is terminal.

The queue lives in the `worker_jobs` table. Jobs are claimed with
`FOR UPDATE SKIP LOCKED` plus a lease, `pg_notify` is a wake-up hint for
immediate pickup, and polling every few seconds is the fallback. A failed job
goes back to the queue after 10s, 60s, 300s; once attempts run out the document
is marked `failed`.

### Answer stream

`POST /conversations/{id}/ask` returns an SSE stream of three event types:

```
event: sources
data: {"sources": [{"document_id": 1, "chunk_index": 4, "score": 0.82}]}

event: token
data: {"text": "According to "}

event: done
data: {"message_id": 17}
```

Sources arrive before the first token, so the UI can show which documents the
answer is being built from while the model is still generating. On failure an
`error` event carries `{code, message, params}`.

### Errors

One shape across every endpoint:

```json
{"code": "document_not_found", "message": "Document not found", "params": {"document_id": 999}}
```

`code` is stable and meant for the client; `params` is structured data to fill
into a localized message. Debug detail never leaves the logs.

## Architecture

Layers and dependency direction are in [AGENTS.md](AGENTS.md).
Domain and invariants are in [docs/CONTEXT.md](docs/CONTEXT.md).
Current state of the work is in [docs/STATUS.md](docs/STATUS.md).

```
backend/
├── api/              # HTTP: routers, dependencies, exception handlers
│   └── v1/
├── app/              # Domain and business logic
│   ├── base/         # Typed exceptions
│   ├── chat/         # Conversations, RAG retrieval, streaming
│   ├── documents/    # Upload, parsing, chunking, indexing
│   └── jobs/         # Job queue
├── core/             # Infrastructure: config, DB, Qdrant, OpenAI
├── migrations/       # Alembic
├── workers/          # Background runner and the tasks it executes
└── tests/
```

Every domain under `app/` is laid out the same way:

| File | Purpose |
|---|---|
| `models.py` | Domain entities — dataclasses, no framework dependencies |
| `db_models.py` | SQLAlchemy ORM models |
| `repository.py` | Storage protocols |
| `repository_impl.py` | SQLAlchemy implementation of those protocols |
| `ports.py` | Protocols for external services (embedder, vectors, LLM) |
| `service.py` | Use cases |
| `schemas.py` | Pydantic DTOs for the API |

## Development

```bash
cd backend
uv run ruff check .      # linter
uv run ruff format .     # formatter
uv run pytest -q         # tests

cd frontend
npx vitest run           # tests
npm run build            # type check and build
```

New migration:

```bash
cd backend && uv run alembic revision --autogenerate -m "description"
```

CI runs on every push and pull request to `main`
([.github/workflows/ci.yml](.github/workflows/ci.yml)): `ruff format --check`,
`ruff check` and `pytest` for the backend, `vitest` and a build for the frontend.

## Tests

There are deliberately no unit tests over implementation details. Two kinds:

- **Property-based** (Hypothesis) over the chunker — they assert properties for
  any input. This is how an infinite loop at `chunk_overlap >= chunk_size`
  was found.
- **Functional** over services — a complete flow against fake implementations
  of the protocols, with no database, Qdrant or network.

The frontend has regression tests over SSE frame parsing, where a silent
framing bug once broke the whole chat with green builds and a clean console.
