"""End-to-end integration test executing full manifest workflow without external calls."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from temporalio.testing import WorkflowEnvironment

from temporal_wonder.testing.harness import create_test_worker, execute_manifest_workflow
from temporal_wonder.testing.mock_server import LogicAppMockServer


@pytest.mark.asyncio
async def test_full_manifest_execution_end_to_end(
    logic_app_mock: LogicAppMockServer,
    temporal_env: WorkflowEnvironment,
) -> None:
    """Execute sample-manifest.yaml from start to finish verifying both legacy and native steps.

    Verifies:
    - Workflow runs through all DAG layers deterministically.
    - Legacy steps send HTTP POST to the local LogicAppMockServer.
    - Native steps execute locally.
    - Zero external network requests are made.
    """
    manifest_path = Path("examples/sample-manifest.yaml")
    manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    # Configure custom responses for the two legacy steps in sample-manifest
    logic_app_mock.set_response(
        action="conf_teamspost",
        status_code=200,
        body={"status": "delivered", "messageId": "msg-12345"},
    )
    logic_app_mock.set_response(
        action="conf_dist_websak",
        status_code=200,
        body={"archiveId": "WS-98765", "registered": True},
    )

    task_queue = "test-e2e-manifest-queue"
    async with create_test_worker(temporal_env.client, task_queue=task_queue):
        result = await execute_manifest_workflow(
            temporal_env.client,
            task_queue=task_queue,
            manifest=manifest_data,
            workflow_id="test-e2e-krt-0000a",
        )

        assert result["status"] == "COMPLETED"
        assert result["manifest_id"] == "krt-0000a-1-modernized"
        assert result["total_steps"] == 5
        assert result["executed_layers"] == 4
        assert result["duration_seconds"] >= 0

        step_results = result["step_results"]
        assert len(step_results) == 5

        # Check legacy steps output
        teams_step = step_results["step_teams_notification"]
        assert teams_step["status"] == "COMPLETED"
        assert teams_step["type"] == "legacy_logic_app"
        assert teams_step["output"]["statusCode"] == 200
        assert teams_step["output"]["response"]["messageId"] == "msg-12345"

        websak_step = step_results["step_archive_websak"]
        assert websak_step["status"] == "COMPLETED"
        assert websak_step["type"] == "legacy_logic_app"
        assert websak_step["output"]["statusCode"] == 200
        assert websak_step["output"]["response"]["archiveId"] == "WS-98765"

        # Check native steps
        assert step_results["step_fetch_altinn_data"]["type"] == "native"
        assert step_results["step_process_xml"]["type"] == "native"
        assert step_results["step_send_receipt"]["type"] == "native"

        # Verify Mock Server received precisely the two HTTP requests
        recorded = logic_app_mock.recorded_requests
        assert len(recorded) == 2

        teams_req = logic_app_mock.get_requests_for_action("conf_teamspost")
        assert len(teams_req) == 1
        assert isinstance(teams_req[0].body, dict)
        assert (
            teams_req[0].body["parameters"]["uri_keyvault_secret"]
            == "int_teams_notification_krt1801"
        )

        websak_req = logic_app_mock.get_requests_for_action("conf_dist_websak")
        assert len(websak_req) == 1
        assert isinstance(websak_req[0].body, dict)
        assert websak_req[0].body["parameters"]["journal_enhet"] == 511.6


@pytest.mark.asyncio
async def test_manifest_execution_from_yaml_string(
    logic_app_mock: LogicAppMockServer,
    temporal_env: WorkflowEnvironment,
) -> None:
    """Verify orchestrator workflow accepts raw YAML string as input."""
    manifest_yaml = Path("examples/sample-manifest.yaml").read_text(encoding="utf-8")

    task_queue = "test-yaml-string-queue"
    async with create_test_worker(temporal_env.client, task_queue=task_queue):
        result = await execute_manifest_workflow(
            temporal_env.client,
            task_queue=task_queue,
            manifest=manifest_yaml,
        )

        assert result["status"] == "COMPLETED"
        assert result["manifest_id"] == "krt-0000a-1-modernized"
        assert len(result["step_results"]) == 5
