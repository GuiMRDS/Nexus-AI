from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ExtractedSection:
    """Trecho extraído mantendo sua localização lógica no documento."""

    text: str
    location_type: str = "document"
    location: str | int | None = None
    section_title: str | None = None


@dataclass(slots=True)
class ExtractedDocument:
    """Conteúdo extraído de um arquivo e suas informações de origem."""

    source_file: str
    file_type: str
    sections: list[ExtractedSection] = field(default_factory=list)
    document_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentChunk:
    """Chunk pronto para a futura etapa de embeddings."""

    text: str
    metadata: dict[str, Any]
