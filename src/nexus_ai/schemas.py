from typing import Literal

from pydantic import BaseModel, Field, field_validator

Canal = Literal["chat", "email", "texto"]


class Fonte(BaseModel):
    """Referência a um trecho de documento que sustenta a resposta."""

    arquivo: str = Field(description="Nome do arquivo de origem.")
    secao: str | None = Field(default=None, description="Seção do documento.")
    localizacao: str | None = Field(
        default=None,
        description="Página, slide ou linhas do trecho, quando aplicável.",
    )
    area: str | None = Field(default=None, description="Área/categoria do documento.")
    atualizado_em: str | None = Field(
        default=None,
        description="Data (AAAA-MM-DD) da última atualização do arquivo.",
    )


class AgentResponse(BaseModel):
    """Formato padronizado de resposta do agente."""

    resposta: str = Field(description="Resposta em linguagem natural para o usuário.")
    fontes: list[Fonte] = Field(
        default_factory=list,
        description="Referências efetivamente usadas para elaborar a resposta.",
    )
    usou_rag: bool = Field(
        default=False,
        description="Indica se a resposta utilizou recuperação de documentos.",
    )
    encontrou_resposta: bool = Field(
        default=False,
        description="Indica se a documentação disponível cobre a pergunta.",
    )
    resposta_formatada: str = Field(
        default="",
        description="Resposta pronta para exibição no canal solicitado, com as referências.",
    )
    interacao_id: str | None = Field(
        default=None,
        description="Identificador da interação registrada, usado para enviar feedback.",
    )


# Turnos anteriores enviados ao agente; mais que isso só aumenta o prompt.
MAX_TURNOS_HISTORICO = 3


class Turno(BaseModel):
    """Uma troca anterior da mesma sessão de conversa."""

    pergunta: str = Field(max_length=4000)
    resposta: str = Field(max_length=8000)


class AskRequest(BaseModel):
    """Corpo JSON aceito pelo endpoint de perguntas."""

    pergunta: str = Field(
        min_length=1,
        max_length=4000,
        description="Pergunta enviada ao assistente Nexus_IA.",
        examples=["Quais são os limites do plano Gratuito?"],
    )
    canal: Canal = Field(
        default="chat",
        description="Canal de exibição: chat (Markdown), email ou texto (Teams/Slack sem Markdown).",
    )
    historico: list[Turno] = Field(
        default_factory=list,
        description=(
            "Trocas anteriores da sessão, da mais antiga para a mais recente. "
            f"Só as {MAX_TURNOS_HISTORICO} últimas são usadas."
        ),
    )

    @field_validator("pergunta")
    @classmethod
    def pergunta_nao_pode_ser_vazia(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A pergunta não pode estar vazia.")
        return value

    @field_validator("historico")
    @classmethod
    def manter_ultimos_turnos(cls, value: list[Turno]) -> list[Turno]:
        return value[-MAX_TURNOS_HISTORICO:]


Avaliacao = Literal["positivo", "negativo"]


class FeedbackRequest(BaseModel):
    """Avaliação do colaborador sobre uma resposta do agente."""

    interacao_id: str = Field(min_length=1, max_length=64)
    avaliacao: Avaliacao
    motivo: str | None = Field(
        default=None,
        max_length=500,
        description="Comentário opcional, geralmente enviado com avaliações negativas.",
    )
