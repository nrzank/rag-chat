import { ApiError } from "./errors";
import type { AskEvent } from "./types";

const SEPARATOR = /\r?\n\r?\n/;

function parseFrame(frame: string): AskEvent | null {
  let event = "";
  const dataLines: string[] = [];

  for (const line of frame.split(/\r?\n/)) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }

  if (!event || dataLines.length === 0) return null;

  try {
    return { event, data: JSON.parse(dataLines.join("\n")) } as AskEvent;
  } catch {
    return null;
  }
}

export async function* streamAsk(
  url: string,
  question: string,
  documentIds: number[] | null,
  signal: AbortSignal,
): AsyncGenerator<AskEvent> {
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, document_ids: documentIds }),
      signal,
    });
  } catch {
    throw new ApiError("network_error");
  }

  if (!response.ok || !response.body) {
    throw new ApiError("internal_error");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      let match = SEPARATOR.exec(buffer);
      while (match !== null) {
        const parsed = parseFrame(buffer.slice(0, match.index));
        buffer = buffer.slice(match.index + match[0].length);
        if (parsed) yield parsed;
        match = SEPARATOR.exec(buffer);
      }
    }

    const trailing = parseFrame(buffer);
    if (trailing) yield trailing;
  } finally {
    // An abandoned generator would otherwise hold the connection open.
    await reader.cancel().catch(() => {});
  }
}
