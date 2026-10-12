# Próximos passos

Esta página lista o que o projeto registrou como **próximas decisões**. Nada aqui está implementado.

!!! info "Estado atual"
    A arquitetura atual está consolidada e validada em Windows e Linux. Os itens abaixo ampliam o
    escopo de uso: de laboratório e uso interno controlado para cenários com exigências maiores de
    isolamento, operação e escala.

## Leash: isolamento forte (proposta)

O **Leash** é a proposta de uma fronteira de execução aplicada **fora** do processo da aplicação:

- autoridade por operação imposta pelo ambiente, não só pela política lógica;
- rede negada por padrão para processos filhos;
- correspondência entre o perímetro registrado no manifesto e o perímetro efetivamente aplicado.

É o pré-requisito para executar código não confiável e para fechar as limitações descritas em
[Segurança e limitações](security.md#limitacoes): ausência de sandbox, escape por `setsid` no POSIX,
processos criados fora da árvore e rede livre para comandos.

## Operação

- **Retenção executável:** um comando de limpeza por idade (registros terminais, sessões,
  idempotência). Hoje a política existe, mas a limpeza é manual.
- **Auditoria para produção:** gravação assíncrona com rotação e, se exigido, encadeamento de hashes
  para evidência contra adulteração.
- **Métricas operacionais** e decisões de produto sobre aprovações, como condição para uso comercial.

## Runtime

- **Orçamento por agente no catálogo**, caso agentes com perfis de custo distintos passem a
  conviver. Hoje o orçamento é do run.
- **Store PostgreSQL** para checkpoints, idempotência e leases, implementando o mesmo protocolo do
  store SQLite. Só se houver demanda multi-host.
- **Execução durável completa** (retomada automática de runs em execução após queda do processo):
  a fronteira para um motor como Temporal está preparada, mas não embutida.
- **Exportador OpenTelemetry**: o ponto de extensão (`TracingProcessor` do SDK) existe; o exportador
  não.

## Como contribuir com uma decisão

Mudanças arquiteturais relevantes entram como um novo ADR em `docs/decisions/`, com testes que
demonstrem as garantias e atualização desta documentação.
