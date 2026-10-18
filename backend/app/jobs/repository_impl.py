from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.db_models import WorkerJobORM
from app.jobs.models import JobKind, WorkerJob

NOTIFY_CHANNEL = "worker_jobs"


class SQLAlchemyJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def enqueue(
        self,
        kind: JobKind,
        payload: dict,
        dedupe_key: str,
        max_attempts: int = 3,
    ) -> WorkerJob:
        now = datetime.now(UTC)
        statement = (
            insert(WorkerJobORM)
            .values(
                kind=kind,
                payload=payload,
                dedupe_key=dedupe_key,
                run_after=now,
                max_attempts=max_attempts,
            )
            .on_conflict_do_update(
                index_elements=[WorkerJobORM.dedupe_key],
                set_={"run_after": now, "lease_until": None},
            )
            .returning(WorkerJobORM)
        )
        orm = (await self.session.execute(statement)).scalar_one()

        await self.session.execute(
            text(f"SELECT pg_notify('{NOTIFY_CHANNEL}', :payload)"),
            {"payload": str(orm.id)},
        )
        return self._to_domain(orm)

    async def claim(self, limit: int, lease_seconds: int) -> list[WorkerJob]:
        now = datetime.now(UTC)
        candidates = (
            select(WorkerJobORM.id)
            .where(
                WorkerJobORM.run_after <= now,
                (WorkerJobORM.lease_until.is_(None)) | (WorkerJobORM.lease_until < now),
            )
            .order_by(WorkerJobORM.run_after)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        statement = (
            update(WorkerJobORM)
            .where(WorkerJobORM.id.in_(candidates.scalar_subquery()))
            .values(
                lease_until=now + timedelta(seconds=lease_seconds),
                attempt_count=WorkerJobORM.attempt_count + 1,
            )
            .returning(WorkerJobORM)
        )
        rows = (await self.session.execute(statement)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def touch_lease(self, job_id: int, lease_seconds: int) -> None:
        await self.session.execute(
            update(WorkerJobORM)
            .where(WorkerJobORM.id == job_id)
            .values(lease_until=datetime.now(UTC) + timedelta(seconds=lease_seconds))
        )

    async def release(self, job_id: int, delay_seconds: int, error: str) -> None:
        await self.session.execute(
            update(WorkerJobORM)
            .where(WorkerJobORM.id == job_id)
            .values(
                lease_until=None,
                run_after=datetime.now(UTC) + timedelta(seconds=delay_seconds),
                last_error=error,
            )
        )

    async def delete(self, job_id: int) -> None:
        await self.session.execute(delete(WorkerJobORM).where(WorkerJobORM.id == job_id))

    async def find_by_dedupe_key(self, dedupe_key: str) -> WorkerJob | None:
        orm = (
            await self.session.execute(select(WorkerJobORM).where(WorkerJobORM.dedupe_key == dedupe_key))
        ).scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    @staticmethod
    def _to_domain(orm: WorkerJobORM) -> WorkerJob:
        return WorkerJob(
            id=orm.id,
            kind=orm.kind,
            payload=orm.payload or {},
            dedupe_key=orm.dedupe_key,
            run_after=orm.run_after,
            lease_until=orm.lease_until,
            attempt_count=orm.attempt_count,
            max_attempts=orm.max_attempts,
            last_error=orm.last_error,
            created_at=orm.created_at,
        )
