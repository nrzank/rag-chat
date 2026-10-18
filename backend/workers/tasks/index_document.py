import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import AppError
from app.documents.repository_impl import SQLAlchemyChunkRepository, SQLAlchemyDocumentRepository
from app.documents.service import DocumentService
from app.jobs.models import WorkerJob
from core.database import async_session
from core.openai import openai_client
from core.qdrant import qdrant_client

logger = logging.getLogger(__name__)

FAILURE_MESSAGE = "Не удалось обработать документ"


def _service(session: AsyncSession) -> DocumentService:
    return DocumentService(
        doc_repo=SQLAlchemyDocumentRepository(session),
        chunk_repo=SQLAlchemyChunkRepository(session),
        embedder=openai_client,
        vector_store=qdrant_client,
    )


async def index_document(session: AsyncSession, job: WorkerJob) -> None:
    document_id = job.payload["document_id"]
    await _mark_processing(document_id)

    try:
        await _service(session).process(document_id)
    except Exception as e:
        if job.attempts_left <= 0:
            await _record_failure(document_id, e)
        raise


async def _mark_processing(document_id: int) -> None:
    """Own transaction: the status must stay visible even if the work below rolls back."""
    async with async_session() as session:
        await _service(session).mark_processing(document_id)
        await session.commit()


async def _record_failure(document_id: int, error: Exception) -> None:
    """Own transaction too: the work transaction is about to roll back."""
    message = error.message if isinstance(error, AppError) else FAILURE_MESSAGE

    async with async_session() as session:
        await _service(session).mark_failed(document_id, message)
        await session.commit()

    logger.error("document %s marked failed after exhausting attempts", document_id)
