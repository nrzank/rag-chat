from app.documents.models import Chunk


def chunk_text(text: str, document_id: int, chunk_size: int = 512, chunk_overlap: int = 64) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")
    if not 0 <= chunk_overlap < chunk_size:
        raise ValueError(f"chunk_overlap must be in [0, chunk_size), got {chunk_overlap} with chunk_size={chunk_size}")

    chunks: list[Chunk] = []
    start = 0
    index = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text_slice = text[start:end]

        if chunk_text_slice.strip():
            chunks.append(
                Chunk(
                    document_id=document_id,
                    index=index,
                    text=chunk_text_slice.strip(),
                )
            )
            index += 1

        start += chunk_size - chunk_overlap

    return chunks
