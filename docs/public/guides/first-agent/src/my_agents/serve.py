"""Serve the HTTP API with this catalog (the same app `agent-app serve` builds).

uv run python -m my_agents.serve
"""

from __future__ import annotations

import uvicorn

from agent_app.api import ApiKeyRegistry, create_app
from agent_app.app import AppServices
from agent_app.config import Settings
from agent_app.observability import configure_logging, configure_tracing
from my_agents.error_reporter import catalog


def main() -> None:
    settings = Settings()
    obs = settings.observability
    configure_logging(obs.log_level, obs.log_format,
                      include_sensitive_data=obs.trace_include_sensitive_data)  # fmt: skip
    configure_tracing(settings)
    keys = ApiKeyRegistry.load(settings.api.keys_file)  # API_KEYS_FILE
    app = create_app(AppServices(settings, directory=keys, catalog=catalog()), keys)
    # One worker on purpose: runs in flight, limits and event buffers live in this process.
    uvicorn.run(app, host=settings.api.host, port=settings.api.port, workers=1, log_config=None)


if __name__ == "__main__":
    main()
