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
├── scripts/
│   └── index_documents.py
├── src/
│   ├── agents/
│   │   ├── agent.py
│   │   └── document_search.py
│   ├── nexus_ai/
│   │   ├── api.py
│   │   ├── my_models.py
│   │   └── ...
│   └── processing/
│       └── store/
│           ├── embeddings.py
│           ├── indexing.py
│           └── vector_store.py
├── tests/
│   ├── test_api.py
│   ├── test_config.py
│   ├── test_document_search.py
│   ├── test_embeddings.py
│   ├── test_processing.py
│   └── test_vector_store.py
├── pyproject.toml
├── uv.lock
└── README.md
```

> **Observação:** essa árvore é uma referência de contextualização. Os arquivos e diretórios devem ser conferidos no repositório antes de criar ou mover componentes. Os itens `...` representam outros arquivos existentes ou componentes cuja estrutura exata precisa ser verificada.

### 4.1. Agentes — `src/agents/`

Contém os componentes relacionados aos agentes de IA e à busca documental.

- `agent.py`: implementação do agente baseado em modelo de linguagem.
- `document_search.py`: componente de busca local de documentos utilizado na recuperação de informações.

### 4.2. Aplicação — `src/nexus_ai/`

Reúne componentes da aplicação, incluindo API, configurações e modelos de dados.

- `api.py`: camada de API construída com FastAPI.
- `my_models.py`: configurações ou definições de modelos utilizados pelo projeto, conforme a implementação atual.

### 4.3. Processamento — `src/processing/`

Responsável pelo processamento e pela preparação dos documentos para consulta.

### 4.4. Embeddings — `src/processing/store/embeddings.py`

Responsável por transformar textos em representações vetoriais utilizando Sentence Transformers.

### 4.5. Armazenamento vetorial — `src/processing/store/vector_store.py`

Responsável pela integração com o ChromaDB e pelas operações de armazenamento e recuperação vetorial.

### 4.6. Indexação — `src/processing/store/indexing.py`

Responsável pela lógica de indexação de documentos e pela preparação dos conteúdos para armazenamento vetorial.

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

Na última execução informada:

| Métrica              | Resultado |
| -------------------- | --------: |
| Arquivos encontrados |         8 |
| Arquivos indexados   |         8 |
| Chunks indexados     |        86 |
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

### Variáveis de ambiente

As variáveis utilizadas durante o desenvolvimento são:

```dotenv
GROQ_API_KEY=sua_chave_aqui
GROQ_MODEL_LLAMA=modelo_configurado_no_projeto
```

- `GROQ_API_KEY`: chave de acesso à API da Groq.
- `GROQ_MODEL_LLAMA`: identificador do modelo configurado na aplicação.

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

### Executar a suíte de testes

```powershell
uv run pytest
```

Os testes abrangem componentes da API, configuração, busca documental, embeddings, processamento e armazenamento vetorial.

### Estado mais recente dos testes

Na última execução informada:

- 21 testes foram coletados.
- 19 testes passaram.
- 2 testes falharam em `tests/test_embeddings.py`.

As falhas ocorreram porque o método `_encode()` chamou `.tolist()` sobre uma lista Python retornada pelo modelo falso utilizado nos testes.

A correção proposta foi tornar a conversão compatível com listas Python e arrays NumPy. A aprovação final depende de executar novamente a suíte após a alteração.

## 10. Estado atual do desenvolvimento

### Implementado ou executado com sucesso

- Busca local de documentos.
- Pipeline de processamento e extração existente.
- Integração inicial com embeddings.
- Integração com ChromaDB.
- Script de indexação.
- Indexação de 8 arquivos, com 86 chunks e nenhum erro na última execução informada.
- Testes automatizados para os principais componentes.

### Em validação

- Correção e aprovação integral dos testes de embeddings.
- Consistência entre busca local e busca vetorial.
- Integração completa entre recuperação de contexto e agente de IA.
- Comportamento da API e tratamento de erros.

### Próximas etapas possíveis

1. Executar novamente a suíte completa de testes.
2. Validar consultas reais ao índice vetorial.
3. Verificar a integração da recuperação de contexto com o agente.
4. Validar os endpoints da API.
5. Melhorar a documentação de instalação e exemplos de uso.
6. Preparar a aplicação para implantação após validar o fluxo local.
7. Avaliar melhorias arquiteturais conforme as necessidades reais do projeto.

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
