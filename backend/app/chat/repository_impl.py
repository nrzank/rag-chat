from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.db_models import ConversationORM, MessageORM
from app.chat.models import Conversation, Message, SourceRef


class SQLAlchemyConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, conversation: Conversation) -> Conversation:
        orm = ConversationORM(title=conversation.title)
        self.session.add(orm)
        await self.session.flush()
        conversation.id = orm.id
        conversation.created_at = orm.created_at
        return conversation

    async def get(self, conversation_id: int) -> Conversation | None:
        orm = await self.session.get(ConversationORM, conversation_id)
        if orm is None:
            return None
        return self._to_domain(orm)

    async def find_all(self) -> list[Conversation]:
        result = await self.session.execute(select(ConversationORM).order_by(ConversationORM.created_at.desc()))
        return [self._to_domain(row) for row in result.scalars().all()]

    async def delete(self, conversation_id: int) -> bool:
        orm = await self.session.get(ConversationORM, conversation_id)
        if orm is None:
            return False
        await self.session.delete(orm)
        await self.session.flush()
        return True

    @staticmethod
    def _to_domain(orm: ConversationORM) -> Conversation:
        return Conversation(
            id=orm.id,
            title=orm.title,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )


class SQLAlchemyMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, message: Message) -> Message:
        orm = MessageORM(
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            sources=[asdict(source) for source in message.sources],
        )
        self.session.add(orm)
        await self.session.flush()
        message.id = orm.id
        message.created_at = orm.created_at
        return message

    async def find_by_conversation(self, conversation_id: int) -> list[Message]:
        result = await self.session.execute(
            select(MessageORM).where(MessageORM.conversation_id == conversation_id).order_by(MessageORM.id)
        )
        return [self._to_domain(row) for row in result.scalars().all()]

    @staticmethod
    def _to_domain(orm: MessageORM) -> Message:
        return Message(
            id=orm.id,
            conversation_id=orm.conversation_id,
            role=orm.role,
            content=orm.content,
            sources=[SourceRef(**source) for source in orm.sources or []],
            created_at=orm.created_at,
        )
