# CLI

O executável é `agent-app` (equivalente: `uv run python -m agent_app`). Todo comando aceita
`--help`. A identidade dos comandos locais vem de `IDENTITY_*` e é afirmada por configuração.

## Execução

| Comando | O que faz | Opções principais |
|---|---|---|
| `doctor` | verifica Python, dependências, configuração, workspace, modelo, MCP e a integridade das instruções versionadas | |
| `run "<prompt>"` | executa um agente do catálogo uma vez sobre `WORKSPACE_ROOT` e imprime a saída estruturada | `--agent <id>` (padrão `incident_investigator`), `--offline`, `--approve ask\|auto\|deny`, `--durable`, `--session <id>`, `--with-mcp` |
| `run-demo` | workflow de incidente de ponta a ponta numa cópia descartável do workspace de exemplo | `--live` |
| `workflow incident <id>` | workflow de incidente sobre `WORKSPACE_ROOT` (a remediação exige `ALLOW_WRITES=true`) | `--offline`, `--approve`, `--durable` |
| `research ["<pergunta>"]` | executa o pesquisador web (`web_search` + `web_fetch`) | `--offline` (internet sintética) |
| `lifecycle-demo` | concorrência, cancelamento e limpeza, offline; exit 1 se uma afirmação falhar | |
| `serve` | serve a API HTTP (um processo, um worker) | `--host`, `--port`, `--offline` |

## Catálogo e ferramentas

| Comando | O que faz |
|---|---|
| `agents list` | agentes do catálogo: o que `run --agent`, runs duráveis e a API podem executar |
| `tools list` | ferramentas registradas, com capability, risco e origem |
| `mcp serve` | serve o servidor MCP de exemplo (stdio) |
| `mcp list` | descobre as capabilities dos servidores MCP configurados |

## Runs duráveis e aprovações

| Comando | O que faz | Permissão |
|---|---|---|
| `approvals list` | operações do seu tenant esperando decisão | `approvals:decide` |
| `approvals show <approval_id>` | o que exatamente seria autorizado (argumentos redigidos e encurtados) | `approvals:decide` |
| `approvals approve <approval_id> [--reason "..."]` | aprova uma operação; retome o run separadamente | `approvals:decide` |
| `approvals reject <approval_id> [--reason "..."]` | rejeita uma operação; o agente é informado e pode continuar sem ela | `approvals:decide` |
| `runs resume <run_id> [--offline]` | continua um run suspenso depois que suas aprovações foram decididas | `runs:resume` |
| `runs cancel <run_id>` | encerra um run durável: `cancelled` se suspenso; um run executando em outro processo é recusado enquanto o lease dele vive | `runs:resume` (`runs:recover` para órfãos) |
| `runs show <run_id>` | status, aprovações pendentes e transições | `runs:read` |
| `runs diff <run_a> <run_b>` | compara o que definiu dois runs (manifestos persistidos) | `runs:read` |
| `sessions show <session_id>` | runs registrados para uma sessão do tenant configurado | |

## Avaliações

| Comando | O que faz |
|---|---|
| `eval [--dataset <path>] [--offline] [--min-pass-rate <x>]` | forma antiga: roda o dataset legado |
| `eval run --dataset <nome\|caminho>` | roda um dataset, salva o relatório, compara com uma baseline e aplica os gates. Opções: `--offline`, `--baseline`, `--gates`, `--judge`, `--case <id>`, `--save-baseline <path>`, `--no-lock` |
| `eval report <id>` | mostra um relatório salvo (sem conteúdo) |
| `eval compare <base> <candidato>` | compara dois relatórios caso a caso e aplica os gates ao candidato |
| `eval review <id> <case_id>` | mostra um caso para revisão, ou registra a revisão (`--verdict`, `--score`, `--notes`, `--replace`) |
| `eval reviews <id>` | histórico de revisões humanas |
| `eval lock --dataset <id>` | registra uma versão do dataset no lock (versão publicada é imutável) |

## API

| Comando | O que faz |
|---|---|
| `api new-key --tenant <t> --principal <p> -p <permissão> ...` | gera uma chave de API: imprime a chave **uma vez** e a entrada (com hash) para `API_KEYS_FILE`. Opções: `--key-id`, `--service` |

## Códigos de saída

| Comando | Exit |
|---|---|
| `run`, `workflow` | `0` sucesso; `2` entrada ou saída recusada por guardrail; demais códigos indicam erro |
| `eval run` | `0` aprovado, `1` reprovado por gate, `2` uso incorreto, `3` dataset inválido, `4` infraestrutura, `5` avaliação incompleta |
| `lifecycle-demo` | `1` se alguma afirmação falhar |
