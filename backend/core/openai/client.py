from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from core.config import settings

EMBEDDING_BATCH_SIZE = 100


class OpenAIClient:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[start : start + EMBEDDING_BATCH_SIZE]
            response = await self._client.embeddings.create(
                model=settings.openai_embedding_model,
                input=batch,
            )
            vectors.extend(item.embedding for item in response.data)
        return vectors

    async def complete(self, messages: list[dict[str, str]]) -> str:
        response = await self._client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


openai_client = OpenAIClient()
