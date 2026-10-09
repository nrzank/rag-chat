import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.models import Document, DocumentStatus
from core.config import settings


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upload(self, filename: str, content_type: str, file_bytes: bytes) -> Document:
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        document = Document(
            filename=filename,
            content_type=content_type,
            file_path="",
            status=DocumentStatus.pending,
        )
        self.session.add(document)
        await self.session.flush()

        file_path = upload_dir / f"{document.id}_{filename}"
        file_path.write_bytes(file_bytes)
        document.file_path = str(file_path)
        await self.session.flush()

        return document

    async def get(self, document_id: int) -> Document | None:
        return await self.session.get(Document, document_id)

    async def find_all(self) -> list[Document]:
        result = await self.session.execute(select(Document).order_by(Document.created_at.desc()))
        return list(result.scalars().all())

    async def delete(self, document_id: int) -> bool:
        document = await self.get(document_id)
        if document is None:
            return False

        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()

        await self.session.delete(document)
        await self.session.flush()
        return True
