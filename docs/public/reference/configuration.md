# Configuração

A configuração vem de variáveis de ambiente ou do arquivo `.env`, lidas por classes
`pydantic-settings` (`src/agent_app/config/settings.py`). O arquivo `.env.example` documenta cada
variável; esta página resume as mais usadas. Valores vazios usam o padrão do contrato
correspondente.

!!! danger "Segredos"
    Chaves de provedores (`OPENAI_API_KEY`, `LITELLM_API_KEY`, `BRAVE_SEARCH_API_KEY`) e
    `DATABASE_URL` só no `.env` ou no ambiente, nunca versionados. A aplicação conhece esses valores
    e os recusa em argumentos de ferramenta e na saída final.

## Modelo

| Variável | Padrão | Significado |
|---|---|---|
| `MODEL_BACKEND` | `openai` | `openai`, `litellm` ou `scripted` (modelo offline) |
| `MODEL_NAME` | vazio (padrão do SDK) | com LiteLLM, `provedor/modelo` |
| `OPENAI_BASE_URL` | vazio | gateway ou servidor compatível com a API OpenAI |
| `MODEL_FALLBACKS` | vazio | JSON: modelos de fallback com as features declaradas |
| `MODEL_RETRY_MAX_ATTEMPTS` | `3` | tentativas por modelo, incluindo a primeira |
| `MODEL_ATTEMPT_TIMEOUT_SECONDS` | `120` | por tentativa, limitado pelo prazo do run |

## Workspace e execução

| Variável | Padrão | Significado |
|---|---|---|
| `WORKSPACE_ROOT` | `./workspace` | o único diretório que as ferramentas podem tocar |
| `ALLOW_WRITES` | `false` | habilita escrita controlada (ainda sujeita a permissão e aprovação) |
| `MAX_FILE_BYTES` | `1000000` | tamanho máximo lido ou escrito |
| `MAX_TOOL_OUTPUT` | `20000` | caracteres máximos que uma ferramenta devolve ao modelo |
| `EXECUTION_BACKEND` | `local` | `local` ou `docker` (reduz o impacto; **não** é um sandbox completo) |
| `ALLOWED_COMMANDS` | `["python"]` | aliases de comando permitidos |
| `COMMAND_TIMEOUT` | `20` | segundos antes de encerrar a árvore de processos de um comando |
| `OPERATION_CLEANUP_SECONDS` | `5` | prazo para uma operação interrompida se resolver antes de ser reportada como indefinida |
| `MAX_PARALLEL_TOOL_CALLS` | `4` | chamadas de ferramenta locais simultâneas de uma resposta do modelo |

## Identidade (CLI)

| Variável | Padrão | Significado |
|---|---|---|
| `IDENTITY_TENANT_ID` | `local` | tenant dos runs locais |
| `IDENTITY_PRINCIPAL_ID` | `local-developer` | principal dos runs locais (afirmado, não autenticado) |
| `IDENTITY_PERMISSIONS` | vazio (perfil local) | lista separada por vírgulas; **substitui** o perfil local |

O perfil local padrão inclui leitura do workspace, execução de verificações, remediação, memória,
operação de runs duráveis, revisão de avaliações e pesquisa web. Ele **não** inclui
`workspace:write` nem acesso a servidores MCP (`mcp:<servidor>`).

## Orçamento

| Variável | Padrão | Significado |
|---|---|---|
| `BUDGET_MAX_TURNS` | `12` | turnos do modelo por run |
| `BUDGET_MAX_TOTAL_TOKENS` | `200000` | tokens por run |
| `BUDGET_MAX_DURATION_SECONDS` | `600` | duração ativa do run |
| `BUDGET_MAX_TOOL_CALLS` | `50` | chamadas de ferramenta (locais + MCP) |
| `BUDGET_TOOL_TIMEOUT_SECONDS` | `60` | por ferramenta local |
| `BUDGET_MAX_COST_USD` | vazio (sem limite) | custo **estimado** pelo catálogo de preços |
| `BUDGET_PRICING_FILE` | `./model_prices.json` | preços por modelo; o repositório só traz o modelo offline |
| `BUDGET_UNKNOWN_CONSUMPTION` | `stop` | um limite de tokens ou custo que não pode ser verificado encerra o run |

## Observabilidade e persistência

| Variável | Padrão | Significado |
|---|---|---|
| `LOG_LEVEL` / `LOG_FORMAT` | `INFO` / `console` | `json` para coleta |
| `TRACING_EXPORT` | `log` | `log`, `openai` (exige `OPENAI_API_KEY`) ou `none` |
| `TRACE_INCLUDE_SENSITIVE_DATA` | `false` | `true` inclui conteúdo em spans e logs: só em ambientes controlados |
| `BUILD_REVISION` | vazio | revisão do código registrada no manifesto (ex.: hash do commit) |
| `DATA_DIR` | `./.agent_app` | auditoria, runs, sessões, checkpoints, avaliações |
| `DATABASE_URL` | vazio | store de memória em PostgreSQL (extra `postgres`) |

## Human-in-the-loop

| Variável | Padrão | Significado |
|---|---|---|
| `HITL_APPROVAL_TTL_SECONDS` | `86400` | janela para decidir e retomar; depois, o run expira |
| `HITL_CHECKPOINT_DB` | `DATA_DIR/checkpoints.sqlite3` | armazenamento protegido: contém o estado dos runs |
| `HITL_LEASE_SECONDS` | `30` | lease de execução entre processos (heartbeat a cada 1/3) |
| `HITL_SELF_APPROVAL` | `local` | `never` impede também o desenvolvedor local de aprovar a própria operação |

## API HTTP

| Variável | Padrão | Significado |
|---|---|---|
| `API_KEYS_FILE` | vazio | arquivo com os hashes das chaves aceitas; vazio significa que tudo responde `401` |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | endereço do `serve` |
| `API_*` (limites) | ver [API HTTP](http-api.md#limites-por-processo) | por processo |

## Web

| Variável | Padrão | Significado |
|---|---|---|
| `WEB_MODE` | `live` | `live`, `fixture` (internet sintética) ou `disabled` |
| `WEB_SEARCH_PROVIDER` | `none` | `none`, `brave` ou `fixture` |
| `WEB_ALLOWED_DOMAINS` / `WEB_BLOCKED_DOMAINS` | vazio | política de domínios (cobre subdomínios) |
| `WEB_TENANT_POLICY_FILE` | vazio | restrição por tenant; arquivo ausente ou inválido falha fechado |

A política de rede (só endereços públicos, sem credenciais em URLs, redirects revalidados, conexão
no endereço validado) **não pode ser desligada**. Ela também não é isolamento de rede: mantenha uma
política de saída na infraestrutura.

## MCP e avaliações

| Variável | Padrão | Significado |
|---|---|---|
| `MCP_CONFIG_FILE` | `./mcp_servers.json` | servidores MCP declarados |
| `MCP_CLIENT_TIMEOUT` | `10` | segundos por chamada MCP |
| `EVAL_JUDGE_MODEL` | vazio | juiz LLM (opcional, pago) |
| `EVAL_GATES_FILE` | `./evals/gates/default.json` | política de gates |
| `EVAL_RUBRIC_FILE` | `./evals/rubrics/investigation-quality.json` | rubrica versionada |
