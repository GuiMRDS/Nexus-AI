"""Curadoria de conteúdo: aponta documentos que precisam de revisão do responsável.

Cruza o inventário documental (`05_inventario_documental.csv`) com os arquivos
que estão de fato em `data/documents/` e sinaliza:
- revisão vencida (última revisão há mais de `prazo_dias`);
- status de curadoria que não é "Aprovado" (ex.: rascunho);
- arquivo modificado depois da última revisão (o índice pode não ter a versão oficial);
- arquivo indexável sem registro no inventário, ou registro sem arquivo.
"""

from __future__ import annotations

import csv
import os
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from processing.extractors import SUPPORTED_EXTENSIONS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"
INVENTORY_FILE = "05_inventario_documental.csv"
DEFAULT_PRAZO_DIAS = 90


@dataclass(slots=True)
class Pendencia:
    documento: str
    nome: str
    categoria: str
    responsavel: str
    ultima_revisao: str | None
    arquivos: list[str]
    motivos: list[str] = field(default_factory=list)


def get_prazo_revisao() -> int:
    value = os.getenv("NEXUS_CURADORIA_PRAZO_DIAS", "").strip()
    return int(value) if value else DEFAULT_PRAZO_DIAS


def _data_revisao(value: str) -> date | None:
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), formato).date()
        except ValueError:
            continue
    return None


def _arquivos_indexaveis(root: Path) -> dict[str, Path]:
    extensions = {str(extension).lower() for extension in SUPPORTED_EXTENSIONS}
    return {
        path.name: path
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix.lower() in extensions
    }


def relatorio_curadoria(
    documents_dir: str | Path | None = None,
    *,
    prazo_dias: int | None = None,
    hoje: date | None = None,
) -> dict[str, Any]:
    """Monta o relatório de curadoria agrupável por responsável."""
    root = Path(documents_dir or DEFAULT_DOCUMENTS_DIR)
    prazo = prazo_dias if prazo_dias is not None else get_prazo_revisao()
    hoje = hoje or date.today()
    arquivos = _arquivos_indexaveis(root)

    inventario = root / INVENTORY_FILE
    try:
        with inventario.open(encoding="utf-8-sig", newline="") as file:
            registros = list(csv.DictReader(file))
    except OSError:
        registros = []

    pendencias: list[Pendencia] = []
    inventariados: set[str] = set()
    for registro in registros:
        nomes = [
            Path(item.strip()).name
            for item in (registro.get("source_path") or "").split(";")
            if item.strip()
        ]
        inventariados.update(nomes)
        revisao = _data_revisao(registro.get("last_reviewed") or "")
        pendencia = Pendencia(
            documento=registro.get("document_id", ""),
            nome=registro.get("document_name", ""),
            categoria=registro.get("category", ""),
            responsavel=registro.get("owner_role") or "Sem responsável definido",
            ultima_revisao=revisao.isoformat() if revisao else None,
            arquivos=nomes,
        )

        if revisao is None:
            pendencia.motivos.append("Data da última revisão ausente ou inválida.")
        elif (hoje - revisao).days > prazo:
            pendencia.motivos.append(
                f"Revisão vencida: {(hoje - revisao).days} dias desde a última (prazo {prazo})."
            )

        status = (registro.get("curation_status") or "").strip()
        if not status.casefold().startswith("aprovado"):
            pendencia.motivos.append(f"Status de curadoria: {status or 'não informado'}.")

        for nome in nomes:
            path = arquivos.get(nome)
            if path is None:
                pendencia.motivos.append(f"Arquivo {nome} não está em data/documents.")
                continue
            modificado = date.fromtimestamp(path.stat().st_mtime)
            if revisao and modificado > revisao:
                pendencia.motivos.append(
                    f"{nome} foi alterado em {modificado.isoformat()}, depois da última revisão."
                )

        if pendencia.motivos:
            pendencias.append(pendencia)

    sem_inventario = sorted(nome for nome in arquivos if nome not in inventariados)

    return {
        "gerado_em": hoje.isoformat(),
        "prazo_dias": prazo,
        "documentos_inventariados": len(registros),
        "pendencias": [asdict(pendencia) for pendencia in pendencias],
        "arquivos_sem_inventario": sem_inventario,
    }
