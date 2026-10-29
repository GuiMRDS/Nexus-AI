# Nexus-AI — Contextualização do Projeto

## 1. Visão geral

O **Nexus-AI** é um projeto de inteligência artificial desenvolvido para explorar a construção de agentes capazes de consultar uma base de conhecimento documental e fornecer respostas contextualizadas a partir das informações disponíveis.

O projeto integra processamento de documentos, busca textual, embeddings, armazenamento vetorial, modelos de linguagem e uma API para disponibilizar as funcionalidades do sistema.

Desenvolvido como projeto de portfólio, o Nexus-AI tem como foco inteligência artificial aplicada, arquitetura de software, organização modular e boas práticas de desenvolvimento.

## 2. Objetivos

- Desenvolver um sistema de consulta documental com inteligência artificial.
- Processar documentos locais para recuperação de informações.
- Gerar embeddings para representar conteúdos textuais em vetores numéricos.
- Armazenar e consultar vetores por meio de um banco de dados vetorial.
- Integrar a recuperação de informações com um agente baseado em modelo de linguagem.
- Disponibilizar funcionalidades por meio de uma API.
- Manter uma arquitetura modular que permita adicionar funcionalidades e agentes especializados.
- Construir uma base sólida para aplicações de IA com recuperação de conhecimento documental.

## 3. Tecnologias utilizadas

| Tecnologia            | Finalidade                                                        |
| --------------------- | ----------------------------------------------------------------- |
| Python                | Linguagem principal                                               |
| uv                    | Gerenciamento de ambiente e dependências                          |
| FastAPI               | Construção da API                                                 |
| LangChain             | Integração e orquestração de componentes de IA                    |
| Groq                  | Acesso ao modelo de linguagem por API                             |
| Sentence Transformers | Geração de embeddings                                             |
| ChromaDB              | Armazenamento e consulta de vetores                               |
| pytest                | Testes automatizados                                              |
| Pydantic              | Validação e estruturação de dados, conforme os schemas utilizados |

Modelo de embeddings configurado como padrão:

`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

As versões exatas das dependências devem ser consultadas no `pyproject.toml` e no `uv.lock`.

## 4. Arquitetura do projeto

A arquitetura separa as responsabilidades de agentes, API, processamento de documentos, armazenamento vetorial e configuração.

Estrutura conceitual baseada na organização atual:

```text
Nexus-AI/
├── data/
│   ├── documents/
│   └── vector_store/
├── data/avaliacao/
│   └── perguntas.jsonl          # conjunto de avaliação de modelos
├── design-system/               # referências visuais da interface
├── scripts/
│   ├── index_documents.py
│   ├── sync_documents.py        # atualização incremental do índice
│   ├── curadoria.py
│   ├── relatorio_qualidade.py
│   └── avaliar_modelos.py
├── src/
│   ├── agents/
│   │   ├── agent.py
│   │   ├── contacts.py
│   │   ├── document_search.py
│   │   ├── formatting.py
│   │   └── validation.py
│   ├── maintenance/
│   │   ├── avaliacao.py
│   │   └── curadoria.py
│   ├── nexus_ai/
│   │   ├── api.py
│   │   ├── config.py
│   │   ├── monitoring.py
│   │   ├── schemas.py
│   │   └── web/                 # chat web (index.html, styles.css, app.js)
│   └── processing/
│       ├── retrieval.py
│       └── store/
│           ├── embeddings.py
│           ├── indexing.py
│           ├── reranker.py
│           ├── sync.py
│           └── vector_store.py
├── tests/
│   ├── conftest.py
│   ├── test_agent.py
│   ├── test_api.py
│   ├── test_config.py
│   ├── test_contacts_formatting.py
│   ├── test_document_search.py
│   ├── test_embeddings.py
│   ├── test_indexing.py
│   ├── test_maintenance.py
│   ├── test_processing.py
│   ├── test_reranker.py
│   ├── test_retrieval.py
│   ├── test_sync.py
│   ├── test_validation.py
│   └── test_vector_store.py
├── pyproject.toml
├── uv.lock
└── README.md
```

> **Observação:** essa árvore é uma referência de contextualização. Os arquivos e diretórios devem ser conferidos no repositório antes de criar ou mover componentes. Os itens `...` representam outros arquivos existentes ou componentes cuja estrutura exata precisa ser verificada.

### 4.1. Agentes — `src/agents/`

Contém os componentes relacionados aos agentes de IA e à busca documental.

- `agent.py`: orquestra recuperação (`Retriever`), limiar de relevância, geração pelo LLM, validação com uma nova tentativa e fallback (ver seção 7.1).
- `validation.py`: controle de alucinação — `RespostaGerada` (saída estruturada do LLM), `filtrar_por_relevancia` e `validar_resposta`.
- `contacts.py`: lê a tabela de `data/documents/07_contatos_areas.md`, usada no fallback.
- `formatting.py`: formatação final por canal (`chat`, `email`, `texto`).
- `document_search.py`: busca lexical antiga. Não é mais usada pelo agente; mantida com seus testes.

### 4.2. Aplicação — `src/nexus_ai/`

Reúne componentes da aplicação, incluindo API, configurações e modelos de dados.

- `api.py`: FastAPI. Serve o chat web em `/` (arquivos em `web/`) e os endpoints `/api/v1/perguntar` (registra cada interação e devolve `interacao_id`), `/api/v1/feedback`, `/api/v1/metricas` e `/api/v1/curadoria`. Com `NEXUS_SYNC_INTERVALO_MIN > 0`, roda a sincronização de documentos em uma thread, usando o mesmo `VectorStore` do agente.
- `config.py`: carrega o `.env` e expõe `get_groq_api_key()`, `get_groq_model()`, `get_min_relevance()` e `get_sync_interval_minutes()`.
- `schemas.py`: modelos Pydantic (`AskRequest` com `canal` e `historico`, `Turno`, `AgentResponse` com `interacao_id`, `Fonte`, `FeedbackRequest`).
- `monitoring.py`: `MonitoringStore` em SQLite (`data/monitoring/nexus.db`, fora do Git). Grava interações e feedback e calcula as métricas de qualidade. Falhas de registro nunca derrubam a resposta.
- `web/`: chat em HTML/CSS/JS puros, sem build. Mostra que o interlocutor é um agente de IA, as fontes de cada resposta, o feedback 👍/👎 com motivos, o histórico da sessão (`sessionStorage`) e um painel de qualidade. O visual combina as quatro referências de `design-system/` (AETHEREAL, VITALIS, Monotone e KINETIC/ONYX).

### 4.2.1. Manutenção — `src/maintenance/` e `src/processing/store/sync.py`

- `sync.py`: `sync_directory` compara o hash de cada arquivo com um manifesto (`data/vector_store/manifest.json`). Reindexa só os arquivos novos ou alterados e remove do índice os arquivos apagados. Arquivos que falharem são tentados de novo na próxima execução.
- `curadoria.py`: cruza `05_inventario_documental.csv` com os arquivos e aponta revisão vencida, status diferente de "Aprovado", arquivo alterado após a revisão e arquivo sem inventário.
- `avaliacao.py`: roda `data/avaliacao/perguntas.jsonl` contra o agente e mede cobertura, conteúdo, respostas fora do escopo e latência. `candidato_aprovado` só aprova um modelo novo se ele não piorar nenhum desses indicadores.

### 4.3. Processamento — `src/processing/`

Responsável pelo processamento e pela preparação dos documentos para consulta.

### 4.4. Embeddings — `src/processing/store/embeddings.py`

Responsável por transformar textos em representações vetoriais utilizando Sentence Transformers.

### 4.5. Armazenamento vetorial — `src/processing/store/vector_store.py`

Responsável pela integração com o ChromaDB e pelas operações de armazenamento e recuperação vetorial.

### 4.6. Indexação — `src/processing/store/indexing.py`

Responsável pela lógica de indexação de documentos e pela preparação dos conteúdos para armazenamento vetorial.

- A categoria de cada documento vem da primeira subpasta em `data/documents/` (`suporte`, `comercial`, `produto`, `privacidade-legal`); arquivos na raiz ficam como `geral`.
- Ao reindexar um arquivo, os trechos antigos dele são removidos antes da inserção, evitando conteúdo desatualizado no índice.

### 4.6.1. Camada de recuperação — `src/processing/retrieval.py` e `src/processing/store/reranker.py`

Implementa o fluxo de recuperação do RAG: transforma a pergunta em embedding, busca os candidatos mais próximos no `VectorStore` (com filtro por metadados via `where`), reordena os candidatos com um cross-encoder (`Reranker`) e monta o bloco de contexto (`montar_contexto_vetorial`) com as fontes para o prompt do LLM.

O contexto de cada trecho inclui arquivo, seção, localização (página/linhas/slide, quando houver), área e data de atualização. É a camada usada pelo agente.

### 4.7. Script de indexação — `scripts/index_documents.py`

Ponto de entrada para executar a rotina de indexação dos documentos.

### 4.8. Testes — `tests/`

Contém testes automatizados para os principais componentes da aplicação.

## 5. Fluxo de processamento e indexação

O fluxo de indexação prepara os documentos para consultas posteriores.

1. Os documentos são disponibilizados em `data/documents/`.
2. O pipeline identifica os arquivos presentes no diretório.
3. Os documentos passam pela extração de conteúdo suportada pela implementação existente.
4. O conteúdo é dividido em unidades menores chamadas _chunks_.
5. O modelo de embeddings transforma os textos em representações vetoriais.
6. Os vetores e seus dados associados são preparados para armazenamento no ChromaDB.
7. O índice fica disponível para utilização pelas funcionalidades de recuperação de informações.

A implementação deve preservar os metadados necessários para identificar a origem dos conteúdos, conforme o formato adotado pelo pipeline.

### Executar a indexação

```powershell
uv run python scripts/index_documents.py
```

O script apresenta um resumo da execução, incluindo o diretório processado, a quantidade de arquivos encontrados, os arquivos indexados, os chunks gerados e eventuais erros.

### Último resultado registrado

Na última execução informada (2026-10-28):

| Métrica              | Resultado |
| -------------------- | --------: |
| Arquivos encontrados |         9 |
| Arquivos indexados   |         9 |
| Chunks indexados     |        88 |
| Erros de indexação   |         0 |

Esses valores representam uma execução específica e podem variar conforme os documentos presentes no diretório.

## 6. Embeddings e armazenamento vetorial

Embeddings representam o conteúdo textual em um espaço vetorial, permitindo comparar textos por similaridade.

O Nexus-AI utiliza Sentence Transformers para gerar essas representações e ChromaDB para armazená-las e recuperá-las.

Modelo configurado como padrão:

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

A utilização de um modelo multilíngue permite trabalhar com conteúdo em português e em outros idiomas suportados pelo modelo.

O armazenamento vetorial complementa a busca documental existente com uma abordagem baseada em similaridade semântica.

**Diretriz de desenvolvimento:** manter a implementação simples e modular. Não introduzir serviços adicionais, bancos de dados ou frameworks de recuperação sem necessidade concreta.

## 7. Agente de IA e integração com Groq

O projeto utiliza LangChain para integrar o agente ao modelo de linguagem disponibilizado pela Groq.

A arquitetura prevê o uso de componentes de recuperação de informações para fornecer contexto ao processo de geração de respostas.

A recuperação documental e a geração de respostas devem permanecer responsabilidades distinguíveis, facilitando testes, manutenção e evolução.

### 7.1. Geração e validação de respostas (parte 5)

Fluxo de `executar_agente(pergunta, historico)` (`src/agents/agent.py`):

1. **Recuperação:** `Retriever.retrieve(pergunta, limit=5, candidate_limit=20)`. Se nenhum trecho passar do limiar e houver histórico, tenta de novo com a pergunta anterior concatenada à atual, o que cobre perguntas de continuação. O histórico (até 3 turnos) também entra no prompt, marcado como "não é fonte". A validação numérica continua aceitando só os números dos trechos e da pergunta atual.
2. **Limiar de confiança:** `filtrar_por_relevancia` descarta trechos com score do reranker abaixo de `NEXUS_MIN_RELEVANCE` (padrão `-3.5`; o cross-encoder devolve logits). Sem nenhum trecho acima do limiar, o LLM **não é chamado** e o agente responde com o fallback.
3. **Geração:** o LLM recebe pergunta + trechos numerados (`[Documento N]`) e é instruído a responder só com base neles. Saída estruturada `RespostaGerada`: `resposta`, `encontrou_resposta`, `documentos_citados`.
4. **Validação de consistência** (`validar_resposta`, determinística): resposta afirmativa precisa citar documentos existentes, e todo número da resposta (preços, limites, prazos, datas) precisa aparecer nos documentos citados ou na pergunta. Se falhar, o LLM gera de novo **uma vez** recebendo os problemas; se falhar outra vez, vira fallback.
5. **Citação:** as `fontes` (arquivo, seção, localização, área, atualizado_em) são montadas pelo código a partir dos metadados dos trechos citados — nunca do texto do modelo.
6. **Fallback:** "Não encontrei essa informação nos documentos disponíveis.", aviso de possível fora de escopo e a lista de contatos das áreas lida de `data/documents/07_contatos_areas.md` (contatos demonstrativos, domínio `.example`). Também é usado quando o LLM marca `encontrou_resposta=false`.
7. **Formatação:** a API devolve `resposta_formatada` conforme `canal` (`chat` = Markdown, `email`, `texto` para Teams/Slack sem Markdown): resumo direto seguido das referências.

Calibração do limiar (2026-10-28, modelos reais): perguntas cobertas tiveram score máximo entre -3,04 e 10,3; perguntas fora do escopo entre -8,6 e -2,83. As faixas se sobrepõem levemente, então casos limítrofes chegam ao LLM, que é a segunda barreira (`encontrou_resposta=false`).

### Variáveis de ambiente

As variáveis utilizadas durante o desenvolvimento são:

```dotenv
GROQ_API_KEY=sua_chave_aqui
GROQ_MODEL=openai/gpt-oss-120b
```

- `GROQ_API_KEY`: chave de acesso à API da Groq.
- `GROQ_MODEL` (opcional): identificador do modelo na Groq. Se ausente ou vazio, usa `openai/gpt-oss-120b`.
- `NEXUS_MIN_RELEVANCE` (opcional): score mínimo do reranker para um trecho virar contexto. Padrão `-3.5`.
- `NEXUS_MONITORING_DB` (opcional): caminho do SQLite de monitoramento.
- `NEXUS_SYNC_INTERVALO_MIN` (opcional): ativa a sincronização periódica dentro da API.
- `NEXUS_DOCUMENTS_DIR` (opcional): pasta de documentos usada pela API.
- `NEXUS_CURADORIA_PRAZO_DIAS` (opcional): prazo de revisão dos documentos (padrão 90).
- `NEXUS_GROQ_SECRET_OCID` (deploy): OCID do segredo da chave da Groq no OCI Vault, usado quando `GROQ_API_KEY` não está definida.
- `NEXUS_DOCUMENTS_BUCKET` / `NEXUS_DOCUMENTS_PREFIX` (deploy): bucket do Object Storage espelhado em `NEXUS_DOCUMENTS_DIR` antes de cada sincronização. Arquivos locais ausentes no bucket são apagados.
- `NEXUS_OCI_AUTH` (deploy): `config` usa `~/.oci/config`; o padrão é *instance principal*.

Os valores são ilustrativos. O nome do modelo e sua disponibilidade devem ser conferidos na configuração atual.

A chave de API deve permanecer em um arquivo `.env` local ou em outro mecanismo seguro de configuração. Nunca deve ser incluída no código-fonte, neste documento ou em um repositório público.

## 8. Configuração do ambiente

### Pré-requisitos

- Python compatível com as dependências do projeto.
- uv instalado.
- Acesso à internet para instalar dependências e baixar o modelo de embeddings na primeira utilização.
- Chave de API da Groq para funcionalidades que dependam do modelo de linguagem.

### Instalação das dependências

Na raiz do projeto:

```powershell
uv sync
```

As dependências devem ser mantidas no `pyproject.toml`, com as versões resolvidas registradas no `uv.lock`.

### Configuração dos documentos

Crie o diretório de entrada, caso ainda não exista:

```powershell
New-Item -ItemType Directory -Force .\data\documents
```

Coloque os documentos a serem processados nesse diretório, respeitando os formatos suportados pelo extrator existente.

## 9. Execução e testes

### Indexar documentos

```powershell
uv run python scripts/index_documents.py
```

### Subir a API e o chat web

```powershell
uv run uvicorn nexus_ai.api:app --host 0.0.0.0 --port 8000
```

O chat fica em `http://localhost:8000/`.

### Rotinas de manutenção

```powershell
uv run python scripts/sync_documents.py            # uma vez; --intervalo 60 para repetir
uv run python scripts/curadoria.py
uv run python scripts/relatorio_qualidade.py --dias 30
uv run python scripts/avaliar_modelos.py --modelos openai/gpt-oss-120b <candidato>
```

### Executar a suíte de testes

```powershell
uv run pytest
```

Os testes abrangem componentes da API, configuração, busca documental, embeddings, reranqueamento, camada de recuperação, processamento e armazenamento vetorial.

### Estado mais recente dos testes

Na última execução informada (2026-10-28):

- 85 testes foram coletados.
- 85 testes passaram.
- 0 testes falharam.

`tests/conftest.py` aponta `NEXUS_MONITORING_DB` para uma pasta temporária, então os testes nunca gravam em `data/monitoring/`.

A falha anterior em `tests/test_embeddings.py` (`.tolist()` sobre uma lista Python do modelo falso) já foi corrigida em `src/processing/store/embeddings.py`, que agora aceita listas Python e arrays NumPy.

Também foi corrigido um bug encontrado por teste manual do endpoint `/api/v1/perguntar`: `executar_agente` (`src/agents/agent.py`) sempre retornava `usou_rag: false`, mesmo quando a busca documental encontrava e usava trechos reais. Agora `usou_rag` reflete se houve fontes.

Validação da interface e manutenção (2026-10-28, modelos reais + Groq): o chat em `/`, o histórico, o feedback e as métricas funcionaram de ponta a ponta. Com histórico, "E quantos membros ele permite?" depois de uma pergunta sobre o Empresarial foi respondida com "Até 100 membros". Sem histórico, o modelo cobriu Pro e Empresarial. A interface foi conferida por screenshot nos temas claro e escuro, em 1440px e em 390px. A primeira pergunta após subir a API leva cerca de 20 s (carregamento dos modelos); as seguintes, cerca de 2 s. `scripts/avaliar_modelos.py` ainda não foi executado contra a Groq.

Validação manual de ponta a ponta (2026-10-28, modelos reais + Groq): perguntas cobertas (limites do Gratuito, preço do Pro, prazo de suporte, contato comercial, dados pessoais coletados) foram respondidas com fontes corretas; perguntas fora do escopo (férias, imposto de renda, capital da Austrália) caíram no fallback com os contatos das áreas.

## 9.1. Deploy na OCI

Guia completo em `deploy/README.md`. Resumo:

- `Dockerfile`: imagem arm64 com Python 3.13, PyTorch só CPU (índice `pytorch-cpu` do `pyproject.toml`, aplicado só no Linux), Tesseract e os dois modelos já baixados. O código roda de `/app/src` e os dados ficam no volume `/app/data`.
- Compute: VM Ampere A1 (Always Free) com `deploy/compose.yaml` (API + Caddy com HTTPS e login nas rotas de manutenção).
- `src/nexus_ai/oci_cloud.py`: lê o segredo do OCI Vault e espelha o bucket do Object Storage, por *instance principal*. O SDK `oci` é o extra opcional `oci`.
- CI/CD: `.github/workflows/deploy.yml` (testes → imagem no OCIR → `oci os object sync` dos documentos → deploy por SSH → health check).
- Estado: os arquivos foram criados e os testes passam, mas o build da imagem e o deploy ainda **não** foram executados (não há Docker nem OCI CLI na máquina de desenvolvimento).

## 10. Estado atual do desenvolvimento

### Implementado ou executado com sucesso

- Busca local de documentos.
- Pipeline de processamento e extração existente.
- Integração com embeddings e ChromaDB.
- Script de indexação.
- Indexação de 9 arquivos, com 88 chunks e nenhum erro na última execução informada.
- Camada de recuperação (RAG) — `src/processing/retrieval.py`: busca semântica com filtro por metadados + reranqueamento via cross-encoder (`src/processing/store/reranker.py`) + montagem de contexto com fontes.
- Agente integrado ao `Retriever`, com limiar de relevância, validação de consistência, citação de fontes, fallback com contatos das áreas e formatação por canal (seção 7.1).
- Chat web (`/`) com indicação de agente de IA, fontes, feedback 👍/👎 com motivos, histórico de sessão e painel de qualidade.
- Registro de interações e feedback em SQLite, com métricas em `/api/v1/metricas` e `scripts/relatorio_qualidade.py`.
- Sincronização incremental de documentos (script ou thread na API), relatório de curadoria e avaliação comparativa de modelos.
- Testes automatizados para os principais componentes, todos passando (93/93 em 2026-10-29, incluindo `tests/test_oci_cloud.py`).
- Artefatos de deploy na OCI (seção 9.1), ainda não executados na nuvem.

### Em validação

- Limiar de relevância calibrado com poucas perguntas; recalibrar com um conjunto de avaliação maior.
- A validação numérica pode rejeitar respostas corretas que façam cálculos (ex.: diferença entre preços).
- O FAQ está indexado em PDF e Markdown, o que duplica fontes (o próprio inventário recomenda indexar só um).
- Comportamento da API e tratamento de erros.

- Endpoints `/api/v1/metricas` e `/api/v1/curadoria` não têm autenticação e expõem perguntas dos colaboradores; em produção, precisam ficar atrás de rede interna ou proxy com login.
- O conjunto `data/avaliacao/perguntas.jsonl` tem 15 casos; ainda não foi rodado contra a Groq.

### Próximas etapas possíveis

1. Rodar `scripts/avaliar_modelos.py` com o modelo atual para ter a linha de base e recalibrar o limiar.
2. Decidir entre o PDF e o Markdown do FAQ para evitar fontes duplicadas.
3. Proteger os endpoints de manutenção e preparar a implantação (servidor interno, HTTPS, agendamento da sincronização).
4. Bot de Teams/Slack usando `canal: "texto"`, se a empresa trabalhar nessas ferramentas.
5. Avaliar melhorias arquiteturais conforme as necessidades reais do projeto.

Os itens futuros não devem ser considerados concluídos até serem implementados e verificados.

## 11. Diretrizes para evolução

Ao realizar alterações no Nexus-AI, devem ser respeitadas as seguintes diretrizes:

- Inspecionar os arquivos existentes antes de criar ou substituir componentes.
- Preservar funcionalidades que já estejam funcionando.
- Evitar refatorações amplas sem necessidade.
- Manter a extração de documentos na estrutura atual, sem fragmentá-la desnecessariamente.
- Não introduzir RAG mais complexo, bancos vetoriais alternativos ou infraestrutura adicional sem solicitação ou justificativa técnica.
- Organizar os agentes por responsabilidade, permitindo a inclusão de agentes especializados futuramente.
- Preferir alterações pequenas, verificáveis e cobertas por testes.
- Não alterar nomes de variáveis de ambiente sem atualizar todos os pontos de utilização.
- Não declarar testes aprovados sem executar a suíte e verificar o resultado.
- Atualizar a documentação quando a arquitetura ou o comportamento do sistema mudar.

## 12. Contexto para futuras sessões de desenvolvimento

Este documento serve como referência de continuidade para futuras sessões de desenvolvimento, revisões de código e utilização de ferramentas de IA.

Antes de sugerir alterações, deve-se considerar o estado atual do repositório, os arquivos efetivamente existentes e os resultados mais recentes dos testes.

Quando houver dúvidas sobre a implementação, deve-se inspecionar o código relevante em vez de presumir que uma estrutura sugerida anteriormente já foi criada.

O objetivo é evoluir o Nexus-AI de maneira incremental, mantendo a estabilidade dos componentes existentes e construindo uma base confiável para aplicações de inteligência artificial com recuperação de conhecimento documental.

---

**Projeto:** Nexus-AI  
**Linguagem principal:** Python  
**Objetivo:** agente de IA com consulta a uma base de conhecimento documental  
**Status:** desenvolvimento e validação incremental
