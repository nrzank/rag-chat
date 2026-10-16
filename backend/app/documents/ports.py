from typing import Protocol


class Embedder(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class VectorStore(Protocol):
    async def upsert(
        self,
        document_id: int,
        chunk_indexes: list[int],
        texts: list[str],
        vectors: list[list[float]],
    ) -> list[str]: ...

    async def delete_document(self, document_id: int) -> None: ...
