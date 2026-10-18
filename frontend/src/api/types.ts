export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export interface Document {
  id: number;
  filename: string;
  content_type: string;
  status: DocumentStatus;
  page_count: number | null;
  error_message: string | null;
  created_at: string | null;
}

export interface Source {
  document_id: number;
  chunk_index: number;
  score: number;
}

export interface Message {
  id: number | null;
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  created_at: string | null;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string | null;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface ApiErrorBody {
  code: string;
  message: string;
  params: Record<string, unknown>;
}

export type AskEvent =
  | { event: "sources"; data: { sources: Source[] } }
  | { event: "token"; data: { text: string } }
  | { event: "done"; data: { message_id: number } }
  | { event: "error"; data: ApiErrorBody };
