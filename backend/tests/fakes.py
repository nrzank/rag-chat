from collections.abc import AsyncIterator
from copy import deepcopy
from datetime import UTC, datetime

from app.base.exceptions import ConversationNotFoundError, DocumentNotFoundError
from app.chat.models import Conversation, Message
from app.documents.models import Chunk, Document
from core.qdrant import SearchHit


class FakeDocumentRepository:
    def __init__(self) -> None:
        self.items: dict[int, Document] = {}
        self._next_id = 1

    async def add(self, document: Document) -> Document:
        document.id = self._next_id
        document.created_at = datetime.now(UTC)
        self._next_id += 1
        self.items[document.id] = deepcopy(document)
        return document

    async def get(self, document_id: int) -> Document | None:
        stored = self.items.get(document_id)
        return deepcopy(stored) if stored else None

    async def find_all(self) -> list[Document]:
        return [deepcopy(d) for d in self.items.values()]

    async def update(self, document: Document) -> Document:
        if document.id not in self.items:
            raise DocumentNotFoundError("Document not found", params={"document_id": document.id})
        self.items[document.id] = deepcopy(document)
        return document

    async def delete(self, document_id: int) -> bool:
        return self.items.pop(document_id, None) is not None


class FakeChunkRepository:
    def __init__(self) -> None:
        self.items: list[Chunk] = []
        self._next_id = 1

    async def add_many(self, chunks: list[Chunk]) -> list[Chunk]:
        for chunk in chunks:
            chunk.id = self._next_id
            self._next_id += 1
        self.items.extend(deepcopy(chunks))
        return chunks

    async def find_by_document(self, document_id: int) -> list[Chunk]:
        return [deepcopy(c) for c in self.items if c.document_id == document_id]

    async def delete_by_document(self, document_id: int) -> None:
        self.items = [c for c in self.items if c.document_id != document_id]


class FakeEmbedder:
    def __init__(self, dim: int = 8) -> None:
        self.dim = dim
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[float(len(text))] * self.dim for text in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.points: dict[str, dict] = {}
        self.deleted: list[int] = []

    async def upsert(
        self,
        document_id: int,
        chunk_indexes: list[int],
        texts: list[str],
        vectors: list[list[float]],
    ) -> list[str]:
        ids = []
        for index, text, vector in zip(chunk_indexes, texts, vectors, strict=True):
            point = f"doc{document_id}-chunk{index}"
            self.points[point] = {"text": text, "vector": vector}
            ids.append(point)
        return ids

    async def delete_document(self, document_id: int) -> None:
        self.deleted.append(document_id)
        for key in [k for k in self.points if k.startswith(f"doc{document_id}-")]:
            del self.points[key]


class FakeConversationRepository:
    def __init__(self) -> None:
        self.items: dict[int, Conversation] = {}
        self._next_id = 1

    async def add(self, conversation: Conversation) -> Conversation:
        conversation.id = self._next_id
        conversation.created_at = datetime.now(UTC)
        self._next_id += 1
        self.items[conversation.id] = deepcopy(conversation)
        return conversation

    async def get(self, conversation_id: int) -> Conversation | None:
        stored = self.items.get(conversation_id)
        return deepcopy(stored) if stored else None

    async def find_all(self) -> list[Conversation]:
        return [deepcopy(c) for c in self.items.values()]

    async def update(self, conversation: Conversation) -> Conversation:
        if conversation.id not in self.items:
            raise ConversationNotFoundError("Conversation not found", params={"conversation_id": conversation.id})
        self.items[conversation.id] = deepcopy(conversation)
        return conversation

    async def delete(self, conversation_id: int) -> bool:
        return self.items.pop(conversation_id, None) is not None


class FakeMessageRepository:
    def __init__(self) -> None:
        self.items: list[Message] = []
        self._next_id = 1

    async def add(self, message: Message) -> Message:
        message.id = self._next_id
        message.created_at = datetime.now(UTC)
        self._next_id += 1
        self.items.append(deepcopy(message))
        return message

    async def find_by_conversation(self, conversation_id: int) -> list[Message]:
        return [deepcopy(m) for m in self.items if m.conversation_id == conversation_id]


class FakeVectorSearch:
    def __init__(self, hits: list[SearchHit] | None = None) -> None:
        self.hits = hits or []
        self.calls: list[dict] = []

    async def search(
        self,
        vector: list[float],
        limit: int = 5,
        document_ids: list[int] | None = None,
    ) -> list[SearchHit]:
        self.calls.append({"limit": limit, "document_ids": document_ids})
        return list(self.hits)


class FakeLLM:
    def __init__(self, tokens: list[str] | None = None, fail: bool = False) -> None:
        self.tokens = tokens or ["Ответ ", "по ", "документам."]
        self.fail = fail
        self.received: list[list[dict[str, str]]] = []

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        self.received.append(messages)
        if self.fail:
            raise RuntimeError("llm is down")
        for token in self.tokens:
            yield token
