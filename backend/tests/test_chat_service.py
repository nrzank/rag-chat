import pytest

from app.base.exceptions import ConversationNotFoundError
from app.chat.models import MessageRole
from app.chat.service import ChatService
from core.qdrant import SearchHit
from tests.fakes import (
    FakeConversationRepository,
    FakeEmbedder,
    FakeLLM,
    FakeMessageRepository,
    FakeVectorSearch,
)

HITS = [
    SearchHit(document_id=1, chunk_index=0, text="FastAPI на бэкенде", score=0.91),
    SearchHit(document_id=1, chunk_index=3, text="Qdrant для векторов", score=0.77),
]


def build(hits=None, llm=None):
    return ChatService(
        conv_repo=FakeConversationRepository(),
        msg_repo=FakeMessageRepository(),
        embedder=FakeEmbedder(),
        vector_search=FakeVectorSearch(hits if hits is not None else HITS),
        llm=llm or FakeLLM(),
    )


async def collect(service, conversation_id, question, document_ids=None):
    return [event async for event in service.ask(conversation_id, question, document_ids)]


async def test_sources_arrive_before_any_token():
    service = build()
    conversation = await service.create_conversation()

    events = await collect(service, conversation.id, "что за проект?")
    order = [e.event for e in events]

    assert order[0] == "sources"
    assert order[-1] == "done"
    assert order.index("sources") < order.index("token")


async def test_stream_yields_every_token_in_order():
    service = build(llm=FakeLLM(tokens=["раз ", "два ", "три"]))
    conversation = await service.create_conversation()

    events = await collect(service, conversation.id, "вопрос")
    tokens = [e.data["text"] for e in events if e.event == "token"]

    assert tokens == ["раз ", "два ", "три"]


async def test_answer_is_saved_with_sources_after_stream():
    service = build(llm=FakeLLM(tokens=["раз ", "два"]))
    conversation = await service.create_conversation()

    await collect(service, conversation.id, "вопрос")
    messages = await service.get_messages(conversation.id)

    assert [m.role for m in messages] == [MessageRole.user, MessageRole.assistant]
    assert messages[0].content == "вопрос"
    assert messages[1].content == "раз два"
    assert [(s.document_id, s.chunk_index) for s in messages[1].sources] == [(1, 0), (1, 3)]


async def test_first_question_becomes_conversation_title():
    service = build()
    conversation = await service.create_conversation()
    assert conversation.title == "Новый диалог"

    await collect(service, conversation.id, "как устроен поиск?")

    updated = await service.get_conversation(conversation.id)
    assert updated.title == "как устроен поиск?"


async def test_title_is_not_overwritten_by_later_questions():
    service = build()
    conversation = await service.create_conversation()

    await collect(service, conversation.id, "первый вопрос")
    await collect(service, conversation.id, "второй вопрос")

    updated = await service.get_conversation(conversation.id)
    assert updated.title == "первый вопрос"


async def test_prompt_carries_context_and_history():
    llm = FakeLLM()
    service = build(llm=llm)
    conversation = await service.create_conversation()

    await collect(service, conversation.id, "первый вопрос")
    await collect(service, conversation.id, "второй вопрос")

    last_prompt = llm.received[-1]
    assert last_prompt[0]["role"] == "system"
    assert any(m["content"] == "первый вопрос" for m in last_prompt)
    assert "Qdrant для векторов" in last_prompt[-1]["content"]
    assert "второй вопрос" in last_prompt[-1]["content"]


async def test_document_filter_is_passed_to_search():
    service = build()
    conversation = await service.create_conversation()

    await collect(service, conversation.id, "вопрос", document_ids=[7, 9])

    assert service.vector_search.calls[-1]["document_ids"] == [7, 9]


async def test_empty_search_result_still_produces_an_answer():
    service = build(hits=[])
    conversation = await service.create_conversation()

    events = await collect(service, conversation.id, "вопрос")

    assert events[0].event == "sources"
    assert events[0].data["sources"] == []
    assert any(e.event == "token" for e in events)


async def test_failing_llm_does_not_save_assistant_message():
    service = build(llm=FakeLLM(fail=True))
    conversation = await service.create_conversation()

    with pytest.raises(RuntimeError):
        await collect(service, conversation.id, "вопрос")

    messages = await service.get_messages(conversation.id)
    assert [m.role for m in messages] == [MessageRole.user]


async def test_unknown_conversation_raises():
    service = build()

    with pytest.raises(ConversationNotFoundError):
        await collect(service, 999, "вопрос")
