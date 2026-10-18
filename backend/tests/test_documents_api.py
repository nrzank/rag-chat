import pytest

from api.deps import get_document_service, get_job_service
from app.documents.service import DocumentService
from app.jobs.service import JobService
from core.config import settings
from main import app
from tests.fakes import (
    FakeChunkRepository,
    FakeDocumentRepository,
    FakeEmbedder,
    FakeVectorStore,
)
from tests.test_job_service import FakeJobRepository

TXT = "text/plain"


@pytest.fixture
def documents(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", tmp_path)

    service = DocumentService(
        doc_repo=FakeDocumentRepository(),
        chunk_repo=FakeChunkRepository(),
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(),
    )
    jobs = JobService(FakeJobRepository())

    app.dependency_overrides[get_document_service] = lambda: service
    app.dependency_overrides[get_job_service] = lambda: jobs
    yield service, jobs
    app.dependency_overrides.pop(get_document_service, None)
    app.dependency_overrides.pop(get_job_service, None)


async def test_upload_accepts_a_supported_file(api, documents):
    response = await api.post(
        "/api/v1/documents/",
        files={"file": ("notes.txt", b"hello", TXT)},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending"


async def test_upload_rejects_an_unsupported_type(api, documents):
    response = await api.post(
        "/api/v1/documents/",
        files={"file": ("payload.exe", b"MZ", "application/x-msdownload")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "unsupported_file_type"


async def test_upload_rejects_an_oversized_file(api, documents, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 1024)

    response = await api.post(
        "/api/v1/documents/",
        files={"file": ("big.txt", b"x" * 5000, TXT)},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"


async def test_process_enqueues_instead_of_working_inline(api, documents, fake_session):
    _, jobs = documents
    uploaded = await api.post("/api/v1/documents/", files={"file": ("notes.txt", b"hi", TXT)})
    document_id = uploaded.json()["id"]

    response = await api.post(f"/api/v1/documents/{document_id}/process")

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert await jobs.repo.find_by_dedupe_key(f"index_document:{document_id}") is not None


async def test_process_on_unknown_document_returns_404(api, documents):
    response = await api.post("/api/v1/documents/999/process")

    assert response.status_code == 404
    assert response.json()["code"] == "document_not_found"


async def test_uploaded_filename_cannot_escape_the_upload_directory(api, documents, tmp_path):
    response = await api.post(
        "/api/v1/documents/",
        files={"file": ("../../../etc/passwd", b"root:x:0:0", TXT)},
    )

    assert response.status_code == 201

    written = list(tmp_path.rglob("*"))
    assert len(written) == 1
    assert written[0].parent == tmp_path
    assert ".." not in written[0].name
