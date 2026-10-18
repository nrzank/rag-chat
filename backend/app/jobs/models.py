from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class JobKind(StrEnum):
    index_document = "index_document"


@dataclass
class WorkerJob:
    id: int | None = None
    kind: JobKind = JobKind.index_document
    payload: dict[str, Any] = field(default_factory=dict)
    dedupe_key: str = ""
    run_after: datetime | None = None
    lease_until: datetime | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    last_error: str | None = None
    created_at: datetime | None = None

    @property
    def attempts_left(self) -> int:
        return max(self.max_attempts - self.attempt_count, 0)
