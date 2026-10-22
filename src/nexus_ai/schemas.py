from pydantic import BaseModel, Field, field_validator


class AgentResponse(BaseModel):
    """Formato padronizado de resposta do agente."""

    resposta: str = Field(description="Resposta em linguagem natural para o usuário.")
    fontes: list[str] = Field(
        default_factory=list,
        description="Referências efetivamente usadas para elaborar a resposta.",
    )
    usou_rag: bool = Field(
        default=False,
        description="Indica se a resposta utilizou recuperação de documentos.",
    )


class AskRequest(BaseModel):
    """Corpo JSON aceito pelo endpoint de perguntas."""

    pergunta: str = Field(
        min_length=1,
        max_length=4000,
        description="Pergunta enviada ao assistente Nexus_IA.",
        examples=["Quais são os limites do plano Gratuito?"],
    )

    @field_validator("pergunta")
    @classmethod
    def pergunta_nao_pode_ser_vazia(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A pergunta não pode estar vazia.")
        return value