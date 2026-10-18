from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_document_service, get_job_service, get_session
from app.base.exceptions import (
    DocumentNotFoundError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.documents.schemas import DocumentOut
from app.documents.service import DocumentService
from app.jobs.service import JobService
from core.config import settings

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


READ_CHUNK_BYTES = 64 * 1024


async def _read_within_limit(file: UploadFile) -> bytes:
    """Read in chunks and abort past the limit, so an oversized body never lands in memory."""
    buffer = bytearray()

    while chunk := await file.read(READ_CHUNK_BYTES):
        buffer.extend(chunk)
        if len(buffer) > settings.max_upload_bytes:
            raise FileTooLargeError(
                "File is too large",
                params={"max_bytes": settings.max_upload_bytes},
            )

    return bytes(buffer)


@router.post("/", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    if file.content_type not in ALLOWED_TYPES:
        raise UnsupportedFileTypeError(
            "Unsupported file type",
            params={"content_type": file.content_type, "allowed": sorted(ALLOWED_TYPES)},
        )

    content = await _read_within_limit(file)
    document = await service.upload(
        filename=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        file_bytes=content,
    )
    await session.commit()
    return document


@router.post("/{document_id}/process", response_model=DocumentOut, status_code=202)
async def process_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    service: DocumentService = Depends(get_document_service),
    jobs: JobService = Depends(get_job_service),
):
    document = await service.mark_queued(document_id)
    await jobs.enqueue_indexing(document_id)
    await session.commit()
    return document


@router.get("/", response_model=list[DocumentOut])
async def list_documents(service: DocumentService = Depends(get_document_service)):
    return await service.find_all()


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: int, service: DocumentService = Depends(get_document_service)):
    document = await service.get(document_id)
    if document is None:
        raise DocumentNotFoundError("Document not found", params={"document_id": document_id})
    return document


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    deleted = await service.delete(document_id)
    if not deleted:
        raise DocumentNotFoundError("Document not found", params={"document_id": document_id})
    await session.commit()
