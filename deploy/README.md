# Deploy do Nexus-AI na Oracle Cloud (OCI)

## Arquitetura

```text
 git push (main)
     │
     ▼
 GitHub Actions ──┬─ testes (pytest)
                  ├─ imagem arm64 ─────────────▶ OCI Container Registry (OCIR)
                  ├─ data/documents ───────────▶ OCI Object Storage (bucket)
                  └─ deploy (SSH) ─┐
                                   ▼
 Colaboradores ──HTTPS──▶ VCN · subnet pública · NSG (443/80)
                           └─ VM Ampere A1 (Always Free)
                               ├─ Caddy (HTTPS + login nas rotas de manutenção)
                               └─ nexus-api (container)
                                   ├─ volume: índice ChromaDB + SQLite de monitoramento
                                   ├─ instance principal ─▶ OCI Vault (chave da Groq)
                                   └─ instance principal ─▶ Object Storage (documentos)
```

| Item da etapa | Como foi atendido |
| --- | --- |
| Containerização | `Dockerfile` (Python 3.13, PyTorch só CPU, modelos já embutidos) → OCIR |
| Compute | OCI Compute, VM `VM.Standard.A1.Flex` (Always Free) com Docker Compose |
| Documentos | OCI Object Storage. A API espelha o bucket na pasta local e reindexa só o que mudou |
| Banco vetorial | ChromaDB em volume da própria VM (ver "Decisões") |
| Segredos | OCI Vault. A aplicação lê a chave por *instance principal* e ela nunca entra em variável de ambiente |
| Rede e segurança | VCN com subnet pública, NSG liberando só 22/80/443 e HTTPS com Let's Encrypt via Caddy |
| CI/CD | GitHub Actions: testes → build → push → sincronização dos documentos → deploy → health check |

### Decisões

- **VM em vez de OKE/Container Instances.** O volume de perguntas é pequeno, a VM A1 é gratuita e tem disco persistente para o índice e o histórico de monitoramento. Para escalar, o caminho é migrar a mesma imagem para OKE.
- **ChromaDB em vez de Autonomous Database.** O índice tem cerca de 90 trechos e é reconstruído do bucket em segundos. Trocar de banco vetorial mudaria a camada de recuperação inteira, que já está validada (`CONTEXT.md`, seção 11).
- **Load Balancer dispensado.** Com uma instância só, o Caddy faz o papel de terminação HTTPS. Um OCI Load Balancer flexível (10 Mbps, Always Free) pode entrar na frente quando houver mais de uma VM.

## Passo a passo (uma vez)

Os exemplos usam a região São Paulo (`sa-saopaulo-1`, registro `gru.ocir.io`). Ajuste para a sua região.

### 1. Compartment
Identity & Security → Compartments → **Create**: `nexus-ai`. Todos os recursos abaixo ficam nele.

### 2. Rede
Networking → Virtual Cloud Networks → **Start VCN Wizard** → *Create VCN with Internet Connectivity* (`nexus-vcn`). O assistente cria as subnets pública e privada, o Internet Gateway e as rotas.

Em seguida, crie um **Network Security Group** `nexus-web` na VCN com estas regras de entrada (stateful):

| Origem | Porta TCP | Motivo |
| --- | --- | --- |
| `0.0.0.0/0` | 443 | HTTPS |
| `0.0.0.0/0` | 80 | Desafio do Let's Encrypt e redirecionamento para HTTPS |
| seu IP `/32` | 22 | SSH (o GitHub Actions também precisa, ver passo 9) |

### 3. Object Storage
Storage → Buckets → **Create Bucket** `nexus-documentos`, com acesso **privado**. Anote o *namespace* que aparece na página do bucket.

### 4. Vault
Identity & Security → Vault → **Create Vault** `nexus-vault` (*virtual vault*, gratuito).
- **Master Encryption Key**: `nexus-key`, protegida por software.
- **Secrets → Create Secret**: `groq-api-key`, tipo texto, valor = sua chave da Groq. Anote o OCID do segredo.

### 5. Container Registry
Developer Services → Container Registry → **Create repository** `nexus-ai` (privado) no compartment `nexus-ai`.

### 6. Usuário do CI e políticas
1. Identity → Groups: crie o grupo `nexus-ci` e o usuário `github-nexus`, e adicione o usuário ao grupo.
2. No usuário: **Auth Tokens → Generate** (será o `OCIR_AUTH_TOKEN`) e **API Keys → Add** (gere o par e baixe a chave privada).
3. Crie as políticas `nexus-ci-policy` no compartment `nexus-ai`:

```text
Allow group nexus-ci to use repos in compartment nexus-ai
Allow group nexus-ci to inspect buckets in compartment nexus-ai
Allow group nexus-ci to manage objects in compartment nexus-ai where target.bucket.name = 'nexus-documentos'
```

### 7. VM
Compute → Instances → **Create instance** `nexus-vm`:
- Imagem **Canonical Ubuntu 24.04** e shape **VM.Standard.A1.Flex** com 2 OCPU / 12 GB (dentro do Always Free).
- Subnet pública da `nexus-vcn`, IP público, NSG `nexus-web`.
- Sua chave SSH pública.
- *Show advanced options → Management → cloud-init*: cole o conteúdo de `deploy/cloud-init.yaml`.

### 8. Permissões da VM (instance principal)
Identity → **Dynamic Groups** → `nexus-vm` com a regra:
```text
instance.id = '<OCID da instância>'
```
Crie as políticas `nexus-vm-policy` no compartment `nexus-ai`:
```text
Allow dynamic-group nexus-vm to read secret-bundles in compartment nexus-ai where target.secret.id = '<OCID do segredo>'
Allow dynamic-group nexus-vm to read objects in compartment nexus-ai where target.bucket.name = 'nexus-documentos'
```
Só leitura de **um** segredo e de **um** bucket. Em tenancies com Identity Domains fora do domínio padrão, use `dynamic-group '<domínio>'/'nexus-vm'`.

### 9. Preparar a VM
```bash
ssh ubuntu@<IP>
docker login gru.ocir.io -u '<namespace>/github-nexus' -p '<auth token>'   # para baixar a imagem privada
cd ~/nexus-ai
nano .env        # conteúdo de deploy/.env.example preenchido
```
Gere o hash da senha das rotas de manutenção com `docker run --rm caddy:2.10.2 caddy hash-password --plaintext 'sua-senha'`.

### 10. GitHub
Settings → Secrets and variables → Actions:

| Tipo | Nome | Valor |
| --- | --- | --- |
| Variable | `OCIR_REGISTRY` | `gru.ocir.io` |
| Variable | `OCIR_NAMESPACE` | namespace do Object Storage |
| Variable | `OCI_REGION` | `sa-saopaulo-1` |
| Variable | `OCI_DOCUMENTS_BUCKET` | `nexus-documentos` |
| Secret | `OCIR_USERNAME` | `<namespace>/github-nexus` (ou `<namespace>/<domínio>/github-nexus`) |
| Secret | `OCIR_AUTH_TOKEN` | auth token do passo 6 |
| Secret | `OCI_USER_OCID`, `OCI_TENANCY_OCID`, `OCI_FINGERPRINT` | dados da API key do passo 6 |
| Secret | `OCI_PRIVATE_KEY` | conteúdo do `.pem` da API key |
| Secret | `VM_HOST` | IP público da VM |
| Secret | `VM_SSH_KEY` | chave privada SSH com acesso à VM |

Crie também o environment `producao` (Settings → Environments). Se quiser, adicione aprovação manual antes do deploy.

O deploy entra por SSH a partir dos runners do GitHub, cujos IPs mudam. Há duas opções: liberar a porta 22 para `0.0.0.0/0` no NSG, aceitando só login por chave (padrão do Ubuntu da OCI), ou usar o OCI Bastion e deixar a 22 fechada.

### 11. Primeiro deploy
Faça um push na `main` (ou rode o workflow manualmente em Actions → CI/CD → *Run workflow*). Ao subir, a API baixa os documentos do bucket e monta o índice. A primeira pergunta leva cerca de 20 s, por causa do carregamento dos modelos.

Para verificar:
- `https://<domínio>/health` → `{"status":"ok"}`
- `https://<domínio>/`: chat web
- `https://<domínio>/api/v1/metricas`: pede o login de manutenção

## Operação

| Tarefa | Como |
| --- | --- |
| Atualizar código | Push na `main`. O deploy só acontece se os testes passarem |
| Atualizar documentos | Commit em `data/documents/` (o pipeline sincroniza o bucket) ou upload direto no bucket. A API reindexa em até `NEXUS_SYNC_INTERVALO_MIN` minutos |
| Ver logs | `cd ~/nexus-ai && docker compose logs -f api` |
| Voltar versão | No `.env`, troque a tag de `NEXUS_IMAGE` pelo SHA anterior e rode `docker compose up -d` |
| Trocar a chave da Groq | Crie uma nova versão do segredo no Vault e rode `docker compose restart api` |
| Backup do monitoramento | `docker compose cp api:/app/data/monitoring/nexus.db ./nexus-$(date +%F).db` |

## Testar a integração OCI fora da nuvem
```powershell
uv sync --extra oci
$env:NEXUS_OCI_AUTH = "config"          # usa ~/.oci/config em vez de instance principal
$env:NEXUS_GROQ_SECRET_OCID = "<OCID>"
$env:NEXUS_DOCUMENTS_BUCKET = "nexus-documentos"
$env:NEXUS_SYNC_INTERVALO_MIN = "5"
uv run uvicorn nexus_ai.api:app --port 8000
```
`GROQ_API_KEY` tem prioridade sobre o Vault: comente essa linha no `.env` local durante o teste.

Atenção: com `NEXUS_DOCUMENTS_BUCKET` definido, a pasta de documentos local vira um espelho do bucket, e arquivos que não estão no bucket são apagados. Para esse teste, aponte `NEXUS_DOCUMENTS_DIR` para uma pasta temporária.
