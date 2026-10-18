import { ApiError, toApiError } from "./errors";
import type { Conversation, ConversationDetail, Document } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8001";
const API = `${BASE}/api/v1`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API}${path}`, init);
  } catch {
    throw new ApiError("network_error");
  }

  if (!response.ok) {
    throw toApiError(await response.json().catch(() => null));
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  listDocuments: () => request<Document[]>("/documents/"),

  uploadDocument: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<Document>("/documents/", { method: "POST", body });
  },

  processDocument: (id: number) =>
    request<Document>(`/documents/${id}/process`, { method: "POST" }),

  deleteDocument: (id: number) =>
    request<void>(`/documents/${id}`, { method: "DELETE" }),

  listConversations: () => request<Conversation[]>("/conversations/"),

  createConversation: () =>
    request<Conversation>("/conversations/", { method: "POST" }),

  getConversation: (id: number) =>
    request<ConversationDetail>(`/conversations/${id}`),

  deleteConversation: (id: number) =>
    request<void>(`/conversations/${id}`, { method: "DELETE" }),

  askUrl: (id: number) => `${API}/conversations/${id}/ask`,
};
