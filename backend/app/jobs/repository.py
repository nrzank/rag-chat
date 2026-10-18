from typing import Protocol

from app.jobs.models import JobKind, WorkerJob


class JobRepository(Protocol):
    async def enqueue(
        self,
        kind: JobKind,
        payload: dict,
        dedupe_key: str,
        max_attempts: int = 3,
    ) -> WorkerJob: ...

    async def claim(self, limit: int, lease_seconds: int) -> list[WorkerJob]: ...

    async def touch_lease(self, job_id: int, lease_seconds: int) -> None: ...

    async def release(self, job_id: int, delay_seconds: int, error: str) -> None: ...

    async def delete(self, job_id: int) -> None: ...

    async def find_by_dedupe_key(self, dedupe_key: str) -> WorkerJob | None: ...
