from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class MessageRole(StrEnum):
    user = "user"
    assistant = "assistant"


@dataclass
class SourceRef:
    document_id: int
    chunk_index: int
    score: float


@dataclass
class StreamEvent:
    event: str
    data: dict


@dataclass
class Conversation:
    id: int | None = None
    title: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Message:
    id: int | None = None
    conversation_id: int = 0
    role: MessageRole = MessageRole.user
    content: str = ""
    sources: list[SourceRef] = field(default_factory=list)
    created_at: datetime | None = None
