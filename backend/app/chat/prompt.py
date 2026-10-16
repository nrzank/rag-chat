from app.chat.models import Message
from core.qdrant import SearchHit

SYSTEM_PROMPT = (
    "Ты — ассистент, который отвечает на вопросы строго по предоставленным фрагментам документов. "
    "Если в контексте нет ответа, прямо скажи об этом и не придумывай. "
    "Ссылайся на использованные фрагменты по их номеру в квадратных скобках, например [1]."
)

HISTORY_LIMIT = 10


def build_context(hits: list[SearchHit]) -> str:
    if not hits:
        return "Контекст пуст — подходящих фрагментов не нашлось."
    return "\n\n".join(
        f"[{number}] документ {hit.document_id}, фрагмент {hit.chunk_index}\n{hit.text}"
        for number, hit in enumerate(hits, start=1)
    )


def build_messages(
    question: str,
    hits: list[SearchHit],
    history: list[Message],
) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend({"role": message.role.value, "content": message.content} for message in history[-HISTORY_LIMIT:])
    messages.append(
        {
            "role": "user",
            "content": f"Контекст:\n{build_context(hits)}\n\nВопрос: {question}",
        }
    )
    return messages
