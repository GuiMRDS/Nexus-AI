from __future__ import annotations

import re
from collections import Counter

# Padrões intencionalmente conservadores: não removem números dentro de frases.
_PAGE_NUMBER_PATTERNS = (
    re.compile(r"^\s*(?:p[aá]gina\s*)?\d{1,4}\s*(?:/\s*\d{1,4})?\s*$", re.IGNORECASE),
    re.compile(r"^\s*[-–—]\s*\d{1,4}\s*[-–—]\s*$"),
)


def clean_text(text: str) -> str:
    """Normaliza espaços e caracteres de controle sem destruir o conteúdo."""
    text = text.replace("\ufeff", "").replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t\f\v ]+", " ", text)
    lines = [line.strip() for line in text.split("\n")]
    cleaned: list[str] = []
    for line in lines:
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        if any(pattern.match(line) for pattern in _PAGE_NUMBER_PATTERNS):
            continue
        cleaned.append(line)
    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_repeated_edge_lines(pages: list[str], *, minimum_pages: int = 3) -> list[str]:
    """Remove linhas idênticas repetidas no topo/rodapé de páginas de PDF.

    Só considera as duas primeiras e as duas últimas linhas não vazias de cada
    página. A remoção ocorre quando a linha aparece em pelo menos metade das
    páginas (e em pelo menos `minimum_pages` páginas), evitando heurísticas
    agressivas em conteúdo comum.
    """
    if len(pages) < minimum_pages:
        return pages

    edge_occurrences: Counter[str] = Counter()
    for page in pages:
        lines = [line.strip() for line in page.splitlines() if line.strip()]
        for line in set(lines[:2] + lines[-2:]):
            if len(line) >= 4:
                edge_occurrences[line] += 1

    threshold = max(minimum_pages, (len(pages) + 1) // 2)
    repeated = {line for line, count in edge_occurrences.items() if count >= threshold}
    if not repeated:
        return pages

    result: list[str] = []
    for page in pages:
        lines = page.splitlines()
        result.append("\n".join(line for line in lines if line.strip() not in repeated))
    return result


def clean_markdown(text: str) -> str:
    """Remove marcação Markdown comum, preservando o texto legível e URLs."""
    text = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*(?:[-*_]\s*){3,}$", "", text, flags=re.MULTILINE)
    text = re.sub(r"(```+|~~~+)[^\n]*", "", text)
    text = text.replace("**", "").replace("__", "").replace("~~", "")
    text = re.sub(r"(?<!\w)[*_]([^*_]+)[*_](?!\w)", r"\1", text)
    text = text.replace("`", "")
    # Converte pipes de tabelas Markdown em separadores legíveis.
    text = re.sub(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\|", "", text, flags=re.MULTILINE)
    text = re.sub(r"\|\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*\|\s*", " | ", text)
    return text