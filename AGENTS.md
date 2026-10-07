## Layering

- `api/v1/` routers own HTTP: parse request, call service, return response.
  No SQL, no business logic in routes.
- `app/` services own queries and business rules. Return ORM objects or plain
  results — never response schemas.
- `app/` never imports `api/`. `core/` never imports `app/`.

## Transactions

- One request = one transaction. Services `flush()`, never `commit()`.
- The session middleware or caller owns commit/rollback.

## Queries

- No N+1: eager-load with `selectinload`, batch by id set.
- `exists()` over `count() > 0`.
- Explicit typed filter arguments, no `**kwargs` / getattr loops.

## LLM and embeddings

- All OpenAI calls go through a single client module (`core/openai/` or
  `app/chat/`). Never instantiate the client inline.
- Always pass `settings.openai_api_key` from config, never hardcode.
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
