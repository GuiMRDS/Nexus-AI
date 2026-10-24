from pathlib import Path

import pytest

from processing.chunking import chunk_section
from processing.cleaning import clean_text, remove_repeated_edge_lines
from processing.models import ExtractedSection


def test_clean_text_normalizes_whitespace_and_page_numbers():
    text = "  Título  \r\n\r\nPágina 3\r\nTexto\t com   espaços\n"
    assert clean_text(text) == "Título\n\nTexto com espaços"


def test_remove_repeated_pdf_edge_lines():
    pages = [
        "Empresa Confidencial\nConteúdo A\nRodapé comum",
        "Empresa Confidencial\nConteúdo B\nRodapé comum",
        "Empresa Confidencial\nConteúdo C\nRodapé comum",
    ]
    cleaned = remove_repeated_edge_lines(pages)
    assert all("Empresa Confidencial" not in page for page in cleaned)
    assert all("Rodapé comum" not in page for page in cleaned)
    assert "Conteúdo B" in cleaned[1]


def test_chunking_respects_maximum_length():
    section = ExtractedSection(
        text=("Esta é uma frase de teste. " * 100),
        location_type="page",
        location=2,
    )
    chunks = chunk_section(section, max_chars=500, overlap_chars=50, min_chars=50)
    assert len(chunks) > 1
    assert all(0 < len(text) <= 500 for text, _ in chunks)
    assert all(meta["page"] == 2 for _, meta in chunks)


def test_chunking_rejects_invalid_maximum():
    with pytest.raises(ValueError):
        chunk_section(ExtractedSection("texto"), max_chars=1200)

def test_storage_round_trip(tmp_path):
    from processing.models import DocumentChunk
    from processing.storage import load_chunks_jsonl, save_chunks_jsonl

    original = [DocumentChunk(text="Conteúdo de teste", metadata={"source_file": "teste.md"})]
    target = tmp_path / "chunks.jsonl"
    save_chunks_jsonl(original, target)
    loaded = load_chunks_jsonl(target)
    assert len(loaded) == 1
    assert loaded[0].text == "Conteúdo de teste"
    assert loaded[0].metadata["source_file"] == "teste.md"