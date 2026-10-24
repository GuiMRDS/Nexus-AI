from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from processing.extractors import SUPPORTED_EXTENSIONS, extract_document
from processing.cleaning import clean_text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"
STOP_WORDS = {
    "a", "as", "o", "os", "um", "uma", "uns", "umas", "de", "da", "do", "das", "dos",
    "e", "ou", "em", "no", "na", "nos", "nas", "para", "por", "com", "sem", "sobre",
    "qual", "quais", "como", "que", "quanto", "quantos", "quantas", "me", "seu", "sua",
    "seus", "suas", "eu", "voce", "vocês", "o", "ao", "aos", "ser", "tem", "ter", "pode",
    "posso", "sao", "é", "e", "do", "mais", "menos", "um", "uma", "no", "na",
}


@dataclass(slots=True)
class DocumentPassage:
    text: str
    source: str
    title: str
    score: int


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _terms(value: str) -> set[str]:
    return {term for term in _normalize(value).split() if len(term) > 1 and term not in STOP_WORDS}


def _split_text(text: str, max_chars: int = 1400) -> list[str]:
    """Divide seções longas em trechos menores para busca por palavras-chave."""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs or [text.strip()]:
        while len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            cut = paragraph.rfind(" ", 0, max_chars)
            cut = cut if cut > max_chars // 2 else max_chars
            chunks.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def buscar_documentacao(
    pergunta: str,
    *,
    documents_dir: str | Path | None = None,
    limit: int = 6,
    min_score: int = 1,
) -> list[DocumentPassage]:
    """Busca trechos nos arquivos locais do SaaS usando correspondência lexical.

    Não usa embeddings, banco vetorial ou uma arquitetura de RAG. Lê a documentação
    local, pontua trechos por termos da pergunta e devolve os mais relevantes.
    """
    root = Path(documents_dir) if documents_dir else DEFAULT_DOCUMENTS_DIR
    if not root.is_dir():
        return []

    question_terms = _terms(pergunta)
    if not question_terms:
        return []

    matches: list[DocumentPassage] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            document = extract_document(path, enable_ocr=False)
        except (OSError, ValueError, RuntimeError):
            # Um arquivo com problema não deve impedir a busca nos demais.
            continue

        relative_source = path.relative_to(root).as_posix()
        for section in document.sections:
            text = clean_text(section.text)
            if not text:
                continue
            for passage in _split_text(text):
                normalized_passage = _normalize(passage)
                passage_terms = _terms(passage)
                overlap = question_terms & passage_terms
                score = len(overlap)
                # Pequeno bônus para frases relevantes que aparecem literalmente.
                normalized_question = _normalize(pergunta)
                if len(normalized_question) >= 8 and normalized_question in normalized_passage:
                    score += 5
                # Valoriza termos raros/concretos sem precisar de embeddings.
                if score >= min_score:
                    matches.append(
                        DocumentPassage(
                            text=passage,
                            source=relative_source,
                            title=section.section_title or path.stem,
                            score=score,
                        )
                    )

    matches.sort(key=lambda item: (-item.score, item.source, item.title))
    # Evita que muitos trechos de um único arquivo escondam outras fontes.
    selected: list[DocumentPassage] = []
    source_counts: dict[str, int] = {}
    for item in matches:
        if source_counts.get(item.source, 0) >= 3:
            continue
        selected.append(item)
        source_counts[item.source] = source_counts.get(item.source, 0) + 1
        if len(selected) >= limit:
            break
    return selected


def montar_contexto_documental(passages: list[DocumentPassage]) -> str:
    if not passages:
        return "Nenhum trecho relevante foi encontrado na documentação local."
    blocks = []
    for index, passage in enumerate(passages, start=1):
        blocks.append(
            f"[Documento {index}]\nArquivo: {passage.source}\nSeção: {passage.title}\n"
            f"Conteúdo:\n{passage.text}"
        )
    return "\n\n---\n\n".join(blocks)
