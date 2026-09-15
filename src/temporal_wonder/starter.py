"""Starter script to submit and trigger integration workflows in Temporal."""

import argparse
import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any, NoReturn

from temporalio.client import Client

from temporal_wonder.config import Settings, get_settings
from temporal_wonder.models.manifest import load_manifest
from temporal_wonder.workflows.orchestrator import IntegrationOrchestratorWorkflow

logger = logging.getLogger("temporal_wonder.starter")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for workflow starter."""
    parser = argparse.ArgumentParser(
        description="Trigger an integration DAG workflow execution in Temporal.",
    )
    parser.add_argument(
        "--manifest",
        "-m",
        type=str,
        default="examples/sample-manifest.yaml",
        help="Path to the manifest file (YAML or JSON). Defaults to examples/sample-manifest.yaml.",
    )
    parser.add_argument(
        "--workflow-id",
        type=str,
        default=None,
        help="Custom workflow ID. If omitted, a unique ID is automatically generated.",
    )
    parser.add_argument(
        "--task-queue",
        type=str,
        default=None,
        help="Target task queue. Defaults to TEMPORAL_TASK_QUEUE from settings.",
    )
    return parser.parse_args()


async def trigger_workflow(
    manifest_path: str | Path,
    workflow_id: str | None = None,
    task_queue: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Load manifest and submit workflow execution to Temporal server.

    Args:
        manifest_path: Path to YAML or JSON manifest.
        workflow_id: Optional custom workflow ID.
        task_queue: Optional custom task queue name.
        settings: Optional custom application settings.

    Returns:
        Workflow execution result dictionary.
    """
    cfg = settings or get_settings()

    path = Path(manifest_path)
    if not path.is_file():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

    # Load and validate manifest
    manifest = load_manifest(path)
    target_workflow_id = workflow_id or f"wf-{manifest.identifier}-{uuid.uuid4().hex[:8]}"
    target_task_queue = task_queue or cfg.temporal_task_queue

    logger.info("Connecting to Temporal at %s...", cfg.temporal_host_url)
    client = await Client.connect(
        target_host=cfg.temporal_host_url,
        namespace=cfg.temporal_namespace,
    )

    logger.info(
        "Submitting workflow '%s' (Manifest: %s)...", target_workflow_id, manifest.identifier
    )
    ui_url = (
        f"http://localhost:8233/namespaces/{cfg.temporal_namespace}/workflows/{target_workflow_id}"
    )
    logger.info("Temporal Web UI: %s", ui_url)

    # Pass the serialized manifest dictionary to the workflow
    manifest_dict = manifest.model_dump(by_alias=True)

    handle = await client.start_workflow(
        IntegrationOrchestratorWorkflow.run,
        manifest_dict,
        id=target_workflow_id,
        task_queue=target_task_queue,
    )

    logger.info("Workflow started with Run ID: %s", handle.result_run_id)
    logger.info("Waiting for execution to complete...")

    result = await handle.result()
    return result


def main() -> NoReturn:
    """Entry point for python -m temporal_wonder.starter."""
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        result = asyncio.run(
            trigger_workflow(
                manifest_path=args.manifest,
                workflow_id=args.workflow_id,
                task_queue=args.task_queue,
            )
        )
        print("\n=== Workflow Execution Succeeded ===")
        print(json.dumps(result, indent=2))
        sys.exit(0)
    except Exception as err:
        logger.error("Workflow submission failed: %s", err)
        sys.exit(1)


if __name__ == "__main__":
    main()
