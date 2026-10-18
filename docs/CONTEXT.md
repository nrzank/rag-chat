# Project context

Read this before changing domain logic. It holds the domain, the vocabulary and
the invariants that are not visible from the code.

## What we are building

A service that answers questions about documents the user uploaded. An LLM
generates the answer, but **only from the retrieved chunks** — it must not answer
from its own knowledge. If the documents do not contain the answer, it has to
say so plainly.

## Why it looks like this

This is a portfolio project. Two consequences follow:

1. **Architecture matters more than delivery speed.** Layers, protocols and
   typed errors are justified here even though they are heavy for this amount
   of code — the project has to demonstrate an approach, not just work.
2. **Features are added only when they show an engineering decision.**
   Authentication, multi-tenancy and billing are deliberately absent: they add
   nothing to a demonstration of a RAG pipeline.

## Vocabulary

Use these terms. Do not invent synonyms.

| Term | Meaning |
|---|---|
| **Document** | An uploaded file. Aggregate root: chunks do not exist without it |
| **Chunk** | A fixed-size slice of a document's text, with overlap |
| **embedding_id** | Identifier of the Qdrant point that corresponds to a chunk |
| **Conversation** | A dialogue. Aggregate root for messages |
| **Message** | One turn in a conversation, role `user` or `assistant` |
| **SourceRef** | A reference to a chunk used in an answer. Value object |
| **WorkerJob** | A queued job. Deleted on success, never archived in place |
| **lease** | How long a worker holds a job. Once it expires another worker may take it |
| **dedupe_key** | The key that keeps re-enqueueing from creating duplicate jobs |
| **retrieval** | Finding relevant chunks by the question's vector |
| **indexing** | Generating embeddings and writing vectors to Qdrant |

Do not mix "chunk" and "fragment" within one layer, do not use "embedding" as a
synonym for "Qdrant point", do not use "chat" instead of "conversation" in
entity names.

## Main flows

### Upload and indexing

```
POST /documents/        → file to disk, row in the DB, status pending

POST /documents/{id}/process  → status queued, job enqueued, responds 202
                              → pg_notify wakes the worker

worker:
    → claim the job (FOR UPDATE SKIP LOCKED + lease)
    → status processing     ← own transaction, survives a rollback of the work
    → delete previous chunks and vectors
    → parse the file
    → split into chunks
    → fetch embeddings in a batch
    → write vectors to Qdrant
    → save chunks with embedding_id
    → status ready, job deleted from the queue

on failure:
    → attempts left  → job returns to the queue after a delay
    → attempts spent → status failed, job deleted
```

### Question and answer

```
POST /conversations/{id}/ask
    → embed the question
    → search top-k chunks in Qdrant
    → save the user message
    → emit the sources event
    → build the prompt: system + history + context + question
    → stream tokens as token events
    → save the assistant answer with its sources
    → emit the done event
```

## Invariants

Breaking any of these is a bug, even if the tests are green.

**Data**

- A document in status `ready` has at least one chunk, and every chunk has an
  `embedding_id`.
- A document in status `failed` must have a non-empty `error_message`.
- Deleting a document removes the file from disk, the chunks from the DB and the
  vectors from Qdrant. None of the three steps is skipped.
- Deleting a conversation deletes all of its messages (cascade).

**Indexing**

- Qdrant point ids are deterministic: `uuid5` over `document_id:chunk_index`.
  Re-processing overwrites the same points.
- Running `process` twice on the same document does not create duplicate chunks.
- Embeddings are requested in batches, never one at a time in a loop.
- Pairing chunks with vectors always uses `zip(..., strict=True)`. Silent
  truncation here means losing data without a single error.

**Chunking**

- `0 <= chunk_overlap < chunk_size`. Breaking this causes an infinite loop,
  which is why the check exists both in the function and in the settings
  validator.
- A chunk is never longer than `chunk_size`.
- Empty and whitespace-only chunks are not saved.
- Chunk indexes within a document run consecutively from zero.

**Queue**

- Delivery is **at-least-once**. A job can run twice: the lease expired, or the
  process died after the work but before the job was deleted. Indexing is
  therefore idempotent — it drops previous chunks and vectors first.
- `pg_notify` is only a hint for immediate pickup. Every path must also work
  through polling: a lost notification must not stall the queue.
- `LISTEN` needs its own asyncpg connection, not one from the SQLAlchemy pool.
- Completing a job means deleting the row. Completed jobs are not archived in
  place, or the table bloats.
- An exhausted job must leave a trace: the document moves to `failed`. Never
  drop a job without recording why.
- The `processing` and `failed` statuses are written **in their own
  transactions**. The work transaction rolls back on failure and would take
  them with it.
- Retry policy belongs to the queue, not the service. `DocumentService.process()`
  must let exceptions propagate instead of swallowing them: otherwise the queue
  considers the work done and retries never fire.
- Every enqueue sets a deterministic `dedupe_key` — asking to process the same
  document again does not create a second job.

**Chat**

- The answer is built only from the provided context. The system prompt forbids
  making things up.
- Chunk numbering in the context matches the order in the `sources` event — the
  UI links a `[2]` citation to the second source.
- History in the prompt is trimmed to the last `HISTORY_LIMIT` messages.
- The assistant message is saved after the stream finishes, together with its
  sources.
- The transaction is committed after the stream ends, not before it.

**Storage consistency**

Postgres and Qdrant are written outside a shared transaction. If the Qdrant
write succeeds and the DB commit fails, orphan vectors remain. That is
acceptable: deterministic point ids make re-processing converge. Do not build a
distributed transaction here.

## Out of scope

These decisions are settled. Do not propose them again without an explicit ask.

- Authentication, users, multi-tenancy
- Reranking of search results
- Hybrid search (vectors plus full text)
- Formats beyond PDF, DOCX and TXT
- Fine-tuning models
