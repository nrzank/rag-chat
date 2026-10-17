from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

from app.base.exceptions import DocumentParsingError


def parse_pdf(file_path: str) -> tuple[str, int]:
    reader = PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages), len(reader.pages)


def parse_docx(file_path: str) -> tuple[str, int]:
    doc = DocxDocument(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs), len(paragraphs)


def parse_txt(file_path: str) -> tuple[str, int]:
    text = Path(file_path).read_text(encoding="utf-8")
    return text, 1


PARSERS = {
    "application/pdf": parse_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": parse_docx,
    "text/plain": parse_txt,
}


def parse_document(file_path: str, content_type: str) -> tuple[str, int]:
    parser = PARSERS.get(content_type)
    if parser is None:
        raise DocumentParsingError(
            "Unsupported content type for parsing",
            params={"content_type": content_type},
        )
    return parser(file_path)
