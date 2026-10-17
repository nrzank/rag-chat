from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.exception_handlers import register_exception_handlers
from api.router import router
from core.qdrant import qdrant_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await qdrant_client.ensure_collection()
    yield


app = FastAPI(title="RAG Chat", version="0.1.0", lifespan=lifespan)

register_exception_handlers(app)
app.include_router(router)
