"""Monitoramento de qualidade: registra interações e feedback e calcula métricas.

Usa SQLite (biblioteca padrão) para não exigir outro serviço. Cada operação abre
a própria conexão, o que é seguro com os workers em thread do FastAPI.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from nexus_ai.schemas import AgentResponse

DEFAULT_DB_PATH = "data/monitoring/nexus.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS interacoes (
    id TEXT PRIMARY KEY,
    criado_em TEXT NOT NULL,
    pergunta TEXT NOT NULL,
    resposta TEXT,
    encontrou_resposta INTEGER NOT NULL DEFAULT 0,
    usou_rag INTEGER NOT NULL DEFAULT 0,
    fontes TEXT NOT NULL DEFAULT '[]',
    latencia_ms INTEGER NOT NULL,
    modelo TEXT,
    canal TEXT,
    erro TEXT
);
CREATE TABLE IF NOT EXISTS feedback (
    interacao_id TEXT PRIMARY KEY REFERENCES interacoes(id),
    avaliacao TEXT NOT NULL CHECK (avaliacao IN ('positivo', 'negativo')),
    motivo TEXT,
    criado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_interacoes_criado_em ON interacoes(criado_em);
"""


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _percentil(valores: list[int], percentil: float) -> int | None:
    if not valores:
        return None
    ordenados = sorted(valores)
    indice = round(percentil * (len(ordenados) - 1))
    return ordenados[indice]


class MonitoringStore:
    """Persistência das interações com o agente e do feedback dos colaboradores."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or os.getenv("NEXUS_MONITORING_DB", DEFAULT_DB_PATH))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def registrar_interacao(
        self,
        pergunta: str,
        response: AgentResponse | None,
        latencia_ms: int,
        *,
        modelo: str | None = None,
        canal: str | None = None,
        erro: str | None = None,
    ) -> str:
        """Grava uma pergunta e o resultado. `response` é None quando houve erro."""
        interacao_id = uuid4().hex
        fontes = [fonte.model_dump() for fonte in response.fontes] if response else []
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO interacoes (id, criado_em, pergunta, resposta, encontrou_resposta,"
                " usou_rag, fontes, latencia_ms, modelo, canal, erro)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    interacao_id,
                    _agora(),
                    pergunta,
                    response.resposta if response else None,
                    int(bool(response and response.encontrou_resposta)),
                    int(bool(response and response.usou_rag)),
                    json.dumps(fontes, ensure_ascii=False),
                    latencia_ms,
                    modelo,
                    canal,
                    erro,
                ),
            )
        return interacao_id

    def registrar_feedback(
        self,
        interacao_id: str,
        avaliacao: str,
        motivo: str | None = None,
    ) -> bool:
        """Grava (ou substitui) a avaliação. Devolve False se a interação não existe."""
        with closing(self._connect()) as conn, conn:
            existe = conn.execute(
                "SELECT 1 FROM interacoes WHERE id = ?", (interacao_id,)
            ).fetchone()
            if not existe:
                return False
            conn.execute(
                "INSERT INTO feedback (interacao_id, avaliacao, motivo, criado_em)"
                " VALUES (?, ?, ?, ?)"
                " ON CONFLICT(interacao_id) DO UPDATE SET"
                " avaliacao = excluded.avaliacao, motivo = excluded.motivo,"
                " criado_em = excluded.criado_em",
                (interacao_id, avaliacao, (motivo or "").strip() or None, _agora()),
            )
        return True

    def metricas(self, dias: int = 30, limite: int = 10) -> dict[str, Any]:
        """Indicadores do período: cobertura, feedback, latência e lacunas da base."""
        inicio = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(timespec="seconds")
        with closing(self._connect()) as conn:
            linhas = conn.execute(
                "SELECT i.criado_em, i.encontrou_resposta, i.latencia_ms, i.erro, f.avaliacao"
                " FROM interacoes i LEFT JOIN feedback f ON f.interacao_id = i.id"
                " WHERE i.criado_em >= ?",
                (inicio,),
            ).fetchall()

            sem_resposta = conn.execute(
                "SELECT MIN(pergunta) AS pergunta, COUNT(*) AS ocorrencias,"
                " MAX(criado_em) AS ultima_vez"
                " FROM interacoes"
                " WHERE criado_em >= ? AND encontrou_resposta = 0 AND erro IS NULL"
                " GROUP BY LOWER(TRIM(pergunta))"
                " ORDER BY ocorrencias DESC, ultima_vez DESC LIMIT ?",
                (inicio, limite),
            ).fetchall()

            mal_avaliadas = conn.execute(
                "SELECT i.id, i.pergunta, i.resposta, i.fontes, f.motivo, f.criado_em"
                " FROM feedback f JOIN interacoes i ON i.id = f.interacao_id"
                " WHERE f.avaliacao = 'negativo' AND i.criado_em >= ?"
                " ORDER BY f.criado_em DESC LIMIT ?",
                (inicio, limite),
            ).fetchall()

        validas = [linha for linha in linhas if linha["erro"] is None]
        sem_resposta_total = sum(1 for linha in validas if not linha["encontrou_resposta"])
        latencias = [linha["latencia_ms"] for linha in validas]
        positivos = sum(1 for linha in linhas if linha["avaliacao"] == "positivo")
        negativos = sum(1 for linha in linhas if linha["avaliacao"] == "negativo")

        por_dia: dict[str, dict[str, int]] = {}
        for linha in validas:
            dia = por_dia.setdefault(linha["criado_em"][:10], {"total": 0, "sem_resposta": 0})
            dia["total"] += 1
            dia["sem_resposta"] += 0 if linha["encontrou_resposta"] else 1

        return {
            "periodo_dias": dias,
            "total_perguntas": len(linhas),
            "respondidas": len(validas) - sem_resposta_total,
            "sem_resposta": sem_resposta_total,
            "erros": len(linhas) - len(validas),
            "taxa_sem_resposta": (sem_resposta_total / len(validas)) if validas else None,
            "latencia_media_ms": round(sum(latencias) / len(latencias)) if latencias else None,
            "latencia_p95_ms": _percentil(latencias, 0.95),
            "feedback": {
                "positivo": positivos,
                "negativo": negativos,
                "taxa_negativa": (
                    negativos / (positivos + negativos) if positivos + negativos else None
                ),
            },
            "por_dia": [{"dia": dia, **valores} for dia, valores in sorted(por_dia.items())],
            "perguntas_sem_resposta": [dict(linha) for linha in sem_resposta],
            "respostas_mal_avaliadas": [
                {**dict(linha), "fontes": json.loads(linha["fontes"])} for linha in mal_avaliadas
            ],
        }
