"""Composition root: the only place that wires concrete infrastructure to services.

Routers depend on these factories, never on `core/` directly.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repository_impl import (
    SQLAlchemyConversationRepository,
    SQLAlchemyMessageRepository,
)
from app.chat.service import ChatService
from app.documents.repository_impl import (
    SQLAlchemyChunkRepository,
    SQLAlchemyDocumentRepository,
)
from app.documents.service import DocumentService
from app.jobs.repository_impl import SQLAlchemyJobRepository
from app.jobs.service import JobService
from core.database import async_session
from core.openai import openai_client
from core.qdrant import qdrant_client


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


def get_document_service(session: AsyncSession = Depends(get_session)) -> DocumentService:
    return DocumentService(
        doc_repo=SQLAlchemyDocumentRepository(session),
        chunk_repo=SQLAlchemyChunkRepository(session),
        embedder=openai_client,
        vector_store=qdrant_client,
    )


def get_chat_service(session: AsyncSession = Depends(get_session)) -> ChatService:
    return ChatService(
        conv_repo=SQLAlchemyConversationRepository(session),
        msg_repo=SQLAlchemyMessageRepository(session),
        embedder=openai_client,
        vector_search=qdrant_client,
        llm=openai_client,
    )


def get_job_service(session: AsyncSession = Depends(get_session)) -> JobService:
    return JobService(SQLAlchemyJobRepository(session))
