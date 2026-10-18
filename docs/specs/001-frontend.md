# 001 — Frontend

Status: delivered 2026-10-18

## Why

The backend works, but the only way to show it was Swagger. We need a UI where
the point is visible: the answer types out as it streams, and the sources
appear **before** the first token.

## What we build

A single-page app: documents and conversations on the left, chat on the right.

### Screen 1. Documents

- List: file name, status, page count, date
- Upload via file picker or drag and drop
- A "Process" button for documents in `pending` or `failed`
- `processing` shows an indicator
- `failed` shows its `error_message`
- Delete with confirmation

### Screen 2. Chat

- Conversation list, create new, delete
- Message history of the selected conversation
- Question input
- Optionally: pick which documents to search (`document_ids`)
- The assistant answer types out as tokens arrive
- A sources block above the answer, shown before the text starts
- `[1]`, `[2]` citations in the answer highlight the matching source

## Boundaries

**In:** documents, conversations, answer streaming, sources, error handling.

**Out:** authentication, theming, mobile layout, multi-file upload, message
editing, export.

## Technical requirements

- React 18+ and TypeScript, strict mode
- Vite
- State: built-in React hooks. Do not add Redux or MobX
- Requests: `fetch`. Do not add an HTTP client
- Styling: Tailwind
- Write API response types by hand in `src/api/types.ts`; do not set up
  OpenAPI codegen
- API base URL from `VITE_API_URL`, defaulting to `http://localhost:8001`

## Working with SSE

`EventSource` does not fit: it only does GET, and `ask` is a POST with a body.
Use `fetch` and read the stream:

```ts
const response = await fetch(`${API}/api/v1/conversations/${id}/ask`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ question, document_ids: documentIds }),
});

const reader = response.body!.getReader();
```

Parse SSE frames by hand: frames are separated by a blank line, and inside a
frame the lines are `event:` and `data:`.

Expected events:

| Event | Body | What to do |
|---|---|---|
| `sources` | `{sources: [{document_id, chunk_index, score}]}` | Show the sources block |
| `token` | `{text: string}` | Append to the answer text |
| `done` | `{message_id: number}` | Finish, commit the message |
| `error` | `{code, message, params}` | Show the error, keep the question in the input |

The stream can be cut off — handle the connection closing without a `done` event.

## API contract

The full endpoint list is in the [README](../../README.md#api).
Errors share one shape: `{code, message, params}`. Show the user text derived
from `code`, not the raw `message` from the response.

Document statuses: `pending`, `queued`, `processing`, `ready`, `failed`.

## Acceptance criteria

1. An uploaded PDF appears in the list; after "Process" the status becomes `ready`
2. An unsupported file type produces a clear message, not a crash
3. The sources block appears before the first character of the answer
4. The answer text types out gradually instead of appearing all at once
5. Conversation history survives a page reload
6. Deleting a document removes it from the list and from the search filter
7. A stopped backend produces an error message, not a blank screen
8. `npm run build` passes with no TypeScript errors

## Layout

```
frontend/
├── src/
│   ├── api/          # client.ts, types.ts, sse.ts
│   ├── components/
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## What surfaced during implementation

- **sse-starlette terminates frames with `\r\n\r\n`, not `\n\n`.** A parser
  looking for `\n\n` never parsed a single frame — the UI stayed silent with no
  console errors. Covered by a test in `src/api/__tests__/sse.test.ts`.
- `error_message` was missing from `DocumentOut` even though the spec required
  showing it. Added to the schema.
- The raw OpenAI error text leaked into the UI. Now a sanitized message goes out
  and the detail stays in the logs.
- CORS added: `CORSMiddleware` in `app/main.py`, origin in `settings.cors_origins`.
- Processing became asynchronous after this spec was written: `process` now
  returns `202` and the UI polls the status while it is `queued` or `processing`.
