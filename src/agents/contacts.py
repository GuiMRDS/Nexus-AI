"""Contatos das áreas, lidos do documento de contatos da base de conhecimento."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTACTS_FILE = PROJECT_ROOT / "data" / "documents" / "07_contatos_areas.md"
EXPECTED_COLUMNS = ("área", "categoria", "assuntos", "contato")


@dataclass(slots=True)
class AreaContact:
    area: str
    categoria: str
    assuntos: str
    contato: str


def carregar_contatos(path: str | Path | None = None) -> list[AreaContact]:
    """Lê a tabela Markdown de contatos. Sem arquivo ou sem tabela, devolve lista vazia.

    O mesmo documento é indexado na base vetorial, então o agente também
    consegue responder perguntas diretas sobre esses contatos.
    """
    file_path = Path(path) if path else DEFAULT_CONTACTS_FILE
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    header: list[str] | None = None
    contacts: list[AreaContact] = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if header is None:
            header = [cell.casefold() for cell in cells]
            if not all(column in header for column in EXPECTED_COLUMNS):
                return []
            continue
        if all(set(cell) <= set("-: ") for cell in cells):
            continue  # Linha separadora |---|---|
        row = dict(zip(header, cells))
        if row.get("contato"):
            contacts.append(
                AreaContact(
                    area=row["área"],
                    categoria=row["categoria"],
                    assuntos=row["assuntos"],
                    contato=row["contato"],
                )
            )
    return contacts
