# Nexus_IA — Embeddings e Busca Vetorial

Esta etapa adiciona a indexação vetorial ao Nexus_IA, permitindo transformar trechos de documentos (_chunks_) em embeddings e realizar buscas por similaridade semântica. A busca lexical existente continua disponível.

## 🚀 Funcionalidades

- **Geração de embeddings:** transforma os textos dos chunks em vetores numéricos.
- **Modelo multilíngue:** utiliza o `paraphrase-multilingual-MiniLM-L12-v2`, compatível com textos em português.
- **Armazenamento vetorial:** utiliza o ChromaDB para persistir embeddings e metadados localmente.
- **Busca semântica:** recupera trechos relacionados ao significado da consulta, mesmo quando as palavras utilizadas são diferentes.
- **Filtros por metadados:** permite filtrar resultados por categoria, arquivo de origem e outros metadados disponíveis.
- **Indexação de documentos:** permite indexar um arquivo ou um diretório inteiro.
- **Persistência local:** mantém o índice salvo entre execuções da aplicação.

## 🛠️ Tecnologias utilizadas

- Python
- Sentence Transformers
- ChromaDB
- Pytest
- Pipeline de processamento de documentos do Nexus_IA

## 📁 Arquivos adicionados

```text
src/
└── processing/
    ├── __init__.py
    └── store/
        ├── embeddings.py
        ├── indexing.py
        └── vector_store.py

scripts/
└── index_documents.py

tests/
├── test_embeddings.py
└── test_vector_store.py
```

Também são necessárias atualizações nas dependências do projeto e no `.gitignore`.

## ⚙️ Instalação

### Com uv

Adicione as dependências abaixo ao `pyproject.toml` existente:

```toml
"sentence-transformers",
"chromadb",
```

Depois, atualize o ambiente:

```bash
uv lock
uv sync
```

### Com pip

Instale as dependências do arquivo `requirements.txt`:

```bash
pip install -r requirements.txt
```

Na primeira execução, o Sentence Transformers poderá baixar o modelo de embeddings, dependendo do cache disponível e da conexão com a internet.

## 📚 Indexação de documentos

Coloque os documentos que deseja indexar no diretório `data/documents/`.

Para indexar todos os documentos suportados, incluindo os encontrados em subdiretórios, execute:

```bash
uv run python scripts/index_documents.py
```

Para indicar outro diretório:

```bash
uv run python scripts/index_documents.py ./meus_documentos
```

Para desativar a busca em subdiretórios:

```bash
uv run python scripts/index_documents.py ./meus_documentos --no-recursive
```

Para desativar o OCR durante o processamento:

```bash
uv run python scripts/index_documents.py ./meus_documentos --no-ocr
```

O comando apresenta um resumo com os arquivos encontrados, os arquivos indexados, a quantidade de chunks processados e eventuais erros.

## 🔎 Exemplo de busca semântica

```python
from processing.store.vector_store import VectorStore

vector_store = VectorStore()

resultados = vector_store.search(
    "Como faço para redefinir minha senha?",
    limit=5,
)

for resultado in resultados:
    print("Texto:", resultado.text)
    print("Metadados:", resultado.metadata)
    print("Distância:", resultado.distance)
```

### Busca com filtro por metadados

```python
resultados = vector_store.search(
    "Informações sobre atendimento",
    limit=5,
    where={"category": "suporte"},
)
```

O filtro depende dos metadados efetivamente armazenados nos documentos indexados.

## 🧭 Camada de recuperação (RAG)

Além da busca vetorial direta, o `Retriever` (`src/processing/retrieval.py`) encapsula o fluxo completo de recuperação usado pelo RAG:

1. Transforma a pergunta em embedding com o mesmo modelo usado na indexação.
2. Busca os `candidate_limit` trechos mais próximos semanticamente no ChromaDB, já aplicando o filtro de metadados (`where`).
3. Reordena os candidatos com um cross-encoder (`Reranker`, em `src/processing/store/reranker.py`), que avalia a pergunta completa junto de cada trecho.
4. Devolve os `limit` trechos mais relevantes após o reranqueamento.

```python
from processing.retrieval import Retriever, montar_contexto_vetorial

retriever = Retriever()
passagens = retriever.retrieve(
    "Quantos dias de férias eu tenho?",
    limit=5,
    candidate_limit=20,
)

contexto = montar_contexto_vetorial(passagens)
```

O modelo de reranqueamento padrão é o `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (multilíngue, inclui português) e pode ser trocado pela variável `NEXUS_RERANKER_MODEL`. Essa é a camada usada pelo agente, descrita a seguir.

## ✅ Geração e validação de respostas

O agente (`src/agents/agent.py`) responde somente com base nos trechos recuperados e sempre indica as fontes:

1. **Limiar de confiança:** trechos com score do reranker abaixo de `NEXUS_MIN_RELEVANCE` (padrão `-3.5`) são descartados. Se nenhum sobrar, o LLM nem é chamado.
2. **Geração:** o LLM recebe a pergunta e os trechos numerados (`[Documento N]`) e devolve a resposta, se encontrou a informação e quais documentos citou.
3. **Validação de consistência:** a resposta precisa citar documentos existentes, e todo número dela (preços, limites, prazos) precisa aparecer nos documentos citados. Se falhar, o LLM gera de novo uma vez; se falhar outra vez, o agente usa o fallback.
4. **Fontes:** montadas a partir dos metadados reais dos trechos — arquivo, seção, página/linhas, área e data de atualização.
5. **Fallback:** "Não encontrei essa informação nos documentos disponíveis.", seguido dos contatos das áreas de `data/documents/07_contatos_areas.md`.
6. **Formatação por canal:** a API devolve `resposta_formatada` para `chat` (Markdown), `email` ou `texto` (Teams/Slack sem Markdown).

```bash
curl -X POST http://localhost:8000/api/v1/perguntar \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Quanto custa o plano Pro?", "canal": "chat"}'
```

```json
{
  "resposta": "R$ 79,90 por organização/mês (valor fictício de demonstração).",
  "fontes": [
    {
      "arquivo": "02_faq_suporte.md",
      "secao": "Qual é o preço do plano Pro?",
      "localizacao": null,
      "area": "suporte",
      "atualizado_em": "2026-10-21"
    }
  ],
  "usou_rag": true,
  "encontrou_resposta": true,
  "resposta_formatada": "R$ 79,90 por organização/mês (valor fictício de demonstração).\n\n**Fontes**\n1. 02_faq_suporte.md — Qual é o preço do plano Pro? · atualizado em 2026-10-21"
}
```

## 🗄️ Armazenamento

Por padrão, o ChromaDB mantém o índice vetorial em:

```text
data/vector_store/
```

É possível configurar o armazenamento por meio das variáveis de ambiente:

| Variável                  | Finalidade                             |
| ------------------------- | -------------------------------------- |
| `NEXUS_VECTOR_STORE_DIR`  | Diretório de persistência do índice    |
| `NEXUS_VECTOR_COLLECTION` | Nome da coleção vetorial               |
| `NEXUS_EMBEDDING_MODEL`   | Modelo utilizado para gerar embeddings |
| `NEXUS_RERANKER_MODEL`    | Cross-encoder utilizado no reranqueamento da camada de recuperação |
| `NEXUS_MIN_RELEVANCE`     | Score mínimo do reranker para um trecho ser usado como contexto (padrão `-3.5`) |

O diretório do índice é gerado localmente e não deve ser enviado ao Git.

## 🧪 Testes

Execute os testes com:

```bash
uv run pytest
```

Ou, utilizando o ambiente Python já ativado:

```bash
pytest
```

## 🔗 Integração com o Nexus_IA

O agente e o endpoint `/api/v1/perguntar` usam a busca vetorial com reranqueamento. A busca lexical antiga (`src/agents/document_search.py`) continua no projeto, mas não é mais usada pelo agente.

Ao indexar `data/documents/`, a primeira subpasta de cada arquivo vira a categoria (`suporte`, `comercial`, `produto`, `privacidade-legal`), e reindexar um arquivo substitui os trechos antigos dele.

## 📌 Observações

- Documentos e consultas devem utilizar o mesmo modelo de embeddings.
- Os metadados permitem organizar e filtrar os resultados da busca.
- O índice vetorial é persistido localmente pelo ChromaDB.
- A primeira execução pode exigir internet para baixar o modelo.
- Os comandos e imports devem ser conferidos com a estrutura real do projeto antes da execução.

## 👨‍💻 Projeto

**Nexus_IA** — Plataforma de busca e recuperação de informações em documentos, com recursos de inteligência artificial.
