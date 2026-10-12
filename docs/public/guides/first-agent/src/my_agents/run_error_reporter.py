"""Run error_reporter once, with the app's runtime (identity, budget, approvals, audit).

uv run python -m my_agents.run_error_reporter
"""

from __future__ import annotations

import asyncio

from agent_app.app import AppServices
from agent_app.config import Settings
from agent_app.contracts.budget import ExecutionBudget
from agent_app.observability import configure_logging, configure_tracing, new_run_id
from agent_app.security import StaticApprover
from my_agents.error_reporter import AGENT_ID, catalog


async def main() -> None:
    settings = Settings()
    obs = settings.observability
    # As the CLI does: logs and traces follow LOG_* / TRACING_EXPORT / TRACE_INCLUDE_SENSITIVE_DATA.
    configure_logging(obs.log_level, obs.log_format,
                      include_sensitive_data=obs.trace_include_sensitive_data)  # fmt: skip
    configure_tracing(settings)

    services = AppServices(settings, catalog=catalog())
    runtime = services.tool_runtime(
        security=services.local_security_context(new_run_id()),  # identity: IDENTITY_* settings
        approver=StaticApprover(approve=True),  # unattended run: approves save_report
        budget=ExecutionBudget(max_turns=6, max_tool_calls=4, max_duration_seconds=120),
    )
    outcome = await services.run_agent(AGENT_ID, "Report the errors in the logs.", runtime)
    print(outcome.final_output.model_dump_json(indent=2))
    for call in runtime.invocations:
        print(f"{call.name}: {call.outcome}")
    print(runtime.budget.report().model_dump_json(include={"turns", "tool_calls"}))


if __name__ == "__main__":
    asyncio.run(main())
