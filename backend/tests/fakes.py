from copy import deepcopy
from datetime import UTC, datetime

from app.base.exceptions import DocumentNotFoundError
from app.documents.models import Chunk, Document


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
