"""Integration tests verifying Temporal RetryPolicy and error handling with mock server."""

from __future__ import annotations

from typing import Any

import pytest
from temporalio.client import WorkflowFailureError
from temporalio.testing import WorkflowEnvironment

from temporal_wonder.testing.harness import create_test_worker, execute_manifest_workflow
from temporal_wonder.testing.mock_server import LogicAppMockServer


@pytest.mark.asyncio
async def test_transient_500_error_retry_success(
    logic_app_mock: LogicAppMockServer,
    temporal_env: WorkflowEnvironment,
) -> None:
    """Verify that transient 500 errors trigger Temporal retries and succeed upon recovery."""
    # Manifest with a single step that retries up to 3 times
    manifest: dict[str, Any] = {
        "identifier": "test-retry-manifest",
        "version": "1.0.0",
        "title": "Retry Test",
        "domain": "test",
        "steps": [
            {
                "id": "step_flaky_service",
                "name": "Flaky Service Step",
                "type": "legacy_logic_app",
                "action": "conf_flaky",
                "parameters": {"param1": "test"},
                "retryPolicy": {
                    "initialInterval": "1s",
                    "backoffCoefficient": 2.0,
                    "maximumAttempts": 3,
                },
                "timeout": {
                    "startToCloseTimeout": "30s",
                },
            }
        ],
    }

    # First two attempts fail with 500, third attempt succeeds with 200
    logic_app_mock.set_response_sequence(
        action="conf_flaky",
        responses=[
            (500, {"error": "Server error 1"}),
            (503, {"error": "Server error 2"}),
            (200, {"status": "recovered", "data": "success"}),
        ],
    )

    task_queue = "test-retry-queue"
    async with create_test_worker(temporal_env.client, task_queue=task_queue):
        result = await execute_manifest_workflow(
            temporal_env.client,
            task_queue=task_queue,
            manifest=manifest,
        )

        assert result["status"] == "COMPLETED"
        step_res = result["step_results"]["step_flaky_service"]
        assert step_res["status"] == "COMPLETED"
        assert step_res["output"]["statusCode"] == 200
        assert step_res["output"]["response"]["status"] == "recovered"

        # Verify that exactly 3 HTTP requests were made due to retries
        requests = logic_app_mock.get_requests_for_action("conf_flaky")
        assert len(requests) == 3


@pytest.mark.asyncio
async def test_permanent_error_exhausts_retries(
    logic_app_mock: LogicAppMockServer,
    temporal_env: WorkflowEnvironment,
) -> None:
    """Verify that persistent 500 errors exhaust maximum attempts and fail the workflow."""
    manifest: dict[str, Any] = {
        "identifier": "test-exhaust-manifest",
        "version": "1.0.0",
        "title": "Exhaust Retries Test",
        "domain": "test",
        "steps": [
            {
                "id": "step_always_fail",
                "name": "Always Failing Step",
                "type": "legacy_logic_app",
                "action": "conf_always_fail",
                "parameters": {},
                "retryPolicy": {
                    "initialInterval": "1s",
                    "backoffCoefficient": 1.0,
                    "maximumAttempts": 2,
                },
                "timeout": {
                    "startToCloseTimeout": "10s",
                },
            }
        ],
    }

    # All attempts return 500
    logic_app_mock.set_response(
        action="conf_always_fail",
        status_code=500,
        body={"error": "Permanent failure"},
    )

    task_queue = "test-exhaust-queue"
    async with create_test_worker(temporal_env.client, task_queue=task_queue):
        with pytest.raises(WorkflowFailureError):
            await execute_manifest_workflow(
                temporal_env.client,
                task_queue=task_queue,
                manifest=manifest,
            )

        # Verify that exactly maximumAttempts (2) requests were made
        requests = logic_app_mock.get_requests_for_action("conf_always_fail")
        assert len(requests) == 2
