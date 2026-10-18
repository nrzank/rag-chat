import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import { describe } from "./api/errors";
import type { Conversation, Document } from "./api/types";
import { ChatView } from "./components/ChatView";
import { ConversationsPanel } from "./components/ConversationsPanel";
import { DocumentsPanel } from "./components/DocumentsPanel";

export default function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [error, setError] = useState("");

  const loadConversations = useCallback(async () => {
    try {
      setConversations(await api.listConversations());
    } catch (e) {
      setError(describe(e));
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    try {
      setDocuments(await api.listDocuments());
    } catch (e) {
      setError(describe(e));
    }
  }, []);

  useEffect(() => {
    void loadConversations();
    void loadDocuments();
  }, [loadConversations, loadDocuments]);

  const create = async () => {
    try {
      const conversation = await api.createConversation();
      setConversations((current) => [conversation, ...current]);
      setActiveId(conversation.id);
    } catch (e) {
      setError(describe(e));
    }
  };

  const remove = async (id: number) => {
    try {
      await api.deleteConversation(id);
      setConversations((current) => current.filter((c) => c.id !== id));
      if (activeId === id) setActiveId(null);
    } catch (e) {
      setError(describe(e));
    }
  };

  const toggle = (id: number) =>
    setSelected((current) =>
      current.includes(id) ? current.filter((x) => x !== id) : [...current, id],
    );

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900">
      <aside className="flex w-80 shrink-0 flex-col gap-6 overflow-y-auto border-r border-slate-200 bg-white p-4">
        <h1 className="text-base font-semibold">RAG Chat</h1>
        {error && <p className="text-xs text-rose-600">{error}</p>}
        <DocumentsPanel selected={selected} onToggleSelected={toggle} />
        <ConversationsPanel
          conversations={conversations}
          activeId={activeId}
          onSelect={setActiveId}
          onCreate={() => void create()}
          onDelete={(id) => void remove(id)}
        />
      </aside>

      <main className="flex-1 overflow-hidden">
        <ChatView
          conversationId={activeId}
          documents={documents}
          selectedDocuments={selected}
          onTitleChanged={() => void loadConversations()}
        />
      </main>
    </div>
  );
}
