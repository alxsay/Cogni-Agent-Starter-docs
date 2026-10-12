"""Tests of error_reporter, offline (no API key, no network, no paid calls).

uv run pytest tests/my_agents
"""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from agents import set_tracing_disabled
from fastapi.testclient import TestClient

from agent_app.api import ApiKeyEntry, ApiKeyRegistry, create_app, new_key
from agent_app.app import AppServices
from agent_app.config import Settings
from agent_app.contracts.budget import ExecutionBudget
from agent_app.contracts.evaluation import CaseStatus
from agent_app.evals.dataset import load_dataset
from agent_app.evals.runner import run_evaluation
from agent_app.security import StaticApprover
from my_agents.error_reporter import AGENT_ID, INSTRUCTIONS, REPORT_PATH, ErrorReport, catalog

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "incident_workspace"


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isolated settings: scripted model, own DATA_DIR, a scratch copy of the example workspace."""
    set_tracing_disabled(True)
    workspace = tmp_path / "ws"
    shutil.copytree(EXAMPLE, workspace)
    for name, value in {
        "MODEL_BACKEND": "scripted",
        "TRACING_EXPORT": "none",
        "DATA_DIR": str(tmp_path / "data"),
        "WORKSPACE_ROOT": str(workspace),
        "ALLOW_WRITES": "true",
        "IDENTITY_PERMISSIONS": "workspace:read,workspace:write",
        "LOG_LEVEL": "WARNING",
    }.items():
        monkeypatch.setenv(name, value)
    return workspace


def test_the_prompt_is_pinned() -> None:
    INSTRUCTIONS.verify()  # raises TemplateDrift if the text changed without a new version


async def test_it_reports_the_errors_and_saves_the_report(offline: Path) -> None:
    services = AppServices(Settings(), catalog=catalog())
    runtime = services.tool_runtime(
        security=services.local_security_context("run_test_ok"),
        approver=StaticApprover(approve=True),
        budget=ExecutionBudget(max_turns=6, max_tool_calls=4),
    )
    outcome = await services.run_agent(AGENT_ID, "Report the errors in the logs.", runtime)
    assert outcome.final_output == ErrorReport(
        error_count=2, files=["logs/processor.log"], report_saved=True
    )
    assert [(c.name, c.outcome) for c in runtime.invocations] == [
        ("search_text", "ok"),
        ("save_report", "ok"),
    ]
    assert (offline / REPORT_PATH).read_text(encoding="utf-8").startswith("# Errors")


async def test_without_write_permission_the_report_is_refused(offline: Path) -> None:
    services = AppServices(Settings(), catalog=catalog())
    security = services.local_security_context("run_test_ro").model_copy(
        update={"permissions": frozenset({"workspace:read"})}
    )
    runtime = services.tool_runtime(security=security, approver=StaticApprover(approve=True))
    outcome = await services.run_agent(AGENT_ID, "Report the errors in the logs.", runtime)
    assert [c.outcome for c in runtime.invocations] == ["ok", "denied"]
    assert outcome.final_output.report_saved is False
    assert not (offline / REPORT_PATH).exists()


async def test_a_human_rejection_means_no_report(offline: Path) -> None:
    services = AppServices(Settings(), catalog=catalog())
    runtime = services.tool_runtime(
        security=services.local_security_context("run_test_rejected"),
        approver=StaticApprover(approve=False),
    )
    outcome = await services.run_agent(AGENT_ID, "Report the errors in the logs.", runtime)
    assert outcome.final_output.report_saved is False
    assert not (offline / REPORT_PATH).exists()


@pytest.fixture
def api() -> Iterator[tuple[TestClient, dict[str, str], dict[str, str]]]:
    """The HTTP API serving this catalog; two people: one starts runs, the other approves."""
    requester_key, requester_hash = new_key()
    approver_key, approver_hash = new_key()
    keys = ApiKeyRegistry([
        ApiKeyEntry(key_id="ana", sha256=requester_hash, tenant_id="acme",
                    principal_id="ana@acme.test",
                    permissions=frozenset({"runs:start", "runs:read",
                                           "workspace:read", "workspace:write"})),
        ApiKeyEntry(key_id="bruno", sha256=approver_hash, tenant_id="acme",
                    principal_id="bruno@acme.test",
                    permissions=frozenset({"approvals:decide", "runs:resume", "runs:read"})),
    ])  # fmt: skip
    services = AppServices(Settings(), directory=keys, catalog=catalog())
    with TestClient(create_app(services, keys)) as client:
        yield (
            client,
            {"Authorization": f"Bearer {requester_key}"},
            {"Authorization": f"Bearer {approver_key}"},
        )


def _settled(client: TestClient, run_id: str, headers: dict[str, str]) -> dict[str, Any]:
    deadline = time.monotonic() + 30
    while True:
        run: dict[str, Any] = client.get(f"/api/v1/runs/{run_id}", headers=headers).json()
        if not run["executing"] and run["status"] not in {"running", "resuming"}:
            return run
        assert time.monotonic() < deadline, run
        time.sleep(0.05)


def test_through_the_api_the_report_waits_for_a_human(
    api: tuple[TestClient, dict[str, str], dict[str, str]], offline: Path
) -> None:
    client, ana, bruno = api
    created = client.post(
        "/api/v1/runs",
        headers=ana,
        json={"kind": "agent", "agent": AGENT_ID, "input": "Report the errors in the logs."},
    )
    assert created.status_code == 202, created.text
    run_id = created.json()["run_id"]

    run = _settled(client, run_id, ana)
    assert run["status"] == "waiting_approval"  # suspended before save_report, durably
    [pending] = run["pending_approvals"]
    assert pending["operation"] == "save_report"
    assert not (offline / REPORT_PATH).exists()

    approve = client.post(f"/api/v1/approvals/{pending['approval_id']}/approve", headers=bruno)
    assert approve.status_code == 200, approve.text
    assert client.post(f"/api/v1/runs/{run_id}/resume", headers=bruno).status_code == 202

    run = _settled(client, run_id, ana)
    assert run["status"] == "completed", run
    assert run["result"]["report_saved"] is True
    assert (offline / REPORT_PATH).exists()


async def test_the_eval_framework_evaluates_it(offline: Path) -> None:
    dataset = Path(__file__).with_name("error-reporter.eval.json")
    services = AppServices(Settings(), catalog=catalog())
    # Case workspaces are relative to the repository root; each case runs on a scratch copy.
    run = await run_evaluation(services, load_dataset(dataset), base_dir=REPO_ROOT)
    failures = {c.case_id: [k.name for k in c.checks if not k.passed] for c in run.report.cases}
    assert {c.case_id: c.status for c in run.report.cases} == {
        "reports-errors": CaseStatus.PASSED,
        "report-needs-a-human": CaseStatus.PASSED,
    }, failures
    assert json.loads(dataset.read_text(encoding="utf-8"))["version"] == "1.0"
