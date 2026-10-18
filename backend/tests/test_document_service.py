import pytest

from app.base.exceptions import DocumentNotFoundError, DocumentParsingError
from app.documents.models import DocumentStatus
from app.documents.service import DocumentService
from core.config import settings
from tests.fakes import (
    FakeChunkRepository,
    FakeDocumentRepository,
    FakeEmbedder,
    FakeVectorStore,
)


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", tmp_path)
    return DocumentService(
        doc_repo=FakeDocumentRepository(),
        chunk_repo=FakeChunkRepository(),
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(),
    )


async def test_upload_stores_file_and_creates_pending_document(service, tmp_path):
    document = await service.upload("notes.txt", "text/plain", b"hello world")

    assert document.id is not None
    assert document.status is DocumentStatus.pending
    assert (tmp_path / f"{document.id}_notes.txt").read_bytes() == b"hello world"


async def test_process_indexes_document_end_to_end(service):
    document = await service.upload("notes.txt", "text/plain", b"alpha beta gamma delta")

    processed = await service.process(document.id)

    assert processed.status is DocumentStatus.ready
    assert processed.error_message is None

    chunks = await service.chunk_repo.find_by_document(document.id)
    assert chunks
    assert all(chunk.embedding_id for chunk in chunks)
    assert len(service.vector_store.points) == len(chunks)


async def test_reprocessing_does_not_duplicate_chunks(service):
    document = await service.upload("notes.txt", "text/plain", b"alpha beta gamma")

    await service.process(document.id)
    first = await service.chunk_repo.find_by_document(document.id)

    await service.process(document.id)
    second = await service.chunk_repo.find_by_document(document.id)

    assert len(first) == len(second)
    assert [c.text for c in first] == [c.text for c in second]


async def test_process_raises_on_unsupported_type(service):
    """The queue owns retry policy, so process() must not swallow failures."""
    document = await service.upload("report.bin", "application/octet-stream", b"\x00\x01")

    with pytest.raises(DocumentParsingError):
        await service.process(document.id)


async def test_mark_failed_records_the_reason(service):
    document = await service.upload("notes.txt", "text/plain", b"alpha")

    failed = await service.mark_failed(document.id, "Не удалось обработать документ")

    assert failed.status is DocumentStatus.failed
    assert failed.error_message == "Не удалось обработать документ"


async def test_mark_queued_clears_previous_error(service):
    document = await service.upload("notes.txt", "text/plain", b"alpha")
    await service.mark_failed(document.id, "старая ошибка")

    queued = await service.mark_queued(document.id)

    assert queued.status is DocumentStatus.queued
    assert queued.error_message is None


async def test_process_unknown_document_raises(service):
    with pytest.raises(DocumentNotFoundError):
        await service.process(999)


async def test_delete_removes_file_chunks_and_vectors(service, tmp_path):
    document = await service.upload("notes.txt", "text/plain", b"alpha beta gamma")
    await service.process(document.id)

    assert await service.delete(document.id) is True

    assert not (tmp_path / f"{document.id}_notes.txt").exists()
    assert await service.chunk_repo.find_by_document(document.id) == []
    assert service.vector_store.points == {}
    assert await service.get(document.id) is None


async def test_delete_unknown_document_returns_false(service):
    assert await service.delete(999) is False
