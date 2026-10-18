import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { describe } from "../api/errors";
import type { Document, DocumentStatus } from "../api/types";

const STATUS_LABEL: Record<DocumentStatus, string> = {
  pending: "не обработан",
  queued: "в очереди",
  processing: "обработка…",
  ready: "готов",
  failed: "ошибка",
};

const STATUS_STYLE: Record<DocumentStatus, string> = {
  pending: "bg-slate-200 text-slate-700",
  queued: "bg-sky-100 text-sky-800",
  processing: "bg-amber-100 text-amber-800",
  ready: "bg-emerald-100 text-emerald-800",
  failed: "bg-rose-100 text-rose-800",
};

const IN_FLIGHT: DocumentStatus[] = ["queued", "processing"];
const POLL_INTERVAL_MS = 2000;

interface Props {
  selected: number[];
  onToggleSelected: (id: number) => void;
}

export function DocumentsPanel({ selected, onToggleSelected }: Props) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [error, setError] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      setDocuments(await api.listDocuments());
    } catch (e) {
      setError(describe(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const hasInFlight = documents.some((d) => IN_FLIGHT.includes(d.status));

  useEffect(() => {
    if (!hasInFlight) return;

    const timer = setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [hasInFlight, load]);

  const upload = async (file: File) => {
    setError("");
    try {
      const created = await api.uploadDocument(file);
      setDocuments((current) => [created, ...current]);
      await process(created.id);
    } catch (e) {
      setError(describe(e));
    }
  };

  const process = async (id: number) => {
    setError("");
    try {
      const updated = await api.processDocument(id);
      setDocuments((current) => current.map((d) => (d.id === id ? updated : d)));
    } catch (e) {
      setError(describe(e));
    }
  };

  const remove = async (id: number) => {
    if (!confirm("Удалить документ?")) return;
    try {
      await api.deleteDocument(id);
      setDocuments((current) => current.filter((d) => d.id !== id));
      if (selected.includes(id)) onToggleSelected(id);
    } catch (e) {
      setError(describe(e));
    }
  };

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-700">Документы</h2>
        <button
          onClick={() => fileInput.current?.click()}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
        >
          Загрузить
        </button>
      </div>

      <input
        ref={fileInput}
        type="file"
        accept=".pdf,.docx,.txt"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void upload(file);
          e.target.value = "";
        }}
      />

      {error && <p className="text-xs text-rose-600">{error}</p>}

      {documents.length === 0 && (
        <p className="text-xs text-slate-400">
          Пока ничего не загружено. Поддерживаются PDF, DOCX и TXT.
        </p>
      )}

      <ul className="flex flex-col gap-2">
        {documents.map((doc) => (
          <li
            key={doc.id}
            className="rounded-lg border border-slate-200 bg-white p-3 text-sm"
          >
            <div className="flex items-start gap-2">
              <input
                type="checkbox"
                className="mt-0.5"
                disabled={doc.status !== "ready"}
                checked={selected.includes(doc.id)}
                onChange={() => onToggleSelected(doc.id)}
                title={
                  doc.status === "ready"
                    ? "Искать в этом документе"
                    : "Доступно после обработки"
                }
              />
              <p
                className="min-w-0 flex-1 truncate font-medium text-slate-800"
                title={doc.filename}
              >
                {doc.filename}
              </p>
            </div>

            <div className="mt-1.5 flex items-center gap-2 pl-6">
              <span
                className={`rounded px-1.5 py-0.5 text-[11px] ${STATUS_STYLE[doc.status]}`}
              >
                {STATUS_LABEL[doc.status]}
              </span>
              {doc.page_count !== null && (
                <span className="text-[11px] text-slate-400">
                  {doc.page_count} стр.
                </span>
              )}
            </div>

            {doc.status === "failed" && doc.error_message && (
              <p className="mt-1.5 break-words pl-6 text-[11px] text-rose-600">
                {doc.error_message}
              </p>
            )}

            <div className="mt-2 flex gap-1 pl-6">
              {(doc.status === "pending" || doc.status === "failed") && (
                <button
                  onClick={() => void process(doc.id)}
                  className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-100"
                >
                  Обработать
                </button>
              )}
              <button
                onClick={() => void remove(doc.id)}
                className="rounded px-2 py-1 text-xs text-rose-600 hover:bg-rose-50"
              >
                Удалить
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
