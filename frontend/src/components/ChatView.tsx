import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { ApiError, describe } from "../api/errors";
import { streamAsk } from "../api/sse";
import type { Document, Message, Source } from "../api/types";
import { SourceList } from "./SourceList";

interface Props {
  conversationId: number | null;
  documents: Document[];
  selectedDocuments: number[];
  onTitleChanged: () => void;
}

export function ChatView({
  conversationId,
  documents,
  selectedDocuments,
  onTitleChanged,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef<HTMLDivElement>(null);
  const inFlight = useRef<AbortController | null>(null);

  useEffect(() => {
    setMessages([]);
    setAnswer("");
    setSources([]);
    setError("");
    setStreaming(false);
    if (conversationId === null) return;

    api
      .getConversation(conversationId)
      .then((detail) => setMessages(detail.messages))
      .catch((e) => setError(describe(e)));

    // Abandon a stream still running for the previous conversation, or its
    // tokens keep landing in this one.
    return () => inFlight.current?.abort();
  }, [conversationId]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, answer]);

  const send = async () => {
    const text = question.trim();
    if (!text || conversationId === null || streaming) return;

    setQuestion("");
    setError("");
    setAnswer("");
    setSources([]);
    setStreaming(true);
    setMessages((current) => [
      ...current,
      { id: null, role: "user", content: text, sources: [], created_at: null },
    ]);

    const controller = new AbortController();
    inFlight.current = controller;

    let streamed = "";
    let received: Source[] = [];
    let failed = false;

    try {
      const events = streamAsk(
        api.askUrl(conversationId),
        text,
        selectedDocuments.length > 0 ? selectedDocuments : null,
        controller.signal,
      );

      for await (const event of events) {
        if (event.event === "sources") {
          received = event.data.sources;
          setSources(received);
        } else if (event.event === "token") {
          streamed += event.data.text;
          setAnswer(streamed);
        } else if (event.event === "error") {
          failed = true;
          setError(describe(new ApiError(event.data.code, event.data.params)));
        }
      }
    } catch (e) {
      if (controller.signal.aborted) return;
      failed = true;
      setError(describe(e));
    } finally {
      if (inFlight.current === controller) inFlight.current = null;
      setStreaming(false);
    }

    // The user switched conversation mid-stream: nothing here belongs to the
    // conversation now on screen.
    if (controller.signal.aborted) return;

    if (failed || streamed === "") {
      setMessages((current) => current.slice(0, -1));
      setQuestion(text);
      setAnswer("");
      setSources([]);
      return;
    }

    setMessages((current) => [
      ...current,
      {
        id: null,
        role: "assistant",
        content: streamed,
        sources: received,
        created_at: null,
      },
    ]);
    setAnswer("");
    setSources([]);
    onTitleChanged();
  };

  if (conversationId === null) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-400">
        Создай диалог, чтобы задать вопрос
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="mx-auto flex max-w-3xl flex-col gap-4">
          {messages.length === 0 && !streaming && (
            <p className="py-8 text-center text-sm text-slate-400">
              Задай вопрос по загруженным документам
            </p>
          )}

          {messages.map((message, index) => (
            <div
              key={index}
              className={message.role === "user" ? "flex justify-end" : ""}
            >
              {message.role === "assistant" && (
                <SourceList sources={message.sources} documents={documents} />
              )}
              <div
                className={
                  message.role === "user"
                    ? "max-w-[80%] rounded-2xl bg-slate-900 px-4 py-2 text-sm text-white"
                    : "whitespace-pre-wrap text-sm leading-relaxed text-slate-800"
                }
              >
                {message.content}
              </div>
            </div>
          ))}

          {streaming && (
            <div>
              <SourceList sources={sources} documents={documents} />
              <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
                {answer}
                <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-slate-400 align-middle" />
              </div>
            </div>
          )}

          {error && <p className="text-sm text-rose-600">{error}</p>}
          <div ref={bottom} />
        </div>
      </div>

      <div className="border-t border-slate-200 bg-white px-6 py-4">
        <div className="mx-auto flex max-w-3xl gap-2">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            rows={1}
            placeholder={
              selectedDocuments.length > 0
                ? `Вопрос по ${selectedDocuments.length} документам…`
                : "Вопрос по всем документам…"
            }
            className="flex-1 resize-none rounded-xl border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-slate-900"
          />
          <button
            onClick={() => void send()}
            disabled={streaming || question.trim() === ""}
            className="rounded-xl bg-slate-900 px-5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-40"
          >
            {streaming ? "…" : "Отправить"}
          </button>
        </div>
      </div>
    </div>
  );
}
