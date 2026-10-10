from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.db_models import ChunkORM, DocumentORM
from app.documents.models import Chunk, Document


class SQLAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, document: Document) -> Document:
        orm = DocumentORM(
            filename=document.filename,
            content_type=document.content_type,
            file_path=document.file_path,
            status=document.status,
        )
        self.session.add(orm)
        await self.session.flush()
        document.id = orm.id
        document.created_at = orm.created_at
        return document

    async def get(self, document_id: int) -> Document | None:
        orm = await self.session.get(DocumentORM, document_id)
        if orm is None:
            return None
        return self._to_domain(orm)

    async def find_all(self) -> list[Document]:
        result = await self.session.execute(
            select(DocumentORM).order_by(DocumentORM.created_at.desc())
        )
        return [self._to_domain(row) for row in result.scalars().all()]

    async def update(self, document: Document) -> Document:
        orm = await self.session.get(DocumentORM, document.id)
        if orm is None:
            raise ValueError(f"Document {document.id} not found")
        orm.filename = document.filename
        orm.content_type = document.content_type
        orm.file_path = document.file_path
        orm.status = document.status
        orm.page_count = document.page_count
        orm.error_message = document.error_message
        await self.session.flush()
        document.updated_at = orm.updated_at
        return document

    async def delete(self, document_id: int) -> bool:
        orm = await self.session.get(DocumentORM, document_id)
        if orm is None:
            return False
        await self.session.delete(orm)
        await self.session.flush()
        return True

    @staticmethod
    def _to_domain(orm: DocumentORM) -> Document:
        return Document(
            id=orm.id,
            filename=orm.filename,
            content_type=orm.content_type,
            file_path=orm.file_path,
            status=orm.status,
            page_count=orm.page_count,
            error_message=orm.error_message,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )


class SQLAlchemyChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_many(self, chunks: list[Chunk]) -> list[Chunk]:
        orms = [
            ChunkORM(
                document_id=c.document_id,
                index=c.index,
                text=c.text,
                embedding_id=c.embedding_id,
            )
            for c in chunks
        ]
        self.session.add_all(orms)
        await self.session.flush()
        for chunk, orm in zip(chunks, orms):
            chunk.id = orm.id
            chunk.created_at = orm.created_at
        return chunks

    async def find_by_document(self, document_id: int) -> list[Chunk]:
        result = await self.session.execute(
            select(ChunkORM)
            .where(ChunkORM.document_id == document_id)
            .order_by(ChunkORM.index)
        )
        return [self._to_domain(row) for row in result.scalars().all()]

    async def delete_by_document(self, document_id: int) -> None:
        await self.session.execute(
            delete(ChunkORM).where(ChunkORM.document_id == document_id)
        )
        await self.session.flush()

    @staticmethod
    def _to_domain(orm: ChunkORM) -> Chunk:
        return Chunk(
            id=orm.id,
            document_id=orm.document_id,
            index=orm.index,
            text=orm.text,
            embedding_id=orm.embedding_id,
            created_at=orm.created_at,
        )
