# Working on this project

RAG chat: document upload, vector search, streamed LLM answers.
Pet project. Work on `main`, no branches, no PRs.

## What to read and when

| File | When |
|---|---|
| [docs/STATUS.md](docs/STATUS.md) | Always first: what is done, what is next, known debt |
| [docs/CONTEXT.md](docs/CONTEXT.md) | Before changing domain logic: vocabulary and invariants |
| [README.md](README.md) | You need the endpoint list, the SSE format or the run commands |
| [docs/specs/](docs/specs/) | Starting a new feature — its spec is here |

The rules below always apply.

## Running things

All commands run from `backend/` through `uv run`. Infrastructure comes up with
`docker compose up -d db qdrant` from the repo root. The worker is a separate
process: `uv run python -m workers.runner`.

Never commit `.env` or real keys.

Note: the UI copy and the LLM prompts are in Russian on purpose — that is the
product language. Code, comments and docs are in English.

## Architecture — DDD / Clean Architecture

Four layers, strict dependency direction: **domain → application → infrastructure → presentation**.

| Layer | Directory | Responsibility | Imports |
|-------|-----------|---------------|---------|
| **Domain** | `app/<domain>/models.py`, `app/<domain>/schemas.py` | Entities, value objects, domain logic | Nothing outside domain |
| **Application** | `app/<domain>/service.py` | Use cases, orchestration | Domain + port interfaces |
| **Infrastructure** | `core/` | DB, Qdrant, OpenAI clients, config | Anything |
| **Presentation** | `api/v1/` | HTTP routers, request/response | Application layer |

### Rules

- **Domain models are pure.** No SQLAlchemy imports, no framework dependencies.
  ORM models live in `app/<domain>/db_models.py` (infrastructure detail).
- **Services depend on abstractions (protocols/interfaces), not concrete
  infrastructure.** Inject DB session, Qdrant client, OpenAI client.
- **Each domain owns its data.** `app/documents/` never queries chat tables
  directly; cross-domain access goes through the owning domain's service.
- `main.py` is the entry point and sits above every layer; `api/deps.py` is the
  composition root. Those two are the only places allowed to wire concrete
  infrastructure (`openai_client`, `qdrant_client`, `async_session`) to services.
- Routers never import infrastructure clients from `core/`. They depend on the
  factories in `api/deps.py`. Reading `core.config.settings` is fine anywhere.
- `app/` never imports `api/`.
- `core/` never imports `app/`.

### Domains

- **documents** — upload, parse, chunk, embed, store
- **chat** — conversation history, RAG retrieval, LLM streaming
- **jobs** — background job queue

## Queue

- All queue access goes through `JobService` — never query `worker_jobs` directly.
- Delivery is at-least-once: every task must be idempotent.
- `pg_notify` is a wake-up hint, never delivery. The poll fallback must work
  on its own.
- Completion deletes the job. Never soft-complete or archive in place.
- Retry policy belongs to the queue, not the service: a task must let
  exceptions propagate instead of swallowing them.
- Status writes that must survive a rollback (`processing`, `failed`) go in
  their own transaction, separate from the work.

## Layering (routers)

- `api/v1/` routers own HTTP: parse request, call service, return response.
  No SQL, no business logic in routes.

## Transactions

- One request = one transaction. Services `flush()`, never `commit()`.
- The session middleware or dependency owns commit/rollback.

## Queries

- No N+1: eager-load with `selectinload`, batch by id set.
- `exists()` over `count() > 0`.
- Explicit typed filter arguments, no `**kwargs` / getattr loops.

## LLM and embeddings

- All OpenAI calls go through `core/openai/client.py`.
  Never instantiate the client inline.
- Always use `settings.openai_api_key` from config, never hardcode.
- Embedding calls batch documents — never one-by-one in a loop.

## Qdrant

- All vector operations go through `core/qdrant/client.py`.
- Collection name comes from `settings.qdrant_collection`.
- Upsert with deterministic point IDs (derived from chunk identity) so
  re-indexing is idempotent.

## Conventions

- `get_*` returns one or `None`; `find_*` returns a list.
- `datetime.now(timezone.utc)` always. Never naive datetime.
- Delete dead code on sight.
- Extract on the third repetition, not before.

## Verification

Before declaring backend changes complete, run from `backend/`:
```bash
uv run ruff format .
uv run ruff check .
```

Both must pass clean. `zip()` always takes `strict=True` — silent truncation
on mismatched lengths is a real bug source when pairing chunks with embeddings.
