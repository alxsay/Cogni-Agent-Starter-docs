# Primeiros passos

Este guia leva do clone a um agente rodando, testes e avaliações. Tudo funciona **sem chave de
API**: o starter traz um modelo offline determinístico que roda *por dentro* do `Runner` real do
OpenAI Agents SDK.

## Pré-requisitos

| Requisito | Observação |
|---|---|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | gerenciador de projeto e ambiente; instala o Python 3.12 se necessário |
| Python 3.12+ | declarado em `pyproject.toml` (`requires-python = ">=3.12"`) |
| Git | para clonar |
| Docker (opcional) | só para o executor Docker e para a imagem do projeto |

Sistemas validados: **Windows 10** e **Linux (Debian 12)**. macOS segue o caminho POSIX, mas não
faz parte da validação registrada.

## 1. Obter o código

```bash
git clone <url-do-repositório> agent-app-starter
cd agent-app-starter
```

!!! note "Acesso ao repositório"
    O endereço do repositório é fornecido pelo mantenedor. Esta documentação não pressupõe que o
    código-fonte seja público.

## 2. Instalar as dependências

As versões vêm do `uv.lock`; a instalação é reprodutível.

```bash
uv sync
```

Extras opcionais:

| Extra | Para quê | Comando |
|---|---|---|
| `litellm` | provedores não-OpenAI (Anthropic, Gemini, modelos locais) via LiteLLM | `uv sync --extra litellm` |
| `postgres` | store de memória em PostgreSQL | `uv sync --extra postgres` |
| `otel` | bibliotecas OpenTelemetry, para quem implementar um exportador de spans (não há exportador embutido) | `uv sync --extra otel` |

Também há scripts que fazem tudo de uma vez (verificam Python e uv, instalam, criam `.env` e
diretórios, rodam verificações):

=== "Linux / macOS"

    ```bash
    ./scripts/bootstrap.sh
    ```

=== "Windows (PowerShell)"

    ```powershell
    powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
    ```

## 3. Configurar o ambiente

```bash
cp .env.example .env
```

O `.env.example` documenta cada variável, agrupada pela classe de configuração que a lê. Para
começar, nada precisa ser alterado: os comandos com `--offline` não chamam nenhum modelo pago.

!!! danger "Segredos"
    O `.env` é ignorado pelo Git e nunca deve ser versionado. Para usar um modelo real, defina
    `OPENAI_API_KEY` (ou a chave do seu provedor) **apenas** no `.env` ou no ambiente.

As variáveis mais relevantes estão em [Configuração](reference/configuration.md).

## 4. Diagnóstico

```bash
uv run agent-app doctor
```

Verifica Python, dependências, configuração, workspace, modelo, servidores MCP e a integridade das
instruções versionadas de cada agente do catálogo (o hash do texto precisa bater com o
`pinned_hash` declarado).

!!! tip "Se o executável `agent-app` não for encontrado"
    `uv run python -m agent_app <comando>` é equivalente a `uv run agent-app <comando>`.

## 5. Rodar o demo

```bash
uv run agent-app run-demo
```

O demo executa o workflow de investigação de incidente de ponta a ponta numa cópia descartável de
`examples/incident_workspace`:

```text
load_incident -> investigate -> classify -> act -> verify -> record_outcome
                     |
                     +-> Agents SDK Runner -> loop do agente -> ferramentas (search/read/run_check)
                         -> InvestigationResult (Pydantic, JSON schema estrito)
```

Com um modelo real configurado no `.env`: `uv run agent-app run-demo --live`.

## 6. Rodar um agente diretamente

Os agentes do catálogo:

```bash
uv run agent-app agents list
```

| Agente | O que faz |
|---|---|
| `incident_investigator` | encontra a causa mais provável de uma falha no workspace |
| `web_researcher` | responde a uma pergunta a partir de fontes web públicas (opcional, ver [segurança](security.md#conteudo-web)) |

Rodar o investigador sobre o workspace de exemplo, offline:

=== "Linux / macOS"

    ```bash
    WORKSPACE_ROOT=examples/incident_workspace \
      uv run agent-app run "Investigue por que data/inbound/orders_2026-10-05.csv falhou" --offline
    ```

=== "Windows (PowerShell)"

    ```powershell
    $env:WORKSPACE_ROOT = "examples/incident_workspace"
    uv run agent-app run "Investigue por que data/inbound/orders_2026-10-05.csv falhou" --offline
    ```

`WORKSPACE_ROOT` é o único diretório que as ferramentas podem tocar. A opção `--approve` define quem
decide sobre operações que exigem aprovação: `ask` (pergunta no terminal, padrão), `auto` ou `deny`.
Com `--durable`, o run **suspende** antes dessas operações e é retomado depois
([Aprovação humana e retomada](architecture/hitl.md)).

## 7. Testes e verificações estáticas

```bash
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
uv run pyright
```

Os testes não fazem chamadas pagas nem acessam a rede: o modelo é o offline e as ferramentas web
usam uma internet sintética.

## 8. Avaliações offline

```bash
uv run agent-app eval --offline
uv run agent-app eval run --dataset agent-core --offline --baseline evals/baselines/agent-core.offline.json
uv run agent-app eval run --dataset agent-safety --offline --baseline evals/baselines/agent-safety.offline.json
uv run agent-app eval run --dataset web-safety --offline --baseline evals/baselines/web-safety.offline.json
uv run agent-app eval run --dataset agent-lifecycle --offline --baseline evals/baselines/agent-lifecycle.offline.json
```

Cada `eval run` termina com `gate decision: APPROVED` (exit 0) ou `REJECTED` (exit 1). O que cada
dataset cobre e como ler o relatório está em [Testes e avaliação](guides/testing-and-evaluation.md).

## 9. Concorrência e cancelamento

```bash
uv run agent-app lifecycle-demo
```

Demonstra, offline, limites de concorrência, cancelamento e limpeza de recursos. Sai com código 1
se alguma das afirmações verificadas falhar.

## Próximo passo

[Construa seu primeiro agente](guides/first-agent.md), ou entenda antes a
[arquitetura](architecture/index.md).
