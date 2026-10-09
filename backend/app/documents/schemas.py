from datetime import datetime

from pydantic import BaseModel

from app.documents.models import DocumentStatus


class DocumentOut(BaseModel):
    id: int | None
    filename: str
    content_type: str
    status: DocumentStatus
    page_count: int | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class ChunkOut(BaseModel):
    id: int | None
    index: int
    text: str

    model_config = {"from_attributes": True}
