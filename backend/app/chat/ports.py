from collections.abc import AsyncIterator
from typing import Protocol

from core.qdrant import SearchHit


class Embedder(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class VectorSearch(Protocol):
    async def search(
        self,
        vector: list[float],
        limit: int = 5,
        document_ids: list[int] | None = None,
    ) -> list[SearchHit]: ...


class LLM(Protocol):
    def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]: ...
