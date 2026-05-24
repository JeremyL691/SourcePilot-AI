from __future__ import annotations

from pathlib import Path

from app.ingestion.base import ExtractedDocument
from app.ingestion.chunking import clean_text


def ingest_pdf(path: str) -> list[ExtractedDocument]:
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for PDF ingestion. Install project dependencies first.") from exc

    reader = PdfReader(str(pdf_path))
    docs: list[ExtractedDocument] = []
    for page_index, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        cleaned = clean_text(raw_text)
        if not cleaned:
            continue
        docs.append(
            ExtractedDocument(
                title=f"{pdf_path.stem} page {page_index}",
                raw_text=raw_text,
                clean_text=cleaned,
                url=None,
                metadata={"source_kind": "pdf", "page": page_index, "local_path": str(pdf_path)},
            )
        )
    return docs

