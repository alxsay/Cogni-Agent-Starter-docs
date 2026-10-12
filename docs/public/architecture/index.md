# Arquitetura

Três páginas, do estático ao dinâmico:

1. **[Componentes](overview.md)**: quais são as peças, o que cada uma decide e como se conectam.
2. **[Ciclo de vida de uma execução](execution-lifecycle.md)**: o caminho de uma solicitação até um
   estado terminal, passando por modelo, ferramentas, autorização, orçamento e auditoria.
3. **[Aprovação humana e retomada](hitl.md)**: como um run suspende antes de uma operação sensível,
   espera uma decisão e continua sem repetir o que já fez.

## Distinções que a arquitetura torna explícitas

A maior parte das decisões de projeto se resume a não confundir conceitos parecidos:

| Distinção | Por que importa |
|---|---|
| **Agent ≠ Runner ≠ Run ≠ Agent loop** | definição estática ≠ executor ≠ uma execução ≠ o algoritmo (que é do SDK; o starter nunca reimplementa o loop) |
| **Autoridade do modelo ≠ autoridade de execução** | o modelo *pede*; o código *decide* e *executa* |
| **Tool calling ≠ MCP** | chamada local ≠ protocolo entre processos, mas ambos sob a mesma política |
| **Versão declarada ≠ conteúdo** | cada artefato tem versão humana **e** hash do conteúdo real |
| **Suspensão ≠ erro ≠ cancelamento** | esperar uma pessoa é um estado durável, não uma falha |
| **Retry do modelo ≠ retry do run** | só a chamada ao modelo é repetida; nunca o run, nunca uma ferramenta |
| **Pedir parada ≠ parar ≠ liberar ≠ saber o efeito** | cancelamento é reportado com honestidade, inclusive quando o efeito é desconhecido |
| **HTTP ≠ segundo runtime** | a API é um adaptador sobre o mesmo runtime durável da CLI |
| **Web Search ≠ Web Fetch ≠ navegador** | busca devolve pistas; fetch lê uma URL sob política de rede; não há navegador |

## Pilha tecnológica

| Camada | Tecnologia | Papel |
|---|---|---|
| Runtime de agente | OpenAI Agents SDK 0.23 | `Agent`, `Runner`, loop, tool calling, guardrails, sessions, tracing |
| Workflows | LangGraph | macro-processo com estado, nós determinísticos e de agente |
| Contratos | Pydantic 2 | entradas, saídas, eventos, manifesto, relatórios, sem I/O |
| Configuração | pydantic-settings | `.env` e variáveis de ambiente, por classe de configuração |
| CLI | Typer + Rich | `agent-app` |
| API | FastAPI + Uvicorn | adaptador HTTP e SSE |
| MCP | SDK oficial `mcp` | servidor e cliente |
| Persistência | SQLite (padrão), PostgreSQL (memória, opcional) | checkpoints, idempotência, sessões, memória |
| Observabilidade | structlog, tracing do SDK | logs, spans, auditoria |
| Qualidade | pytest, Ruff, Pyright (strict) | testes e verificação estática |

## Onde está o acoplamento

| Dependência | Grau | Contenção |
|---|---|---|
| OpenAI Agents SDK | médio | só `agents/` e `tools/sdk.py` usam a API de `Agent`/`Runner`/`function_tool` |
| LangGraph | baixo a médio | só os `graph.py` dos workflows; nós e roteadores são funções sobre Pydantic |
| OpenAI como provedor | baixo | `agents/models.py`; LiteLLM ou `OPENAI_BASE_URL` para outros |
| SDK MCP | baixo | servidor isolado em `mcp/server.py` |
| PostgreSQL | baixo | atrás do protocolo `MemoryStore` |
