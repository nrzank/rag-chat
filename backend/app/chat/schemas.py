from datetime import datetime

from pydantic import BaseModel, Field

from app.chat.models import MessageRole
from core.config import settings


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
    question: str = Field(min_length=1, max_length=settings.max_question_length)
    document_ids: list[int] | None = Field(default=None, max_length=settings.max_document_filter)
