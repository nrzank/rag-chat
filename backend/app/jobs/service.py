import logging

from app.jobs.models import JobKind, WorkerJob
from app.jobs.repository import JobRepository

logger = logging.getLogger(__name__)

BACKOFF_SECONDS = [10, 60, 300]


class JobService:
    def __init__(self, repo: JobRepository) -> None:
        self.repo = repo

    async def enqueue_indexing(self, document_id: int) -> WorkerJob:
        return await self.repo.enqueue(
            kind=JobKind.index_document,
            payload={"document_id": document_id},
            dedupe_key=f"{JobKind.index_document}:{document_id}",
        )

    async def claim(self, limit: int, lease_seconds: int) -> list[WorkerJob]:
        return await self.repo.claim(limit=limit, lease_seconds=lease_seconds)

    async def heartbeat(self, job: WorkerJob, lease_seconds: int) -> None:
        await self.repo.touch_lease(job.id, lease_seconds)

    async def complete(self, job: WorkerJob) -> None:
        await self.repo.delete(job.id)

    async def fail(self, job: WorkerJob, error: str) -> bool:
        """Return True if the job will be retried, False if attempts ran out."""
        if job.attempts_left <= 0:
            logger.error("job %s exhausted after %s attempts", job.id, job.attempt_count)
            await self.repo.delete(job.id)
            return False

        delay = BACKOFF_SECONDS[min(job.attempt_count - 1, len(BACKOFF_SECONDS) - 1)]
        logger.warning("job %s failed, retrying in %ss: %s", job.id, delay, error)
        await self.repo.release(job.id, delay_seconds=delay, error=error)
        return True
