import uuid
from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient, models

from core.config import settings

POINT_NAMESPACE = uuid.UUID("6f1c1f6e-0b1e-4b7a-9c3a-5d2e8f0a7b41")


@dataclass
class SearchHit:
    document_id: int
    chunk_index: int
    text: str
    score: float


def point_id(document_id: int, chunk_index: int) -> str:
    return str(uuid.uuid5(POINT_NAMESPACE, f"{document_id}:{chunk_index}"))


class QdrantVectorStore:
    def __init__(self) -> None:
        self._client = AsyncQdrantClient(url=settings.qdrant_url)
        self._collection = settings.qdrant_collection

    async def ensure_collection(self) -> None:
        if await self._client.collection_exists(self._collection):
            return
        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config=models.VectorParams(
                size=settings.embedding_dim,
                distance=models.Distance.COSINE,
            ),
        )

    async def upsert(
        self,
        document_id: int,
        chunk_indexes: list[int],
        texts: list[str],
        vectors: list[list[float]],
    ) -> list[str]:
        ids = [point_id(document_id, index) for index in chunk_indexes]
        points = [
            models.PointStruct(
                id=pid,
                vector=vector,
                payload={"document_id": document_id, "chunk_index": index, "text": text},
            )
            for pid, index, text, vector in zip(ids, chunk_indexes, texts, vectors, strict=True)
        ]
        await self._client.upsert(collection_name=self._collection, points=points)
        return ids

    async def search(
        self,
        vector: list[float],
        limit: int = 5,
        document_ids: list[int] | None = None,
    ) -> list[SearchHit]:
        query_filter = None
        if document_ids:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchAny(any=document_ids),
                    )
                ]
            )

        response = await self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )
        return [
            SearchHit(
                document_id=point.payload["document_id"],
                chunk_index=point.payload["chunk_index"],
                text=point.payload["text"],
                score=point.score,
            )
            for point in response.points
        ]

    async def delete_document(self, document_id: int) -> None:
        await self._client.delete(
            collection_name=self._collection,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            ),
        )


qdrant_client = QdrantVectorStore()
