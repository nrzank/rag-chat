import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from api.deps import get_chat_service, get_session
from app.base.exceptions import AppError, ConversationNotFoundError
from app.chat.schemas import AskIn, ConversationDetailOut, ConversationOut
from app.chat.service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["chat"])


@router.post("/", response_model=ConversationOut, status_code=201)
async def create_conversation(
    session: AsyncSession = Depends(get_session),
    service: ChatService = Depends(get_chat_service),
):
    conversation = await service.create_conversation()
    await session.commit()
    return conversation


@router.get("/", response_model=list[ConversationOut])
async def list_conversations(service: ChatService = Depends(get_chat_service)):
    return await service.find_conversations()


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: int,
    service: ChatService = Depends(get_chat_service),
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
    service: ChatService = Depends(get_chat_service),
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
    service: ChatService = Depends(get_chat_service),
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
            error = {"code": e.code, "message": e.message, "params": e.params}
            yield {"event": "error", "data": json.dumps(error, ensure_ascii=False)}
        except Exception:
            await session.rollback()
            logger.exception("ask stream failed for conversation %s", conversation_id)
            error = {"code": "internal_error", "message": "Internal server error", "params": {}}
            yield {"event": "error", "data": json.dumps(error, ensure_ascii=False)}

    return EventSourceResponse(event_stream())
