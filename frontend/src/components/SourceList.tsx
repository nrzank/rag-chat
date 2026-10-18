import type { Document, Source } from "../api/types";

interface Props {
  sources: Source[];
  documents: Document[];
}

export function SourceList({ sources, documents }: Props) {
  if (sources.length === 0) return null;

  const nameOf = (id: number) =>
    documents.find((d) => d.id === id)?.filename ?? `документ ${id}`;

  return (
    <div className="mb-2 flex flex-wrap gap-1.5">
      {sources.map((source, index) => (
        <span
          key={`${source.document_id}-${source.chunk_index}`}
          title={`релевантность ${source.score.toFixed(3)}`}
          className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-600"
        >
          [{index + 1}] {nameOf(source.document_id)} · фрагмент {source.chunk_index}
        </span>
      ))}
    </div>
  );
}
