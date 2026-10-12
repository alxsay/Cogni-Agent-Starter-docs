# Decisões de arquitetura

As decisões do projeto são registradas como ADRs (*Architecture Decision Records*) no repositório, em
`docs/decisions/`. Esta página resume cada uma em uma linha. Todas estão com status **aceito**.

| ADR | Decisão | Em uma linha |
|---|---|---|
| 0001 | Runtime de agente: OpenAI Agents SDK | o loop, tool calling, guardrails e tracing são do SDK; o starter nunca implementa um loop próprio |
| 0002 | Workflows com LangGraph | o macro-processo com estado fica num grafo; nós e roteadores são funções sobre Pydantic |
| 0003 | Contratos estruturados com Pydantic | entradas, saídas, eventos e relatórios são modelos tipados, sem I/O |
| 0004 | Modelo de segurança de ferramentas | o modelo pede, o código decide; workspace, allowlist de comandos e aprovação por risco. Adendo: política de caminhos portável entre Windows e Linux |
| 0005 | Context, State, Session e Memory separados | quatro ciclos de vida distintos, quatro mecanismos distintos |
| 0006 | Fronteira para execução durável | preparar a fronteira para um motor como Temporal, sem embuti-lo |
| 0007 | Ferramental e modelo offline | uv, Ruff, Pyright estrito, pytest; modelo roteirizado dentro do `Runner` real para testes e CI |
| 0008 | Integração MCP | cliente do SDK, servidor com o SDK oficial, configuração declarativa com allowlist |
| 0009 | Histórico de sessão sob política da aplicação | a sessão é do SDK; o que volta ao modelo é decidido pela aplicação |
| 0010 | Observabilidade sem conteúdo sensível por padrão | tracing e captura de conteúdo são decisões separadas |
| 0011 | Quatro fronteiras de guardrail | entrada, argumentos, saída de ferramenta e saída final; MCP sob a mesma política das ferramentas locais |
| 0012 | Identidade, tenant e autorização | `SecurityContext` imutável por run; autorização determinística antes de qualquer efeito |
| 0013 | Orçamentos de execução | limites por run definidos por código confiável; custo desconhecido não é zero |
| 0014 | Resiliência das chamadas ao modelo | retry, backoff, timeout e fallback só para a chamada ao modelo, sob o mesmo orçamento |
| 0015 | Versionamento e manifesto de execução | versão declarada e hash do conteúdo de cada artefato; manifesto imutável por run |
| 0016 | Human-in-the-loop durável e checkpoints | suspensão sobre o `RunState` nativo do SDK; um run retomado é o mesmo run |
| 0017 | API HTTP e streaming | adaptador FastAPI sobre os runs duráveis; SSE de eventos de ciclo de vida, nunca de conteúdo |
| 0018 | Avaliação, datasets adversariais e feedback humano | datasets versionados, gates, relatórios sem conteúdo, revisão humana; juiz LLM só consultivo |
| 0019 | Web Search e Web Fetch | capacidades opt-in sob política de rede, com conexão no endereço validado |
| 0020 | Concorrência, cancelamento e limpeza | pedir parada ≠ parar ≠ liberar ≠ saber o efeito; estados honestos (`unsettled`, `ambiguous`) |
| 0021 | Consolidação arquitetural | uma regra de fim de run, ledger para MCP e workflows, perímetro no manifesto, separação de funções, lease, catálogo de agentes |
| 0022 | Árvore de processos no Windows com Job Objects | o comando é contido desde a criação; o encerramento é confirmado pela contagem do sistema operacional |
