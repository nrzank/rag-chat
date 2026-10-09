import enum
from dataclasses import dataclass
from datetime import datetime


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


@dataclass
class Document:
    id: int | None = None
    filename: str = ""
    content_type: str = ""
    file_path: str = ""
    status: DocumentStatus = DocumentStatus.pending
    page_count: int | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Chunk:
    id: int | None = None
    document_id: int = 0
    index: int = 0
    text: str = ""
    embedding_id: str | None = None
    created_at: datetime | None = None
