from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.router import router
from core.qdrant import qdrant_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await qdrant_client.ensure_collection()
    yield


app = FastAPI(title="RAG Chat", version="0.1.0", lifespan=lifespan)

app.include_router(router)
