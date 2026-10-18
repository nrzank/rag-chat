import pytest
from httpx import ASGITransport, AsyncClient

from api.deps import get_session
from main import app


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.fixture
def fake_session():
    return FakeSession()


@pytest.fixture
def api(fake_session):
    """HTTP client over the real app with the DB session replaced."""
    app.dependency_overrides[get_session] = lambda: fake_session

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")

    yield client

    app.dependency_overrides.clear()


def sse_events(text: str) -> list[dict]:
    """Parse an SSE response body into {event, data} dicts."""
    import json
    import re

    events = []
    for frame in re.split(r"\r?\n\r?\n", text):
        name = ""
        data: list[str] = []
        for line in frame.split("\n"):
            line = line.strip()
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].strip())
        if name and data:
            events.append({"event": name, "data": json.loads("\n".join(data))})
    return events
