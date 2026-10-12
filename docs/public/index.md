# Cogni Agent Starter

O **Cogni Agent Starter** é uma base de código em Python para construir **agentes de software**:
programas em que um modelo de linguagem decide quais ferramentas usar, enquanto o código da
aplicação decide o que pode ser executado, por quem, com qual orçamento e com qual registro.

Não é um agente específico nem um framework genérico. É a infraestrutura operacional que se
repete em toda aplicação com agentes, pronta, testada e documentada, para que cada novo agente
seja só a parte de domínio: instruções, ferramentas, contrato de saída e testes.

> **Princípio de projeto:** *deterministic shell around probabilistic intelligence.*
> O software controla processo, permissões, contratos e efeitos. O modelo é usado onde há
> incerteza real. Autonomia é **alocada**, não maximizada.

## Para quem é

- Engenheiros que vão construir agentes internos (investigação, triagem, pesquisa, automação de
  rotinas) e precisam que eles rodem com identidade, limites e auditoria desde o primeiro dia.
- Times que querem um ponto de partida revisável, em vez de montar a mesma infraestrutura em cada
  projeto.
- Quem precisa avaliar o comportamento de agentes de forma reprodutível, inclusive em cenários
  adversariais, antes de expô-los a dados ou sistemas reais.

## Por que um starter, e não começar do zero

Fazer um modelo chamar ferramentas é a parte fácil. O trabalho está no que vem em volta. Cada
pergunta abaixo já tem uma resposta implementada e testada no starter:

| Pergunta de engenharia | Resposta no starter |
|---|---|
| Quem pediu esta execução e o que essa identidade pode fazer? | `SecurityContext` imutável por run; permissões verificadas antes de cada operação |
| O modelo pediu para ler um arquivo sensível. Quem decide? | O código: fronteira de ferramentas com política de caminho, argumentos e risco |
| Esta operação muda algo. Uma pessoa precisa aprovar? | Política por nível de risco; aprovação pode **suspender o run de forma durável** e retomá-lo em outro processo |
| Quanto esta execução pode consumir? | Orçamento por run: turnos, tokens, custo estimado, duração e chamadas de ferramenta |
| O provedor falhou. Repetimos? | Só a chamada ao modelo, com backoff e fallback; nunca o run, nunca uma ferramenta |
| Alguém cancelou. O efeito parou? | Ledger de operações distingue pedido, parada, liberação de recursos e efeito; nunca transforma "não sei" em "parou" |
| O que exatamente rodou neste run? | Manifesto de execução imutável: versões e hashes de instruções, ferramentas, contratos, modelo, configuração e build |
| O agente piorou depois de uma mudança? | Datasets versionados, avaliação offline determinística, baselines e gates de regressão |

## O que está implementado

- **Runtime de agentes** sobre o [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/),
  com saída estruturada (Pydantic), instruções versionadas e um **catálogo de agentes**: registrar um
  agente o torna disponível para CLI, API, execuções duráveis e avaliações.
- **Ferramentas com fronteira única** (`invoke_tool`): orçamento → autorização → política de
  argumentos → aprovação → execução registrada → saída marcada como não confiável.
- **Workspace isolado logicamente** para as ferramentas de arquivo, com política de caminhos
  portável entre Windows e Linux.
- **Execução de comandos por allowlist**, com timeout, limite de saída, ambiente sanitizado e
  controle da árvore de processos (Job Objects no Windows; grupo de processos no POSIX).
- **MCP** (Model Context Protocol): cliente e servidor, sob a mesma política das ferramentas locais.
- **Web Search e Web Fetch** opcionais, com política anti-SSRF e conexão no endereço validado.
- **Human-in-the-loop durável**: suspensão antes de operações sensíveis, decisão por outra pessoa,
  retomada do mesmo run sem repetir o que já foi feito.
- **API HTTP** (FastAPI) com chaves de API, eventos de ciclo de vida via SSE e idempotência.
- **Workflows** com estado (LangGraph) que combinam passos determinísticos e agentes.
- **Observabilidade** sem captura de conteúdo sensível por padrão: logs estruturados, tracing do
  SDK, trilha de auditoria e log de runs.
- **Avaliação**: datasets adversariais versionados, modelo offline determinístico, baselines,
  gates, revisão humana e juiz LLM opcional (apenas consultivo).

## O que ele não pretende resolver

!!! warning "Limites deliberados"
    - **Não é um sandbox.** O executor local roda comandos com a autoridade do usuário do sistema
      operacional. O executor Docker reduz o impacto, mas não é um isolamento completo. Isolamento
      forte é trabalho futuro (veja [Próximos passos](roadmap.md)).
    - **Não é uma plataforma distribuída.** Estado durável em SQLite, um host, um worker por
      processo de API. Veja [Operação e implantação](operations.md).
    - **Não mede a inteligência do modelo offline.** O modelo offline valida a arquitetura; a
      qualidade de um agente só se mede com modelo real.
    - **Não garante exactly-once** para efeitos externos. Efeitos incertos são reportados como
      tais (`ambiguous`), nunca escondidos.

## Por onde começar

<div class="grid cards" markdown>

- **[Primeiros passos](getting-started.md)**: instale, rode o diagnóstico, o demo, os testes e as
  avaliações, sem chave de API.
- **[Arquitetura](architecture/index.md)**: componentes, ciclo de vida de uma execução e
  aprovação humana durável.
- **[Construindo seu primeiro agente](guides/first-agent.md)**: um agente completo, testado, com
  ferramenta própria, aprovação humana, API e avaliação.
- **[Segurança e limitações](security.md)**: o que é garantido, como, e o que não é.

</div>

## Estado do projeto

Versão do pacote `0.1.0`. A arquitetura passou por uma auditoria independente e por uma
consolidação, e foi validada em **Windows e Linux** (Python 3.12): suíte completa de testes,
verificação estática estrita, demos e avaliações offline contra baselines. As limitações conhecidas
estão documentadas em [Segurança e limitações](security.md#limitacoes) e em
[Operação e implantação](operations.md).
