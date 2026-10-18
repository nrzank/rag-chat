import { describe, expect, it, vi } from "vitest";
import { streamAsk } from "../sse";
import type { AskEvent } from "../types";

function responseFrom(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(stream, { status: 200 });
}

async function collect(chunks: string[]): Promise<AskEvent[]> {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(responseFrom(chunks)));
  const events: AskEvent[] = [];
  for await (const event of streamAsk("/ask", "q", null, new AbortController().signal)) {
    events.push(event);
  }
  vi.unstubAllGlobals();
  return events;
}

describe("streamAsk", () => {
  it("parses frames separated by \\r\\n\\r\\n as sse-starlette sends them", async () => {
    const events = await collect([
      'event: sources\r\ndata: {"sources": []}\r\n\r\n',
      'event: token\r\ndata: {"text": "hi"}\r\n\r\n',
      'event: done\r\ndata: {"message_id": 7}\r\n\r\n',
    ]);

    expect(events.map((e) => e.event)).toEqual(["sources", "token", "done"]);
  });

  it("parses frames separated by plain \\n\\n", async () => {
    const events = await collect(['event: token\ndata: {"text": "hi"}\n\n']);

    expect(events).toEqual([{ event: "token", data: { text: "hi" } }]);
  });

  it("reassembles a frame split across chunks", async () => {
    const events = await collect(['event: tok', 'en\r\ndata: {"text"', ': "hi"}\r\n\r\n']);

    expect(events).toEqual([{ event: "token", data: { text: "hi" } }]);
  });

  it("yields a trailing frame that has no separator", async () => {
    const events = await collect(['event: error\r\ndata: {"code": "internal_error"}']);

    expect(events.map((e) => e.event)).toEqual(["error"]);
  });

  it("skips malformed frames instead of throwing", async () => {
    const events = await collect([
      "event: token\r\ndata: not json\r\n\r\n",
      'event: token\r\ndata: {"text": "ok"}\r\n\r\n',
    ]);

    expect(events).toEqual([{ event: "token", data: { text: "ok" } }]);
  });
});
