from __future__ import annotations

import re

from processing.models import DocumentChunk, ExtractedSection


def chunk_section(
    section: ExtractedSection,
    *,
    max_chars: int = 1000,
    overlap_chars: int = 100,
    min_chars: int = 50,
) -> list[tuple[str, dict[str, str | int | None]]]:
    """Divide uma seção em chunks, priorizando parágrafos e frases.

    O limite máximo é estrito. A última parte de uma seção pode ter menos de
    `min_chars` para não misturar conteúdo de páginas, slides ou planilhas
    diferentes; essa exceção preserva a localização documental.
    """
    if not 50 <= max_chars <= 1000:
        raise ValueError("max_chars deve estar entre 50 e 1000.")
    if min_chars < 1 or min_chars > max_chars:
        raise ValueError("min_chars deve ser maior que zero e não exceder max_chars.")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars deve ser >= 0 e menor que max_chars.")

    text = section.text.strip()
    if not text:
        return []
    pieces = _split_text_with_overlap(text, max_chars=max_chars, overlap_chars=overlap_chars, min_chars=min_chars)
    location_metadata = _location_metadata(section)
    return [(piece, location_metadata.copy()) for piece in pieces]


def create_chunks(
    sections: list[ExtractedSection],
    *,
    source_file: str,
    base_metadata: dict,
    category: str = "geral",
    max_chars: int = 1000,
    overlap_chars: int = 100,
    min_chars: int = 50,
) -> list[DocumentChunk]:
    """Converte seções extraídas em chunks com metadados para embeddings."""
    result: list[DocumentChunk] = []
    grouped_sections = _group_related_sections(sections)
    for section_index, section in enumerate(grouped_sections):
        for text, location_metadata in chunk_section(
            section,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
            min_chars=min_chars,
        ):
            metadata = {
                **base_metadata,
                "source_file": source_file,
                "category": category,
                "section_index": section_index,
                "chunk_index": len(result),
                "section_title": section.section_title,
                **location_metadata,
            }
            # Vector stores como Chroma não aceitam valores None em metadados.
            metadata = {key: value for key, value in metadata.items() if value is not None}
            result.append(DocumentChunk(text=text, metadata=metadata))
    return result


def _split_text_with_overlap(
    text: str, *, max_chars: int, overlap_chars: int, min_chars: int
) -> list[str]:
    """Corta por limites de parágrafo/frase quando possível, com sobreposição."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        hard_end = min(start + max_chars, length)
        end = hard_end
        if hard_end < length:
            # Prioriza fronteiras lógicas na metade final da janela.
            lower_bound = start + max(min_chars, int(max_chars * 0.60))
            candidates = [
                text.rfind("\n\n", lower_bound, hard_end),
                text.rfind("\n", lower_bound, hard_end),
                text.rfind(". ", lower_bound, hard_end),
                text.rfind("? ", lower_bound, hard_end),
                text.rfind("! ", lower_bound, hard_end),
                text.rfind(" ", lower_bound, hard_end),
            ]
            boundary = max(candidates)
            if boundary >= lower_bound:
                end = boundary + (2 if text[boundary:boundary + 2] in {". ", "? ", "! ", "\n\n"} else 1)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break

        next_start = max(start + 1, end - overlap_chars)
        # Evita começar no meio de uma palavra quando há um espaço próximo.
        whitespace = text.find(" ", next_start, min(end + 1, next_start + 40))
        newline = text.find("\n", next_start, min(end + 1, next_start + 40))
        possible = [index for index in (whitespace, newline) if index >= 0]
        if possible:
            next_start = min(possible) + 1
        start = next_start

    return chunks


def _split_into_units(text: str, max_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: list[str] = []
    for paragraph in paragraphs or [text]:
        if len(paragraph) <= max_chars:
            units.append(paragraph)
            continue
        # Se o parágrafo for longo, tenta preservar frases antes de cortar por tamanho.
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        buffer = ""
        for sentence in sentences:
            if len(sentence) > max_chars:
                if buffer:
                    units.append(buffer)
                    buffer = ""
                units.extend(sentence[i : i + max_chars] for i in range(0, len(sentence), max_chars))
                continue
            candidate = f"{buffer} {sentence}".strip() if buffer else sentence
            if len(candidate) <= max_chars:
                buffer = candidate
            else:
                if buffer:
                    units.append(buffer)
                buffer = sentence
        if buffer:
            units.append(buffer)
    return units


def _location_metadata(section: ExtractedSection) -> dict[str, str | int | None]:
    metadata: dict[str, str | int | None] = {
        "location_type": section.location_type,
        "location": section.location,
    }
    if section.location_type == "page":
        metadata["page"] = section.location
    elif section.location_type == "slide":
        metadata["slide"] = section.location
    elif section.location_type == "sheet":
        metadata["sheet"] = section.location
    elif section.location_type == "section":
        metadata["section"] = section.location
    return metadata


def _group_related_sections(sections: list[ExtractedSection]) -> list[ExtractedSection]:
    """Agrupa parágrafos consecutivos da mesma seção sem cruzar páginas/slides/abas."""
    grouped: list[ExtractedSection] = []
    for section in sections:
        can_merge = bool(grouped) and (
            section.location_type == grouped[-1].location_type
            and section.location == grouped[-1].location
            and section.section_title == grouped[-1].section_title
            and section.location_type not in {"page", "slide", "sheet"}
        )
        if can_merge:
            previous = grouped[-1]
            previous.text = f"{previous.text}\n\n{section.text}"
        else:
            grouped.append(ExtractedSection(
                text=section.text,
                location_type=section.location_type,
                location=section.location,
                section_title=section.section_title,
            ))
    return grouped