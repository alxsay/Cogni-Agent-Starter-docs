# Operação e implantação

O Cogni Agent Starter é uma aplicação **de um host**. Ele serve bem para desenvolvimento,
laboratório e agentes internos controlados. Esta página diz em quais condições ele roda, o que
precisa ser providenciado em volta dele e onde estão os limites.

!!! warning "Não é uma plataforma distribuída de produção"
    O estado durável usa SQLite num host; a API roda um worker por processo; limites de concorrência,
    taxa e buffers de eventos são por processo; o controle de processos é local. Escalar além disso
    exige trabalho descrito em [Próximos passos](roadmap.md).

## Ambientes suportados

| Item | Estado |
|---|---|
| Python | 3.12+ |
| Windows 10 | validado (suíte completa, verificação estática, demos, avaliações) |
| Linux (Debian 12) | validado (idem, em contêiner) |
| macOS | caminho POSIX; não faz parte da validação registrada |
| Imagem Docker (`docker/Dockerfile`) e `docker-compose.yml` | fornecidos; a imagem roda como usuário não-root (`uid 10001`) com `WORKSPACE_ROOT=/workspace` e `DATA_DIR=/data`; não fazem parte da validação registrada |

## Formas de execução

| Forma | Comando | Observação |
|---|---|---|
| CLI, uma execução | `agent-app run ...` / `agent-app workflow incident ...` | aprovação inline ou durável (`--durable`) |
| API HTTP | `agent-app serve` | um processo, um worker; padrão `127.0.0.1:8000` |
| Imagem | `docker build -f docker/Dockerfile -t agent-app .` | `ENTRYPOINT ["agent-app"]`; padrão `doctor` |
| Serviços opcionais | `docker compose -f docker/docker-compose.yml up -d postgres` | PostgreSQL só para o store de memória |

## Dados em disco

Tudo fica em `DATA_DIR` (padrão `./.agent_app`):

| Arquivo | Conteúdo | Sensibilidade |
|---|---|---|
| `checkpoints.sqlite3` | runs duráveis, pedidos de aprovação, **estado do SDK** (inclui o histórico do run), idempotência, leases | alta: proteja como dado de produção |
| `audit.jsonl` | trilha de auditoria (sem valores de argumentos) | média |
| `runs.jsonl` | log de runs com o manifesto | média |
| sessões, avaliações | histórico de sessões; relatórios e `outputs.json` das avaliações | alta para `outputs.json` |

Não há limpeza automática de dados: a retenção precisa ser feita pela operação. Checkpoints não são
criptografados em repouso; em POSIX, o arquivo é criado com permissão `0600`.

## Usando a API num ambiente interno

Checklist mínimo:

- [ ] **Chaves por pessoa** (`agent-app api new-key`), com as permissões mínimas de cada papel.
      Quem inicia runs não deve ser quem aprova. O arquivo de chaves guarda só hashes.
- [ ] **TLS e exposição de rede** por um proxy reverso; o servidor escuta em `127.0.0.1` por padrão
      e não termina TLS.
- [ ] **Usuário de SO de privilégio mínimo** para o processo, e `DATA_DIR` acessível só a ele.
- [ ] **`EXECUTION_BACKEND=docker`** para agentes que executam comandos, com uma imagem mínima.
- [ ] **`BUILD_REVISION`** definido no build, para que manifestos identifiquem o código.
- [ ] **Preços dos modelos** em `model_prices.json`, se você usa limite de custo. Sem preço, o custo
      é desconhecido, e um limite de custo recusa o modelo.
- [ ] **Antes de um deploy**, drene ou cancele os runs suspensos: um checkpoint de outro build é
      recusado na retomada.
- [ ] **Rotação de chaves** exige reinício do processo.

## Preparação por cenário de uso

| Cenário | Situação | Condições |
|---|---|---|
| **Laboratório** e desenvolvimento | adequado | modelo offline ou real; workspaces descartáveis |
| **Agentes internos somente leitura** | adequado | permissões mínimas; dados internos sob a política do workspace |
| **Agentes internos que mutam** (uso interno controlado) | adequado **com condições** | executor Docker, chaves por pessoa e separação de funções, aprovação humana para mutações, `DATA_DIR` protegido |
| **Uso comercial** | **ainda não** | faltam retenção executável, rotação e integridade da auditoria, métricas operacionais e decisões de produto sobre aprovações |
| **Execução de código não confiável** | **não** | exige isolamento forte fora do processo (contêiner restritivo, gVisor ou microVM, rede negada por padrão), ainda não implementado |

## Limites operacionais

| Limite | Consequência |
|---|---|
| SQLite em um host | runs duráveis, idempotência e leases não são compartilhados entre hosts |
| Um worker por processo de API | concorrência, taxa e buffers de eventos são locais; *N* processos significam *N* vezes os limites |
| Execução ativa vive no processo | se o processo cai, só a **suspensão** é durável; um run em execução vira órfão e é recuperado como `ambiguous` depois que o lease expira |
| Eventos SSE em memória | a reconexão retoma a partir do buffer do processo; fora dele, o `snapshot` indica `gap: true` |
| Chaves de API estáticas | sem OAuth/OIDC; rotação exige reinício |
| Rate limit e quotas | rate limit só por processo; sem quotas por tenant |
| Lease de execução | supõe um host e um relógio coerentes |
| Auditoria | síncrona, arquivo local, sem rotação embutida nem proteção contra adulteração |
| Retry de modelo | só no mesmo backend; sem *circuit breaker* |
| Tracing | sem exportador OpenTelemetry embutido: o extra `otel` instala as bibliotecas, e a integração é um `TracingProcessor` do SDK a ser implementado |

## Observabilidade em operação

| Sinal | Onde |
|---|---|
| Logs estruturados | stdout/stderr; `LOG_FORMAT=json` para coleta |
| Spans | `TRACING_EXPORT=log` (padrão), `openai` ou `none` |
| Auditoria | `DATA_DIR/audit.jsonl` |
| Runs | `DATA_DIR/runs.jsonl`; `agent-app runs show`, `agent-app runs diff` |
| Saúde | `GET /health` (o processo responde) e `GET /ready` (pronto para servir, sem chamar modelo) |

`TRACE_INCLUDE_SENSITIVE_DATA=true` inclui prompts, saídas e argumentos em spans e logs. Use só em
ambientes controlados: segredos em formatos conhecidos continuam redigidos nos logs da aplicação,
mas **não** nos spans exportados pelo SDK.
