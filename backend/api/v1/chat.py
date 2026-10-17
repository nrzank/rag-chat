import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from api.deps import get_session
from app.base.exceptions import AppError, ConversationNotFoundError
from app.chat.repository_impl import (
    SQLAlchemyConversationRepository,
    SQLAlchemyMessageRepository,
)
from app.chat.schemas import AskIn, ConversationDetailOut, ConversationOut
from app.chat.service import ChatService
from core.openai import openai_client
from core.qdrant import qdrant_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["chat"])


def _get_service(session: AsyncSession = Depends(get_session)) -> ChatService:
    return ChatService(
        conv_repo=SQLAlchemyConversationRepository(session),
        msg_repo=SQLAlchemyMessageRepository(session),
        embedder=openai_client,
        vector_search=qdrant_client,
        llm=openai_client,
    )


@router.post("/", response_model=ConversationOut, status_code=201)
async def create_conversation(
    session: AsyncSession = Depends(get_session),
    service: ChatService = Depends(_get_service),
):
    conversation = await service.create_conversation()
    await session.commit()
    return conversation


@router.get("/", response_model=list[ConversationOut])
async def list_conversations(service: ChatService = Depends(_get_service)):
    return await service.find_conversations()


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: int,
    service: ChatService = Depends(_get_service),
):
    conversation = await service.get_conversation(conversation_id)
    if conversation is None:
        raise ConversationNotFoundError("Conversation not found", params={"conversation_id": conversation_id})

    messages = await service.get_messages(conversation_id)
    return ConversationDetailOut(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=messages,
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: int,
    session: AsyncSession = Depends(get_session),
    service: ChatService = Depends(_get_service),
):
    deleted = await service.delete_conversation(conversation_id)
    if not deleted:
        raise ConversationNotFoundError("Conversation not found", params={"conversation_id": conversation_id})
    await session.commit()


@router.post("/{conversation_id}/ask")
async def ask(
    conversation_id: int,
    payload: AskIn,
    session: AsyncSession = Depends(get_session),
    service: ChatService = Depends(_get_service),
):
    if await service.get_conversation(conversation_id) is None:
        raise ConversationNotFoundError("Conversation not found", params={"conversation_id": conversation_id})

    async def event_stream() -> AsyncIterator[dict[str, str]]:
        try:
            async for event in service.ask(
                conversation_id=conversation_id,
                question=payload.question,
                document_ids=payload.document_ids,
            ):
                yield {"event": event.event, "data": json.dumps(event.data, ensure_ascii=False)}
            await session.commit()
        except AppError as e:
            await session.rollback()
            payload = {"code": e.code, "message": e.message, "params": e.params}
            yield {"event": "error", "data": json.dumps(payload, ensure_ascii=False)}
        except Exception:
            await session.rollback()
            logger.exception("ask stream failed for conversation %s", conversation_id)
            payload = {"code": "internal_error", "message": "Internal server error", "params": {}}
            yield {"event": "error", "data": json.dumps(payload, ensure_ascii=False)}

    return EventSourceResponse(event_stream())
