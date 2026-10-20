# Plano de coleta e organização de documentos — Nexus_IA

**Versão:** 1.0  
**Data:** 20/10/2026  
**Etapa do projeto:** Coleta e organização documental  
**Responsável geral pelo protótipo:** Equipe do projeto Nexus_IA

## 1. Objetivo

Definir quais documentos farão parte da base de conhecimento do agente Nexus_IA, onde serão armazenados, como serão classificados, quem será responsável por sua revisão e como serão encaminhados para a ingestão inicial.

Neste desafio, o Nexus_IA é um protótipo educacional. Os documentos de produto, preços e políticas são fictícios e servem para testar a recuperação de informações por RAG. Não há conexão real com repositórios corporativos nem responsáveis de uma empresa real designados.

## 2. Escopo e premissas

- **Público do agente:** todos os colaboradores do cenário hipotético podem fazer perguntas.
- **Permissão de fontes:** o processo de ingestão deve ter acesso somente de leitura aos locais aprovados.
- **Fonte inicial:** arquivos versionados no repositório do projeto e armazenados em `data/documents/`.
- **Método inicial:** upload/cópia manual controlada, para que o protótipo funcione sem depender de integrações externas.
- **Integrações futuras:** Google Drive, SharePoint ou OneDrive poderão ser conectados quando houver credenciais, permissões e APIs configuradas.
- **Dados sensíveis:** não incluir documentos reais de RH, folha de pagamento, contratos confidenciais ou dados pessoais no conjunto de demonstração.

## 3. Mapeamento das fontes

| Fonte | Uso nesta etapa | Situação | Observações |
|---|---|---|---|
| `data/documents/` no projeto Nexus_IA | Fonte inicial de documentos | Ativa para o protótipo | Armazenamento local/versionado dos arquivos aprovados |
| Google Drive | Possível fonte corporativa | Não conectado | Exigiria integração OAuth/API e aprovação do proprietário |
| SharePoint / OneDrive | Possível fonte corporativa | Não conectado | Exigiria configuração de aplicativo e permissões de leitura |
| Intranet / ERP / RH | Possíveis fontes futuras | Fora do escopo atual | Não conectar sem autorização e análise de dados |
| E-mails arquivados | Possível fonte futura | Fora do escopo atual | Exigir critérios claros de relevância e privacidade |

## 4. Categorias documentais

Cada documento deve ter uma categoria de negócio, um tipo, uma versão, um status e um responsável pela revisão.

| Categoria | Conteúdo esperado | Responsável proposto |
|---|---|---|
| Produto | Descrição do produto, funcionalidades e limites | Responsável de Produto |
| Suporte | FAQ, procedimentos e prazos de atendimento | Responsável de Suporte |
| Privacidade e Legal | Política de privacidade, termos e regras legais | Responsável Jurídico/Privacidade |
| Comercial | Planos, preços, limites e condições comerciais | Responsável Comercial |
| Técnico | Arquitetura, operação e documentação de implementação | Responsável Técnico |

Os responsáveis são papéis sugeridos para o cenário fictício; não representam pessoas ou departamentos reais.

## 5. Inventário inicial

O inventário completo está em `05_inventario_documental.csv`. Ele registra, para cada item, nome, categoria, caminho, formato, versão, status, responsável proposto, método de ingestão e observações.

| Documento | Categoria | Formato | Status inicial |
|---|---|---|---|
| Base de conhecimento do Nexus_IA | Produto | Markdown | Aprovado para demonstração |
| FAQ de suporte | Suporte | PDF e Markdown | Aprovado para demonstração |
| Política de privacidade | Privacidade e Legal | Markdown | Rascunho demonstrativo; requer revisão jurídica para uso real |
| Planos e preços | Comercial | CSV | Aprovado para demonstração; valores fictícios |
| Termos de uso | Privacidade e Legal | DOCX | Rascunho demonstrativo; requer revisão jurídica para uso real |

## 6. Curadoria e critérios de inclusão

Antes de indexar qualquer arquivo, verificar:

1. **Relevância:** ajuda a responder perguntas previstas para o agente?
2. **Autoridade:** é uma versão oficial ou aprovada para o cenário?
3. **Atualidade:** a versão e a data de revisão estão identificadas?
4. **Duplicidade:** já existe cópia equivalente na base?
5. **Integridade:** o arquivo abre e o texto pode ser extraído corretamente?
6. **Privacidade:** contém dados pessoais, credenciais, segredos ou informações confidenciais desnecessárias?
7. **Consistência:** conflita com outro documento, por exemplo, apresentando preços diferentes?

### Regras de decisão

- **Incluir:** relevante, legível, identificado e aprovado para demonstração.
- **Revisar:** relevante, mas incompleto, sem versão ou com conteúdo potencialmente desatualizado.
- **Rejeitar:** duplicado sem necessidade, irrelevante, corrompido, não autorizado ou contendo segredos/dados sensíveis desnecessários.
- **Substituir:** uma nova versão oficial foi aprovada; a anterior deve ser retirada da indexação ativa e mantida em arquivo apenas se houver necessidade de auditoria.

## 7. Ownership e atualização

Cada categoria tem um papel responsável pela aprovação e manutenção. No protótipo, a responsabilidade fica atribuída por função, não por nome de pessoa.

| Categoria | Responsabilidade |
|---|---|
| Produto | Confirmar funcionalidades, limites e nomenclatura |
| Suporte | Validar respostas frequentes e prazos publicados |
| Comercial | Confirmar preços, planos e condições |
| Privacidade e Legal | Revisar política de privacidade e termos antes de qualquer uso real |
| Técnico | Manter inventário, formatos, pipeline de ingestão e logs de atualização |

### Gatilhos de revisão

- Alteração de preço, plano ou limite.
- Mudança em funcionalidade ou fluxo de suporte.
- Alteração legal, regulatória ou de política.
- Arquivo substituído, removido ou marcado como obsoleto.
- Resposta do agente identificada como incorreta devido a documento desatualizado.

## 8. Acesso e permissões

O agente pode estar disponível a todos os colaboradores do cenário, mas isso não significa que a ingestão deva ter acesso irrestrito a todos os sistemas.

- Usar conta de serviço com permissão **somente de leitura** nas fontes aprovadas.
- Conceder acesso mínimo necessário; evitar permissões administrativas.
- Não armazenar tokens, senhas ou chaves no repositório.
- Guardar credenciais em variáveis de ambiente ou serviço de segredos.
- Registrar fonte, data de ingestão, versão e resultado do processamento.
- Para este conjunto público/fictício, não são necessárias permissões corporativas.
- Em um ambiente real, documentos restritos não devem ser expostos a todos apenas porque o agente é acessível a todos. A autorização para recuperar trechos deve respeitar a classificação e as permissões dos documentos.

## 9. Processo de ingestão inicial

### Fase A — preparação manual

1. Colocar os arquivos aprovados em `data/documents/`.
2. Conferir os nomes e comparar com `05_inventario_documental.csv`.
3. Verificar se os arquivos abrem e se não contêm informações sensíveis.
4. Extrair texto de cada formato e registrar erros.
5. Dividir o conteúdo em trechos (*chunks*), preservando títulos e contexto.
6. Adicionar metadados como `document_id`, `category`, `source_path`, `version`, `status` e `last_reviewed`.
7. Gerar embeddings e armazenar os vetores.
8. Fazer perguntas de teste e comparar as respostas com os documentos originais.

### Fase B — sincronização futura

Quando houver integração aprovada com Drive, SharePoint ou OneDrive:

1. Identificar documentos novos, alterados e removidos.
2. Verificar permissões e metadados da fonte.
3. Processar somente arquivos elegíveis.
4. Atualizar ou remover os vetores associados à versão antiga.
5. Registrar resultado, data, erros e contagem de documentos.
6. Alertar o responsável quando houver falha, conflito ou documento vencido.

## 10. Estrutura de pastas recomendada

```text
data/
└── documents/
    ├── produto/
    │   └── 01_base_conhecimento.md
    ├── suporte/
    │   ├── 02_faq_suporte.pdf
    │   └── 02_faq_suporte.md
    ├── privacidade-legal/
    │   ├── 03_politica_privacidade.md
    │   └── 05_termos_de_uso.docx
    └── comercial/
        └── 04_planos_precos.csv
```

Se a implementação atual usar uma única pasta, é aceitável começar com `data/documents/` e organizar por subpastas posteriormente. O inventário deve sempre refletir os caminhos reais usados pelo projeto.

## 11. Checklist de conclusão

- [x] Lista inicial de documentos definida.
- [x] Categorias de negócio definidas.
- [x] Responsáveis funcionais propostos.
- [x] Critérios de curadoria definidos.
- [x] Estratégia de acesso mínimo descrita.
- [x] Ingestão inicial manual definida.
- [ ] Conferir os arquivos no diretório real do projeto.
- [ ] Implementar validação automática de tipo, tamanho e duplicidade.
- [ ] Implementar pipeline de ingestão e logs.
- [ ] Testar perguntas e validar respostas com os documentos-fonte.
- [ ] Configurar integrações automáticas somente quando autorizadas.

## 12. Critério de aceite desta etapa

A etapa estará pronta para passar ao processamento quando todos os documentos selecionados tiverem um registro no inventário, categoria definida, caminho válido, status de curadoria, versão identificada e decisão de inclusão documentada. Nenhuma fonte externa deve ser conectada sem autorização explícita.
