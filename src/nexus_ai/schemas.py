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

    @field_validator("pergunta")
    @classmethod
    def pergunta_nao_pode_ser_vazia(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A pergunta não pode estar vazia.")
        return value
