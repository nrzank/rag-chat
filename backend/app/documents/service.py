from pathlib import Path

from app.documents.chunker import chunk_text
from app.documents.models import Document, DocumentStatus
from app.documents.parser import parse_document
from app.documents.repository import ChunkRepository, DocumentRepository
from core.config import settings


class DocumentService:
    def __init__(self, doc_repo: DocumentRepository, chunk_repo: ChunkRepository) -> None:
        self.doc_repo = doc_repo
        self.chunk_repo = chunk_repo

    async def upload(self, filename: str, content_type: str, file_bytes: bytes) -> Document:
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        document = Document(
            filename=filename,
            content_type=content_type,
            status=DocumentStatus.pending,
        )
        document = await self.doc_repo.add(document)

        file_path = upload_dir / f"{document.id}_{filename}"
        file_path.write_bytes(file_bytes)
        document.file_path = str(file_path)
        document = await self.doc_repo.update(document)

        return document

    async def process(self, document_id: int) -> Document:
        document = await self.doc_repo.get(document_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        document.status = DocumentStatus.processing
        document = await self.doc_repo.update(document)

        try:
            text, page_count = parse_document(document.file_path, document.content_type)
            document.page_count = page_count

            chunks = chunk_text(
                text,
                document_id=document.id,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
            await self.chunk_repo.add_many(chunks)

            document.status = DocumentStatus.ready
            document = await self.doc_repo.update(document)

        except Exception as e:
            document.status = DocumentStatus.failed
            document.error_message = str(e)
            document = await self.doc_repo.update(document)

        return document

    async def get(self, document_id: int) -> Document | None:
        return await self.doc_repo.get(document_id)

    async def find_all(self) -> list[Document]:
        return await self.doc_repo.find_all()

    async def delete(self, document_id: int) -> bool:
        document = await self.doc_repo.get(document_id)
        if document is None:
            return False

        await self.chunk_repo.delete_by_document(document_id)

        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()

        return await self.doc_repo.delete(document_id)
