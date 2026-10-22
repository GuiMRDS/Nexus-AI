from __future__ import annotations

from pathlib import Path
from typing import Any

from nexus_ai.processing.chunking import create_chunks
from nexus_ai.processing.cleaning import clean_text, remove_repeated_edge_lines
from nexus_ai.processing.extractors import extract_document
from nexus_ai.processing.metadata import build_document_metadata
from nexus_ai.processing.models import DocumentChunk, ExtractedSection


def processar_documento(
    path: str | Path,
    *,
    category: str = "geral",
    responsible: str | None = None,
    max_chars: int = 1000,
    overlap_chars: int = 100,
    min_chars: int = 50,
    enable_ocr: bool = True,
    extra_metadata: dict[str, Any] | None = None,
) -> list[DocumentChunk]:
    """Processa um documento e devolve chunks com metadados para embeddings."""
    file_path = Path(path)
    extracted = extract_document(file_path, enable_ocr=enable_ocr)

    # Remoção de cabeçalhos/rodapés repetidos entre páginas PDF, antes da limpeza.
    if extracted.file_type == "pdf":
        page_texts = [section.text for section in extracted.sections]
        cleaned_pages = remove_repeated_edge_lines(page_texts)
        extracted.sections = [
            ExtractedSection(
                text=cleaned_pages[index],
                location_type=section.location_type,
                location=section.location,
                section_title=section.section_title,
            )
            for index, section in enumerate(extracted.sections)
        ]

    cleaned_sections: list[ExtractedSection] = []
    for section in extracted.sections:
        cleaned = clean_text(section.text)
        if cleaned:
            cleaned_sections.append(
                ExtractedSection(
                    text=cleaned,
                    location_type=section.location_type,
                    location=section.location,
                    section_title=section.section_title,
                )
            )

    metadata = build_document_metadata(
        file_path,
        category=category,
        responsible=responsible,
        created_at=extracted.document_metadata.get("file_created_at"),
        updated_at=extracted.document_metadata.get("file_modified_at"),
        extra={
            "source_path": extracted.document_metadata.get("source_path"),
            "file_size_bytes": extracted.document_metadata.get("file_size_bytes"),
            "document_author": extracted.document_metadata.get("document_author"),
            "document_created_at": extracted.document_metadata.get("document_created_at"),
            "document_modified_at": extracted.document_metadata.get("document_modified_at"),
            **(extra_metadata or {}),
        },
    )
    return create_chunks(
        cleaned_sections,
        source_file=extracted.source_file,
        base_metadata=metadata,
        category=category,
        max_chars=max_chars,
        overlap_chars=overlap_chars,
        min_chars=min_chars,
    )
