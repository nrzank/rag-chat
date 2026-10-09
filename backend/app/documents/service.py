from pathlib import Path

from app.documents.models import Document, DocumentStatus
from app.documents.repository import DocumentRepository
from core.config import settings


class DocumentService:
    def __init__(self, repo: DocumentRepository) -> None:
        self.repo = repo

    async def upload(self, filename: str, content_type: str, file_bytes: bytes) -> Document:
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        document = Document(
            filename=filename,
            content_type=content_type,
            status=DocumentStatus.pending,
        )
        document = await self.repo.add(document)

        file_path = upload_dir / f"{document.id}_{filename}"
        file_path.write_bytes(file_bytes)
        document.file_path = str(file_path)
        document = await self.repo.update(document)

        return document

    async def get(self, document_id: int) -> Document | None:
        return await self.repo.get(document_id)

    async def find_all(self) -> list[Document]:
        return await self.repo.find_all()

    async def delete(self, document_id: int) -> bool:
        document = await self.repo.get(document_id)
        if document is None:
            return False

        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()

        return await self.repo.delete(document_id)
