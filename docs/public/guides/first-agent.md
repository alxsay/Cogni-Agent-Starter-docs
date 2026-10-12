# Construindo seu primeiro agente

Este guia constrói um agente completo, o `error_reporter`. Ele conta as linhas `ERROR` nos logs do
workspace e salva um relatório, mas **só** depois que uma pessoa aprova a escrita. O exemplo é
pequeno, mas passa por todas as peças que um agente real usa:

| Peça | No exemplo |
|---|---|
| Instruções versionadas | `PromptTemplate` com versão e `pinned_hash` |
| Saída estruturada | `ErrorReport` (Pydantic, schema estrito) |
| Ferramentas | `search_text` (embutida, somente leitura) + `save_report` (própria, mutação) |
| Permissões | `workspace:read` e `workspace:write`, derivadas das capabilities das ferramentas |
| Aprovação humana | `save_report` declara `HumanApproval`; na API, o run **suspende** até outra pessoa aprovar |
| Orçamento | `ExecutionBudget` definido pelo código que inicia o run |
| Registro | um `CatalogAgent` |
| Execução | por código, pela CLI e pela API HTTP |
| Testes e avaliação | pytest offline + um dataset de avaliação com caso durável |

!!! success "Código verificado"
    Os arquivos mostrados aqui são incluídos **diretamente** dos arquivos do exemplo, e não
    copiados à mão. Eles foram executados numa cópia limpa do repositório: os testes passam,
    o agente roda pela CLI e pela API, e Ruff e Pyright (modo estrito) não acusam nada. Você pode
    baixá-los pelos links de cada seção.

## Estrutura

Nenhum arquivo existente do starter precisa mudar. Você adiciona dois diretórios:

```text
src/my_agents/
    __init__.py
    error_reporter.py          # o agente: prompt, contrato, ferramenta, modelo offline, registro
    run_error_reporter.py      # executa o agente por código
    serve.py                   # serve a API HTTP com o catálogo que inclui o agente
tests/my_agents/
    __init__.py
    test_error_reporter.py     # testes offline (runner, permissões, aprovação, API, avaliação)
    error-reporter.eval.json   # dataset de avaliação
```

`src/` já está no caminho de importação do ambiente criado por `uv sync`, então `my_agents` é
importável pelo `uv run`, pelos testes e pela CLI. Ruff e Pyright já verificam `src/` e `tests/`.

## Passo 1: o agente

O arquivo inteiro está abaixo; as seções numeradas do código são explicadas em seguida.
[Baixar `error_reporter.py`](first-agent/src/my_agents/error_reporter.py).

```python title="src/my_agents/error_reporter.py"
--8<-- "src/my_agents/error_reporter.py"
```

### 1. Instruções versionadas

`PromptTemplate` carrega o texto, um id estável, uma versão legível e o **hash do conteúdo**
(`pinned_hash`). O manifesto de cada run registra a versão declarada **e** o hash real. O
`agent-app doctor` e o teste `test_the_prompt_is_pinned` acusam um texto alterado sem nova versão.

Para obter o hash depois de escrever ou mudar o texto:

```bash
uv run python -c "from my_agents.error_reporter import INSTRUCTIONS; print(INSTRUCTIONS.content_hash)"
```

Mudou o texto? Incremente `version` e atualize `pinned_hash` juntos.

!!! warning "Conteúdo de ferramentas é dado, não instrução"
    As instruções dizem explicitamente que resultados de ferramentas são dados não confiáveis. A
    fronteira de ferramentas também os marca com `<untrusted-data>`. A instrução orienta o modelo;
    a **segurança** vem das permissões e da fronteira de execução, não do prompt.

### 2. Contrato de saída

`ErrorReport` é um modelo Pydantic **sem valores padrão**: o SDK gera um JSON schema estrito, e a
resposta final do modelo precisa satisfazê-lo. Quem chama recebe um objeto tipado, não texto.

### 3. Ferramenta própria com aprovação

`save_report` é uma **mutação local**:

- `needs_approval=HumanApproval(OperationRisk.LOCAL_MUTATION, Capability.FS_WRITE)` diz ao SDK que
  esta ferramenta pode exigir uma pessoa. Em execuções duráveis, o loop é interrompido **antes**
  dela.
- O corpo chama **`invoke_tool`**, a fronteira única das ferramentas locais. Ela aplica, nesta
  ordem: orçamento → autorização (`fs.write` exige `workspace:write`) → política de argumentos →
  aprovação → execução registrada no ledger → saída sanitizada → auditoria.
- O trabalho bloqueante roda em `ctx.context.operations.run_sync(...)`, e não em
  `asyncio.to_thread`, para que o ledger saiba se a escrita ainda está executando.
- A escrita usa `filesystem.write_file`, que passa pelo `Workspace`: caminho validado, escrita só
  com `ALLOW_WRITES=true`, limite de tamanho.

### 4. Menor privilégio

`build_error_reporter` seleciona **só** as ferramentas de que o agente precisa, com teto de risco
`LOCAL_MUTATION`. Ele não recebe `read_file`, `run_check` nem ferramentas web. Os guardrails padrão
de entrada e saída são anexados.

### 5. Modelo offline

`error_reporter_offline_model()` é um `ScriptedModel`: uma sequência de passos que recebe o
*transcript* (os resultados reais das ferramentas) e devolve a próxima resposta do "modelo". Ele
roda **dentro** do `Runner` real do SDK, então testes e CI exercitam a fronteira de ferramentas,
autorização, aprovação, orçamento e manifesto de verdade, sem chamadas pagas.

!!! note "O que o modelo offline prova"
    Prova que o runtime se comporta corretamente diante das decisões que o roteiro simula. Não
    prova a qualidade do agente com um modelo real: isso se mede com avaliações *live*.

### 6. Registro

`ERROR_REPORTER` é o `CatalogAgent`: definição, função de construção, contrato, features que o
modelo precisa ter, modelo offline e ferramentas próprias. `catalog()` devolve o catálogo do starter
mais este agente.

## Passo 2: permissões

A permissão exigida vem da **capability** de cada ferramenta:

| Ferramenta | Capability | Permissão exigida |
|---|---|---|
| `search_text` | `search` | `workspace:read` |
| `save_report` | `fs.write` | `workspace:write` |

A identidade local (CLI e scripts) é afirmada por `IDENTITY_*`. O perfil local padrão **não**
inclui `workspace:write`, porque nenhum agente escreve arquivos por padrão. Para este agente:

```bash
IDENTITY_PERMISSIONS=workspace:read,workspace:write
ALLOW_WRITES=true
```

`ALLOW_WRITES` é a política do workspace; a permissão é da identidade. As duas são necessárias, e
ainda assim a escrita passa pela aprovação.

!!! danger "Use uma cópia do workspace"
    O agente escreve em `notes/error-report.md`. Aponte `WORKSPACE_ROOT` para uma **cópia** do
    workspace de exemplo, não para `examples/incident_workspace`.

## Passo 3: orçamento

O orçamento é do **run** e é definido por quem o inicia, nunca pelo modelo:

```python
budget=ExecutionBudget(max_turns=6, max_tool_calls=4, max_duration_seconds=120)
```

Sem um orçamento explícito, valem os padrões de `BUDGET_*`. Esgotado um limite obrigatório, nenhuma
operação nova começa e o run termina `limit_exceeded`.

## Passo 4: executar por código

[Baixar `run_error_reporter.py`](first-agent/src/my_agents/run_error_reporter.py).

```python title="src/my_agents/run_error_reporter.py"
--8<-- "src/my_agents/run_error_reporter.py"
```

Repare em `configure_tracing(settings)`: um script próprio deve aplicar a configuração de
observabilidade do app, como a CLI faz, para que `TRACING_EXPORT` e
`TRACE_INCLUDE_SENSITIVE_DATA` valham também para ele.

=== "Linux / macOS"

    ```bash
    cp -r examples/incident_workspace /tmp/er-workspace
    MODEL_BACKEND=scripted WORKSPACE_ROOT=/tmp/er-workspace ALLOW_WRITES=true \
      IDENTITY_PERMISSIONS=workspace:read,workspace:write \
      uv run python -m my_agents.run_error_reporter
    ```

=== "Windows (PowerShell)"

    ```powershell
    Copy-Item -Recurse examples/incident_workspace $env:TEMP\er-workspace
    $env:MODEL_BACKEND = "scripted"; $env:WORKSPACE_ROOT = "$env:TEMP\er-workspace"
    $env:ALLOW_WRITES = "true"; $env:IDENTITY_PERMISSIONS = "workspace:read,workspace:write"
    uv run python -m my_agents.run_error_reporter
    ```

Saída (offline):

```text
{
  "error_count": 2,
  "files": [
    "logs/processor.log"
  ],
  "report_saved": true
}
search_text: ok
save_report: ok
{"turns":3,"tool_calls":2}
```

`MODEL_BACKEND=scripted` usa o modelo offline. Para um modelo real, remova essa variável e configure
o provedor no `.env`. Neste script, `StaticApprover(approve=True)` aprova automaticamente: é um run
**não assistido**, adequado a um workspace descartável. Com `StaticApprover(approve=False)`, a
escrita é negada e `report_saved` volta `false`.

## Passo 5: executar pela CLI (opcional)

Para que os comandos do próprio starter (`agent-app run`, `agent-app serve`, `agent-app eval`,
`agent-app doctor`) conheçam o agente, registre-o no **composition root**, `default_catalog()` em
`src/agent_app/app.py`. Esse é o ponto de extensão documentado, e é a única mudança fora do seu
pacote:

```python title="src/agent_app/app.py (default_catalog)"
def default_catalog() -> AgentCatalog:
    catalog = AgentCatalog(            # antes: return AgentCatalog(
        [
            ...                        # os agentes existentes, sem mudança
        ]
    )
    from my_agents.error_reporter import ERROR_REPORTER  # imported here: avoids a cycle

    catalog.register(ERROR_REPORTER)
    return catalog
```

O import fica **dentro** da função porque `my_agents.error_reporter` importa `agent_app.app`; no
topo do módulo, o ciclo de import falharia. `catalog()` continua funcionando: ele não registra o
agente duas vezes.

```bash
uv run agent-app agents list
uv run agent-app doctor
uv run agent-app run "Report the errors in the logs." --agent error_reporter --offline --approve auto
```

O `doctor` passa a verificar o prompt do novo agente
(`prompt:error-reporter-instructions ok v1.0`). Com `--approve ask` (o padrão), a CLI pergunta no
terminal antes de `save_report`. Com `--durable`, o run suspende e é decidido depois com
`agent-app approvals` e `agent-app runs resume`
([Aprovação humana e retomada](../architecture/hitl.md)).

## Passo 6: executar pela API HTTP

Na API, todo run é **durável**: o run suspende antes de `save_report` até que **outra pessoa**
aprove. Há dois caminhos:

- com o registro no composition root (passo 5), `uv run agent-app serve` já serve o agente;
- sem tocar no starter, sirva o seu catálogo com o mesmo `create_app` que o `serve` usa.

[Baixar `serve.py`](first-agent/src/my_agents/serve.py).

```python title="src/my_agents/serve.py"
--8<-- "src/my_agents/serve.py"
```

Crie duas chaves: uma para quem pede e outra para quem aprova. A separação de funções impede que o
solicitante aprove a própria operação.

```bash
uv run agent-app api new-key --tenant acme --principal ana@acme.example \
  -p runs:start -p runs:read -p workspace:read -p workspace:write
uv run agent-app api new-key --tenant acme --principal bruno@acme.example \
  -p approvals:decide -p runs:resume -p runs:read
```

Cada comando imprime a chave **uma vez** e a entrada JSON (apenas o hash) para o arquivo apontado
por `API_KEYS_FILE`. Depois:

```bash
uv run python -m my_agents.serve      # ou: uv run agent-app serve --offline (com o passo 5)
```

O ciclo completo, com `ANA` e `BRUNO` contendo as chaves:

```bash
curl -s -X POST localhost:8000/api/v1/runs -H "Authorization: Bearer $ANA" \
     -H "Content-Type: application/json" \
     -d '{"kind": "agent", "agent": "error_reporter", "input": "Report the errors in the logs."}'
# 202 {"run_id": "run_...", ...}

curl -s localhost:8000/api/v1/runs/<run_id> -H "Authorization: Bearer $ANA"
# "status": "waiting_approval", "pending_approvals": [{"approval_id": "apr_...", "operation": "save_report", ...}]

curl -s -X POST localhost:8000/api/v1/approvals/<approval_id>/approve -H "Authorization: Bearer $BRUNO"
curl -s -X POST localhost:8000/api/v1/runs/<run_id>/resume -H "Authorization: Bearer $BRUNO"
curl -s localhost:8000/api/v1/runs/<run_id> -H "Authorization: Bearer $ANA"
# "status": "completed", "result": {"error_count": 2, ..., "report_saved": true}
```

Para acompanhar em tempo real: `GET /api/v1/runs/<run_id>/events` (SSE). Veja a
[referência da API](../reference/http-api.md).

## Passo 7: testes

[Baixar `test_error_reporter.py`](first-agent/tests/my_agents/test_error_reporter.py).

```python title="tests/my_agents/test_error_reporter.py"
--8<-- "tests/my_agents/test_error_reporter.py"
```

```bash
uv run pytest tests/my_agents
```

Os testes rodam offline e cobrem:

1. o prompt está fixado na versão declarada;
2. o agente executa as ferramentas na ordem esperada e entrega o contrato;
3. **sem `workspace:write`**, a escrita é negada pela autorização, mesmo com aprovação;
4. **com a aprovação negada**, nada é escrito;
5. **pela API**, o run suspende antes da escrita, outra pessoa aprova, o run retoma e completa;
6. o framework de avaliação avalia o agente, inclusive num run durável.

O fixture `offline` isola cada teste: modelo roteirizado, `DATA_DIR` próprio, cópia do workspace e
tracing desligado. Os testes ficam em `tests/`, onde o `conftest.py` do starter acrescenta o mesmo
isolamento.

## Passo 8: avaliação

[Baixar `error-reporter.eval.json`](first-agent/tests/my_agents/error-reporter.eval.json).

```json title="tests/my_agents/error-reporter.eval.json"
--8<-- "tests/my_agents/error-reporter.eval.json"
```

- `reports-errors` verifica a **trajetória** (`search_text` antes de `save_report`, uma execução de
  cada) e campos da saída.
- `report-needs-a-human` roda como **execução durável**. Os passos `hitl` fazem o papel do operador
  (aprovar, retomar), e o caso verifica o status final e o número de aprovações pedidas.
- Cada caso roda numa **cópia** do workspace indicado; o diretório de exemplo não é alterado.

Com o registro no composition root (passo 5), o mesmo dataset roda pela CLI:

```bash
uv run agent-app eval run --dataset tests/my_agents/error-reporter.eval.json --offline --no-lock
```

`--no-lock` é para rascunhos. Para publicar uma versão do dataset (imutável, travada por hash),
coloque-o em `evals/datasets/` e use `agent-app eval lock`. Detalhes em
[Testes e avaliação](testing-and-evaluation.md).

## Checklist para o seu próprio agente

- [ ] Uma responsabilidade. Se a frase precisa de "e", talvez sejam dois passos de um workflow.
- [ ] Instruções versionadas, com `pinned_hash` atualizado a cada mudança de texto.
- [ ] Contrato de saída Pydantic sem defaults.
- [ ] Só as ferramentas necessárias (`registry.select(..., max_risk=...)`).
- [ ] Toda ferramenta própria passa por `invoke_tool`, declara capability e risco, e acima de
      `read_only` declara `HumanApproval`.
- [ ] Trabalho bloqueante em `operations.run_sync`.
- [ ] Modelo offline que deriva a resposta **só** dos resultados das ferramentas.
- [ ] Testes de sucesso, de negação por permissão e de rejeição humana.
- [ ] Casos de avaliação, incluindo cenários adversariais relevantes ao domínio.
- [ ] Nenhum modelo na definição do agente: ele vem da configuração (`MODEL_*`).
