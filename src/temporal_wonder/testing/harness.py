"""Test harness utilities for running Temporal workflows and workers in test environments."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any
from uuid import uuid4

from temporalio.client import Client
from temporalio.runtime import LoggingConfig, Runtime, TelemetryConfig, TelemetryFilter
from temporalio.worker import Worker

from temporal_wonder.activities.legacy.logic_app import call_legacy_logic_app
from temporal_wonder.activities.native.native_step import execute_native_step
from temporal_wonder.workflows.orchestrator import IntegrationOrchestratorWorkflow

DEFAULT_TEST_WORKFLOWS: list[type] = [IntegrationOrchestratorWorkflow]
DEFAULT_TEST_ACTIVITIES: list[Callable[..., Any]] = [
    call_legacy_logic_app,
    execute_native_step,
]


def get_test_runtime() -> Runtime:
    """Return a Temporal Runtime configured for test environments.

    Sets Rust SDK core log level to ERROR to suppress harmless capability
    warnings (e.g. activity_failure_include_heartbeat) when running against
    in-memory ephemeral test servers.
    """
    return Runtime(
        telemetry=TelemetryConfig(
            logging=LoggingConfig(filter=TelemetryFilter(core_level="ERROR", other_level="ERROR"))
        )
    )


def create_test_worker(
    client: Client,
    task_queue: str,
    workflows: Sequence[type] | None = None,
    activities: Sequence[Callable[..., Any]] | None = None,
) -> Worker:
    """Create a configured Temporal Worker instance suitable for test execution.

    Args:
        client: Temporal client connected to test environment.
        task_queue: Task queue name.
        workflows: Optional custom list of workflow definitions.
        activities: Optional custom list of activity functions.

    Returns:
        Worker instance ready to be used as context manager.
    """
    return Worker(
        client,
        task_queue=task_queue,
        workflows=workflows if workflows is not None else DEFAULT_TEST_WORKFLOWS,
        activities=activities if activities is not None else DEFAULT_TEST_ACTIVITIES,
    )


async def execute_manifest_workflow(
    client: Client,
    task_queue: str,
    manifest: dict[str, Any] | str,
    workflow_id: str | None = None,
) -> dict[str, Any]:
    """Execute IntegrationOrchestratorWorkflow in test client and return execution result.

    Args:
        client: Temporal client.
        task_queue: Task queue name where worker is listening.
        manifest: Manifest data dictionary or raw YAML/JSON string.
        workflow_id: Optional custom workflow ID.

    Returns:
        Result dictionary returned by workflow.
    """
    wf_id = workflow_id or f"test-workflow-{uuid4()}"
    raw_result = await client.execute_workflow(
        IntegrationOrchestratorWorkflow.run,
        manifest,
        id=wf_id,
        task_queue=task_queue,
    )
    assert isinstance(raw_result, dict)
    return raw_result
