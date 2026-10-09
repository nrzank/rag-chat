from app.documents.models import Chunk


def chunk_text(text: str, document_id: int, chunk_size: int = 512, chunk_overlap: int = 64) -> list[Chunk]:
    chunks: list[Chunk] = []
    start = 0
    index = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text_slice = text[start:end]

        if chunk_text_slice.strip():
            chunks.append(Chunk(
                document_id=document_id,
                index=index,
                text=chunk_text_slice.strip(),
            ))
            index += 1

        start += chunk_size - chunk_overlap

    return chunks
