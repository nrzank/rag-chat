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
- `api/` never imports `core/` directly — it goes through `app/` services.
- `app/` never imports `api/`.
- `core/` never imports `app/`.

### Domains

- **documents** — upload, parse, chunk, embed, store
- **chat** — conversation history, RAG retrieval, LLM streaming

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
uv run ruff format --check .
uv run ruff check .
```
