from datetime import datetime

from pydantic import BaseModel

from app.chat.models import MessageRole


class SourceOut(BaseModel):
    document_id: int
    chunk_index: int
    score: float


class MessageOut(BaseModel):
    id: int | None
    role: MessageRole
    content: str
    sources: list[SourceOut] = []
    created_at: datetime | None

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: int | None
    title: str
    created_at: datetime | None

    model_config = {"from_attributes": True}


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut] = []


class AskIn(BaseModel):
    question: str
    document_ids: list[int] | None = None
