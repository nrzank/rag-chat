import type { Conversation } from "../api/types";

interface Props {
  conversations: Conversation[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onCreate: () => void;
  onDelete: (id: number) => void;
}

export function ConversationsPanel({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onDelete,
}: Props) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-700">Диалоги</h2>
        <button
          onClick={onCreate}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
        >
          Новый
        </button>
      </div>

      {conversations.length === 0 && (
        <p className="text-xs text-slate-400">Диалогов пока нет.</p>
      )}

      <ul className="flex flex-col gap-1">
        {conversations.map((conversation) => (
          <li key={conversation.id} className="group flex items-center gap-1">
            <button
              onClick={() => onSelect(conversation.id)}
              className={`min-w-0 flex-1 truncate rounded-md px-2 py-1.5 text-left text-sm ${
                conversation.id === activeId
                  ? "bg-slate-900 text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              {conversation.title}
            </button>
            <button
              onClick={() => onDelete(conversation.id)}
              className="rounded px-1.5 py-1 text-xs text-slate-400 opacity-0 transition group-hover:opacity-100 hover:text-rose-600"
              aria-label="Удалить диалог"
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
