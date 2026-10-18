import pytest

from api.deps import get_chat_service
from app.base.exceptions import ConversationNotFoundError
from app.chat.service import ChatService
from core.qdrant import SearchHit
from main import app
from tests.conftest import sse_events
from tests.fakes import (
    FakeConversationRepository,
    FakeEmbedder,
    FakeLLM,
    FakeMessageRepository,
    FakeVectorSearch,
)

HITS = [SearchHit(document_id=1, chunk_index=0, text="FastAPI на бэкенде", score=0.9)]


@pytest.fixture
def chat_service():
    service = ChatService(
        conv_repo=FakeConversationRepository(),
        msg_repo=FakeMessageRepository(),
        embedder=FakeEmbedder(),
        vector_search=FakeVectorSearch(HITS),
        llm=FakeLLM(tokens=["раз ", "два"]),
    )
    app.dependency_overrides[get_chat_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_chat_service, None)


async def test_ask_streams_sources_then_tokens_then_done(api, chat_service, fake_session):
    """Regression: `payload` was shadowed inside event_stream, so this never worked."""
    conversation = await chat_service.create_conversation()

    response = await api.post(
        f"/api/v1/conversations/{conversation.id}/ask",
        json={"question": "о чём документ?"},
    )

    assert response.status_code == 200
    events = sse_events(response.text)

    assert [e["event"] for e in events] == ["sources", "token", "token", "done"]
    assert events[0]["data"]["sources"][0]["document_id"] == 1
    assert "".join(e["data"]["text"] for e in events if e["event"] == "token") == "раз два"
    assert fake_session.commits == 1


async def test_ask_persists_the_answer(api, chat_service):
    conversation = await chat_service.create_conversation()

    await api.post(
        f"/api/v1/conversations/{conversation.id}/ask",
        json={"question": "вопрос"},
    )

    messages = await chat_service.get_messages(conversation.id)
    assert [m.role.value for m in messages] == ["user", "assistant"]
    assert messages[1].content == "раз два"


async def test_ask_on_unknown_conversation_returns_404(api, chat_service):
    response = await api.post("/api/v1/conversations/999/ask", json={"question": "вопрос"})

    assert response.status_code == 404
    assert response.json()["code"] == "conversation_not_found"


async def test_ask_emits_error_event_and_rolls_back(api, chat_service, fake_session, monkeypatch):
    conversation = await chat_service.create_conversation()

    async def boom(*args, **kwargs):
        raise ConversationNotFoundError("gone", params={"conversation_id": 1})
        yield  # pragma: no cover — makes this an async generator

    monkeypatch.setattr(chat_service, "ask", boom)

    response = await api.post(
        f"/api/v1/conversations/{conversation.id}/ask",
        json={"question": "вопрос"},
    )

    events = sse_events(response.text)
    assert [e["event"] for e in events] == ["error"]
    assert events[0]["data"]["code"] == "conversation_not_found"
    assert fake_session.rollbacks == 1
    assert fake_session.commits == 0


async def test_unexpected_error_does_not_leak_details(api, chat_service, monkeypatch):
    conversation = await chat_service.create_conversation()

    async def boom(*args, **kwargs):
        raise RuntimeError("connection string postgres://user:secret@host/db")
        yield  # pragma: no cover

    monkeypatch.setattr(chat_service, "ask", boom)

    response = await api.post(
        f"/api/v1/conversations/{conversation.id}/ask",
        json={"question": "вопрос"},
    )

    assert "secret" not in response.text
    assert sse_events(response.text)[0]["data"] == {
        "code": "internal_error",
        "message": "Internal server error",
        "params": {},
    }


async def test_conversation_crud(api, chat_service, fake_session):
    created = await api.post("/api/v1/conversations/")
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    listed = await api.get("/api/v1/conversations/")
    assert [c["id"] for c in listed.json()] == [conversation_id]

    detail = await api.get(f"/api/v1/conversations/{conversation_id}")
    assert detail.json()["messages"] == []

    deleted = await api.delete(f"/api/v1/conversations/{conversation_id}")
    assert deleted.status_code == 204

    assert (await api.get(f"/api/v1/conversations/{conversation_id}")).status_code == 404
