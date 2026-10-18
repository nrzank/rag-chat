from app.jobs.models import JobKind, WorkerJob
from app.jobs.service import BACKOFF_SECONDS, JobService


class FakeJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[int, WorkerJob] = {}
        self.released: list[tuple[int, int, str]] = []
        self.deleted: list[int] = []
        self.touched: list[tuple[int, int]] = []
        self._next_id = 1

    async def enqueue(self, kind, payload, dedupe_key, max_attempts=3) -> WorkerJob:
        existing = await self.find_by_dedupe_key(dedupe_key)
        if existing:
            existing.lease_until = None
            return existing

        job = WorkerJob(
            id=self._next_id,
            kind=kind,
            payload=payload,
            dedupe_key=dedupe_key,
            max_attempts=max_attempts,
        )
        self.jobs[job.id] = job
        self._next_id += 1
        return job

    async def claim(self, limit: int, lease_seconds: int) -> list[WorkerJob]:
        claimed = []
        for job in list(self.jobs.values())[:limit]:
            job.attempt_count += 1
            claimed.append(job)
        return claimed

    async def touch_lease(self, job_id: int, lease_seconds: int) -> None:
        self.touched.append((job_id, lease_seconds))

    async def release(self, job_id: int, delay_seconds: int, error: str) -> None:
        self.released.append((job_id, delay_seconds, error))

    async def delete(self, job_id: int) -> None:
        self.deleted.append(job_id)
        self.jobs.pop(job_id, None)

    async def find_by_dedupe_key(self, dedupe_key: str) -> WorkerJob | None:
        return next((j for j in self.jobs.values() if j.dedupe_key == dedupe_key), None)


def build():
    repo = FakeJobRepository()
    return JobService(repo), repo


async def test_enqueue_uses_a_deterministic_dedupe_key():
    service, _ = build()

    job = await service.enqueue_indexing(42)

    assert job.kind is JobKind.index_document
    assert job.payload == {"document_id": 42}
    assert job.dedupe_key == "index_document:42"


async def test_enqueueing_the_same_document_twice_reuses_one_job():
    service, repo = build()

    first = await service.enqueue_indexing(42)
    second = await service.enqueue_indexing(42)

    assert first.id == second.id
    assert len(repo.jobs) == 1


async def test_completed_job_is_deleted_from_the_queue():
    service, repo = build()
    job = await service.enqueue_indexing(1)

    await service.complete(job)

    assert repo.deleted == [job.id]


async def test_failure_schedules_a_retry_with_backoff():
    service, repo = build()
    job = await service.enqueue_indexing(1)
    job.attempt_count = 1

    retried = await service.fail(job, "boom")

    assert retried is True
    assert repo.released == [(job.id, BACKOFF_SECONDS[0], "boom")]
    assert repo.deleted == []


async def test_backoff_grows_with_each_attempt():
    service, repo = build()
    job = await service.enqueue_indexing(1)

    job.attempt_count = 2
    await service.fail(job, "boom")

    assert repo.released[-1][1] == BACKOFF_SECONDS[1]


async def test_exhausted_job_is_dropped_not_retried():
    service, repo = build()
    job = await service.enqueue_indexing(1)
    job.attempt_count = job.max_attempts

    retried = await service.fail(job, "boom")

    assert retried is False
    assert repo.deleted == [job.id]
    assert repo.released == []


async def test_heartbeat_extends_the_lease():
    service, repo = build()
    job = await service.enqueue_indexing(1)

    await service.heartbeat(job, lease_seconds=120)

    assert repo.touched == [(job.id, 120)]


async def test_claim_increments_attempt_count():
    service, _ = build()
    await service.enqueue_indexing(1)

    claimed = await service.claim(limit=5, lease_seconds=60)

    assert [j.attempt_count for j in claimed] == [1]
