from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from app.documents.repository_impl import SQLAlchemyChunkRepository, SQLAlchemyDocumentRepository
from app.documents.schemas import DocumentOut
from app.documents.service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"}


def _get_service(session: AsyncSession = Depends(get_session)) -> DocumentService:
    return DocumentService(
        doc_repo=SQLAlchemyDocumentRepository(session),
        chunk_repo=SQLAlchemyChunkRepository(session),
    )


@router.post("/", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
    service: DocumentService = Depends(_get_service),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    content = await file.read()
    document = await service.upload(file.filename or "unnamed", file.content_type or "application/octet-stream", content)
    await session.commit()
    return document


@router.post("/{document_id}/process", response_model=DocumentOut)
async def process_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    service: DocumentService = Depends(_get_service),
):
    try:
        document = await service.process(document_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found")
    await session.commit()
    return document


@router.get("/", response_model=list[DocumentOut])
async def list_documents(service: DocumentService = Depends(_get_service)):
    return await service.find_all()


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: int, service: DocumentService = Depends(_get_service)):
    document = await service.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    service: DocumentService = Depends(_get_service),
):
    deleted = await service.delete(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    await session.commit()
