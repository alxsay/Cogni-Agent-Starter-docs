# API HTTP

A API é um **adaptador** (FastAPI) sobre os runs duráveis do runtime: não há segundo runtime nem
segundo sistema de aprovação. Todo run iniciado pela API é durável. O schema OpenAPI fica em
`GET /openapi.json`, com UI em `/docs`.

## Subir o servidor

```bash
uv run agent-app api new-key --tenant acme --principal alice@acme.example \
  -p runs:start -p runs:read -p workspace:read
# copie a entrada JSON impressa para o arquivo apontado por API_KEYS_FILE
uv run agent-app serve --offline     # 127.0.0.1:8000, um worker; sem --offline usa o modelo configurado
```

O arquivo de chaves guarda só o SHA-256 de cada chave. A chave aparece **uma vez**, na criação:

```json
{"keys": [
  {"key_id": "alice-2026-10", "sha256": "<64 hex>", "tenant_id": "acme",
   "principal_id": "alice@acme.example",
   "permissions": ["runs:start", "runs:read", "workspace:read"]},
  {"key_id": "ci-bot", "sha256": "<64 hex>", "tenant_id": "acme", "principal_id": "svc:ci",
   "kind": "service", "permissions": ["runs:start", "runs:read"],
   "expires_at": "2027-01-01T00:00:00Z"}
]}
```

**Rotação:** adicione a entrada nova, migre os clientes, marque a antiga com `"disabled": true` (ou
`expires_at`) e reinicie. Sem nenhuma chave ativa, tudo que exige identidade responde `401` e
`/ready` responde `503`.

## Autenticação

`Authorization: Bearer <chave>`. A identidade vem **só** da chave: tenant, principal e permissões.
Nenhum cabeçalho ou campo do corpo altera a identidade. As permissões de ferramenta da chave
(`workspace:read`, `checks:execute`...) são as do run que ela inicia.

## Endpoints

| Rota | Permissão | Resposta |
|---|---|---|
| `GET /api/v1/agents` | autenticado | agentes do catálogo que o servidor executa |
| `POST /api/v1/runs` | `runs:start` | `202 {run_id, links}` + `Location` |
| `GET /api/v1/runs/{id}` | `runs:read` | estado do run (`RunView`) |
| `GET /api/v1/runs/{id}/events` | `runs:read` | `text/event-stream` |
| `POST /api/v1/runs/{id}/resume` | `runs:resume` | `202 {run_id, links}` |
| `POST /api/v1/runs/{id}/cancel` | `runs:resume` | `200`/`202` `RunView` |
| `GET /api/v1/approvals?limit=&cursor=` | `approvals:decide` | `{items, next_cursor}` |
| `GET /api/v1/approvals/{id}` | `approvals:decide` | o que exatamente seria autorizado |
| `POST /api/v1/approvals/{id}/approve` | `approvals:decide` | decisão registrada |
| `POST /api/v1/approvals/{id}/reject` | `approvals:decide` | decisão registrada |
| `GET /health` · `GET /ready` | nenhuma | probes; não chamam o modelo |

Corpo de `POST /api/v1/runs`:

```json
{"kind": "agent", "agent": "incident_investigator", "input": "Investigate INC-1042"}
```

Orçamento e limites são do servidor (`BUDGET_*`); o corpo não aceita limites.

## Ciclo completo

```bash
H="Authorization: Bearer $KEY"     # nunca em logs, nunca na URL

curl -s -X POST localhost:8000/api/v1/runs -H "$H" -H "Content-Type: application/json" \
     -H "Idempotency-Key: inc-1042-try-1" \
     -d '{"kind": "agent", "agent": "incident_investigator", "input": "Investigate INC-1042"}'

curl -N localhost:8000/api/v1/runs/<run_id>/events -H "$H"
# event: snapshot / run_started / tool_started / ... / approval_required / run_suspended

curl -s localhost:8000/api/v1/approvals/<approval_id> -H "$H2"        # outra pessoa
curl -s -X POST localhost:8000/api/v1/approvals/<approval_id>/approve -H "$H2" \
     -H "Content-Type: application/json" -d '{"reason": "verifiquei o script"}'
curl -s -X POST localhost:8000/api/v1/runs/<run_id>/resume -H "$H2"
curl -s localhost:8000/api/v1/runs/<run_id> -H "$H"     # status, result, usage, transitions
```

## Semântica

| Momento | Significado |
|---|---|
| `202` de `POST /runs` | requisição aceita **e** run iniciado: o registro durável existe |
| `running` / `resuming` | uma task deste processo executa o run (`executing: true`) |
| `waiting_approval` | suspenso e durável; nada executa |
| `completed` / `failed` / `limit_exceeded` | fim, com `result` ou `error` (código estruturado) |
| `cancelled` / `expired` | fim por operador, por cancelamento cooperativo ou por janela vencida |
| `ambiguous` | fim com efeito não confirmado |

- **Desconectar o SSE não cancela nada**: o run pertence ao supervisor do processo, não à conexão.
- **Reconexão:** envie `Last-Event-ID`. Se o evento ainda estiver no buffer do processo, chegam só
  os seguintes; senão, o `snapshot` traz `gap: true` e o estado verdadeiro é `GET /runs/{id}`.
  Eventos não são persistidos.
- **Cancelar** um run em execução responde `202`: o que não tem efeito é interrompido na hora, uma
  mutação em voo termina e nenhuma ferramenta nova começa. Um run executando em **outro** processo
  responde `409 executing_elsewhere` enquanto o lease do dono estiver vivo.
- **Idempotência:** o mesmo `Idempotency-Key` com o mesmo corpo devolve o mesmo `run_id`
  (`Idempotent-Replayed: true`); com corpo diferente, `422`.
- **Aprovar não retoma.** Decida todos os pedidos e chame `resume`. O solicitante recebe
  `403 self_approval` ao tentar aprovar a própria operação, e uma chave `service` recebe
  `403 approver_not_human`.
- **Outro tenant:** `404`.

## Eventos (SSE)

`run_started`, `run_resumed`, `model_started`, `model_completed`, `tool_started`, `tool_completed`,
`approval_required`, `approval_decided`, `run_suspended`, `cancel_requested`, `run_completed`,
`run_failed`, `run_cancelled`, `run_expired`, `run_ambiguous`.

Cada tipo tem uma **allowlist** de campos escalares: nomes, contagens, status, ids de aprovação,
operação e risco. Nunca transmite argumentos, resultados, prompts, saída do modelo ou identidades. Não
há eventos de tokens: o modelo não é chamado em modo streaming, porque um stream não pode ser
repetido com segurança.

## Erros

Formato único:

```json
{"error": {"code": "approvals_pending", "message": "...", "request_id": "req_..."}}
```

Mensagens de erro não ecoam os valores enviados.

## Limites (por processo)

| Variável | Padrão | Ao exceder |
|---|---|---|
| `API_REQUESTS_PER_MINUTE` | 120 por principal | `429 rate_limited` |
| `API_MAX_ACTIVE_RUNS` / `_PER_TENANT` | 8 / 4 | `429 too_many_active_runs` |
| `API_MAX_STREAMS` / `_PER_TENANT` | 64 / 16 | `429 too_many_streams` |
| `API_MAX_BODY_BYTES` | 64 KiB | `413 payload_too_large` |
| `API_EVENT_BUFFER_SIZE` | 512 eventos por run | `gap` na reconexão |
| `API_IDEMPOTENCY_TTL_SECONDS` | 86400 | a chave pode ser reutilizada |
| `API_SHUTDOWN_GRACE_SECONDS` | 10 | runs restantes são cancelados; cada um registra `cancelled` ou `ambiguous`, nunca sucesso |

## Limitações

- A execução ativa não sobrevive à queda do processo; só a suspensão é durável.
- Um worker por processo: limites, buffers e tokens de cancelamento são locais.
- Chaves estáticas; sem OAuth/OIDC; sem rate limit distribuído.
- SQLite (checkpoints e idempotência) num host.
