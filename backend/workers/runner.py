import asyncio
import contextlib
import logging
import signal

import asyncpg

from app.jobs.models import JobKind, WorkerJob
from app.jobs.repository_impl import NOTIFY_CHANNEL, SQLAlchemyJobRepository
from app.jobs.service import JobService
from core.config import settings
from core.database import async_session
from core.qdrant import qdrant_client
from workers.tasks.index_document import index_document

logger = logging.getLogger(__name__)

HANDLERS = {JobKind.index_document: index_document}


class Runner:
    def __init__(self) -> None:
        self._wakeup = asyncio.Event()
        self._stopping = asyncio.Event()

    async def run(self) -> None:
        await qdrant_client.ensure_collection()

        listener = asyncio.create_task(self._listen())
        logger.info("worker started, poll interval %ss", settings.worker_poll_seconds)

        try:
            while not self._stopping.is_set():
                processed = await self._drain()
                if processed == 0:
                    await self._sleep_until_wakeup()
        finally:
            listener.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await listener
            logger.info("worker stopped")

    def stop(self) -> None:
        self._stopping.set()
        self._wakeup.set()

    async def _sleep_until_wakeup(self) -> None:
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._wakeup.wait(), timeout=settings.worker_poll_seconds)
        self._wakeup.clear()

    async def _listen(self) -> None:
        """LISTEN needs its own asyncpg connection: it cannot share the pooled engine."""
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

        while not self._stopping.is_set():
            try:
                connection = await asyncpg.connect(dsn)
                await connection.add_listener(NOTIFY_CHANNEL, lambda *_: self._wakeup.set())
                logger.info("listening on %s", NOTIFY_CHANNEL)
                await self._stopping.wait()
                await connection.close()
            except Exception:
                logger.exception("listener dropped, reconnecting in 5s")
                await asyncio.sleep(5)

    async def _drain(self) -> int:
        async with async_session() as session:
            service = JobService(SQLAlchemyJobRepository(session))
            jobs = await service.claim(
                limit=settings.worker_batch_size,
                lease_seconds=settings.worker_lease_seconds,
            )
            await session.commit()

        for job in jobs:
            await self._execute(job)
        return len(jobs)

    async def _execute(self, job: WorkerJob) -> None:
        handler = HANDLERS.get(job.kind)
        if handler is None:
            logger.error("no handler for job kind %s", job.kind)
            async with async_session() as session:
                await JobService(SQLAlchemyJobRepository(session)).fail(job, "unknown kind")
                await session.commit()
            return

        logger.info("job %s (%s) attempt %s", job.id, job.kind, job.attempt_count)
        try:
            async with async_session() as session:
                await handler(session, job)
                await JobService(SQLAlchemyJobRepository(session)).complete(job)
                await session.commit()
        except Exception as e:
            logger.exception("job %s raised", job.id)
            async with async_session() as session:
                await JobService(SQLAlchemyJobRepository(session)).fail(job, str(e))
                await session.commit()


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    runner = Runner()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, runner.stop)

    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
