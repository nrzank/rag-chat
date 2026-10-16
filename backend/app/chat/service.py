from collections.abc import AsyncIterator
from dataclasses import asdict

from app.chat.models import (
    Conversation,
    Message,
    MessageRole,
    SourceRef,
    StreamEvent,
)
from app.chat.ports import LLM, Embedder, VectorSearch
from app.chat.prompt import build_messages
from app.chat.repository import ConversationRepository, MessageRepository
from core.config import settings

TITLE_MAX_LENGTH = 100


class ChatService:
    def __init__(
        self,
        conv_repo: ConversationRepository,
        msg_repo: MessageRepository,
        embedder: Embedder,
        vector_search: VectorSearch,
        llm: LLM,
    ) -> None:
        self.conv_repo = conv_repo
        self.msg_repo = msg_repo
        self.embedder = embedder
        self.vector_search = vector_search
        self.llm = llm

    async def create_conversation(self, title: str = "") -> Conversation:
        return await self.conv_repo.add(Conversation(title=title or "Новый диалог"))

    async def get_conversation(self, conversation_id: int) -> Conversation | None:
        return await self.conv_repo.get(conversation_id)

    async def find_conversations(self) -> list[Conversation]:
        return await self.conv_repo.find_all()

    async def delete_conversation(self, conversation_id: int) -> bool:
        return await self.conv_repo.delete(conversation_id)

    async def get_messages(self, conversation_id: int) -> list[Message]:
        return await self.msg_repo.find_by_conversation(conversation_id)

    async def ask(
        self,
        conversation_id: int,
        question: str,
        document_ids: list[int] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        conversation = await self.conv_repo.get(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        history = await self.msg_repo.find_by_conversation(conversation_id)

        if not history:
            conversation.title = question[:TITLE_MAX_LENGTH]
            await self.conv_repo.update(conversation)

        hits = await self._retrieve(question, document_ids)
        sources = [
            SourceRef(
                document_id=hit.document_id,
                chunk_index=hit.chunk_index,
                score=hit.score,
            )
            for hit in hits
        ]

        await self.msg_repo.add(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.user,
                content=question,
            )
        )

        yield StreamEvent("sources", {"sources": [asdict(source) for source in sources]})

        parts: list[str] = []
        async for token in self.llm.stream(build_messages(question, hits, history)):
            parts.append(token)
            yield StreamEvent("token", {"text": token})

        answer = "".join(parts)
        message = await self.msg_repo.add(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.assistant,
                content=answer,
                sources=sources,
            )
        )

        yield StreamEvent("done", {"message_id": message.id})

    async def _retrieve(self, question: str, document_ids: list[int] | None):
        vectors = await self.embedder.embed([question])
        return await self.vector_search.search(
            vector=vectors[0],
            limit=settings.retrieval_top_k,
            document_ids=document_ids,
        )
