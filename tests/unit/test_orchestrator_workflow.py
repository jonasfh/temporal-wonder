"""Integration unit tests for IntegrationOrchestratorWorkflow."""

from pathlib import Path
from typing import Any

import pytest
import yaml
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from temporal_wonder.activities.legacy.logic_app import call_legacy_logic_app
from temporal_wonder.activities.native.native_step import execute_native_step
from temporal_wonder.testing.mock_server import LogicAppMockServer
from temporal_wonder.workflows.orchestrator import IntegrationOrchestratorWorkflow


@pytest.mark.asyncio
async def test_orchestrator_workflow_full_execution(
    logic_app_mock: LogicAppMockServer,
    temporal_env: WorkflowEnvironment,
) -> None:
    """Test full DAG execution with legacy/native steps using WorkflowEnvironment and Mock."""
    manifest_path = Path("examples/sample-manifest.yaml")
    assert manifest_path.is_file()

    manifest_dict: dict[str, Any] = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    task_queue = "test-integration-queue"
    async with Worker(
        temporal_env.client,
        task_queue=task_queue,
        workflows=[IntegrationOrchestratorWorkflow],
        activities=[
            call_legacy_logic_app,
            execute_native_step,
        ],
    ):
        result = await temporal_env.client.execute_workflow(
            IntegrationOrchestratorWorkflow.run,
            manifest_dict,
            id="test-execution-krt0000a",
            task_queue=task_queue,
        )

        assert result["status"] == "COMPLETED"
        assert result["manifest_id"] == "krt-0000a-1-modernized"
        assert result["total_steps"] == 5
        assert result["executed_layers"] == 4
        assert len(result["step_results"]) == 5

        # Verify individual step executions
        step_teams = result["step_results"]["step_teams_notification"]
        assert step_teams["type"] == "legacy_logic_app"
        assert step_teams["status"] == "COMPLETED"
        assert step_teams["output"]["statusCode"] == 200

        step_altinn = result["step_results"]["step_fetch_altinn_data"]
        assert step_altinn["type"] == "native"
        assert step_altinn["status"] == "COMPLETED"

        step_xml = result["step_results"]["step_process_xml"]
        assert step_xml["type"] == "native"
        assert step_xml["status"] == "COMPLETED"

        step_archive = result["step_results"]["step_archive_websak"]
        assert step_archive["type"] == "legacy_logic_app"
        assert step_archive["status"] == "COMPLETED"
        assert step_archive["output"]["statusCode"] == 200

        step_receipt = result["step_results"]["step_send_receipt"]
        assert step_receipt["type"] == "native"
        assert step_receipt["status"] == "COMPLETED"

        # Verify that mock server received the HTTP calls for the legacy steps
        teams_requests = logic_app_mock.get_requests_for_action("conf_teamspost")
        assert len(teams_requests) == 1
        assert teams_requests[0].method == "POST"

        archive_requests = logic_app_mock.get_requests_for_action("conf_dist_websak")
        assert len(archive_requests) == 1
        assert archive_requests[0].method == "POST"
