from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.jobs.models import JobKind
from core.database import Base


class WorkerJobORM(Base):
    __tablename__ = "worker_jobs"

    kind: Mapped[JobKind] = mapped_column(Enum(JobKind))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    dedupe_key: Mapped[str] = mapped_column(String(255), unique=True)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_worker_jobs_claim", "run_after", "lease_until"),)
