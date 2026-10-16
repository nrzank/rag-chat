from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.chat.models import MessageRole
from core.database import Base


class ConversationORM(Base):
    __tablename__ = "conversations"

    title: Mapped[str] = mapped_column(String(512))

    messages: Mapped[list["MessageORM"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageORM.id",
    )


class MessageORM(Base):
    __tablename__ = "messages"

    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole))
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    conversation: Mapped[ConversationORM] = relationship(back_populates="messages")
