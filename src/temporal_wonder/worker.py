"""Temporal worker running integration workflows and activities."""

import asyncio
import logging
import signal
import sys
from typing import NoReturn

from temporalio.client import Client
from temporalio.worker import Worker

from temporal_wonder.activities.legacy.logic_app import call_legacy_logic_app
from temporal_wonder.activities.native.native_step import execute_native_step
from temporal_wonder.config import Settings, get_settings
from temporal_wonder.workflows.orchestrator import IntegrationOrchestratorWorkflow

logger = logging.getLogger("temporal_wonder.worker")


async def run_worker(settings: Settings | None = None) -> None:
    """Initialize and run the Temporal worker process."""
    cfg = settings or get_settings()

    logging.basicConfig(
        level=getattr(logging, cfg.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info(
        "Connecting to Temporal server at %s (namespace: %s)...",
        cfg.temporal_host_url,
        cfg.temporal_namespace,
    )
    try:
        client = await Client.connect(
            target_host=cfg.temporal_host_url,
            namespace=cfg.temporal_namespace,
        )
    except Exception as err:
        logger.error(
            "Failed to connect to Temporal server at %s. "
            "Ensure 'docker compose up -d' is running. Error: %s",
            cfg.temporal_host_url,
            err,
        )
        sys.exit(1)

    logger.info("Connected successfully to Temporal server.")
    logger.info("Starting worker on task queue: '%s'", cfg.temporal_task_queue)

    worker = Worker(
        client,
        task_queue=cfg.temporal_task_queue,
        workflows=[IntegrationOrchestratorWorkflow],
        activities=[
            call_legacy_logic_app,
            execute_native_step,
        ],
    )

    stop_event = asyncio.Event()

    def handle_signal(sig_name: str) -> None:
        logger.info("Received %s, shutting down worker gracefully...", sig_name)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal, sig.name)
        except (NotImplementedError, RuntimeError):
            # Fallback for environments without full signal handler support
            pass

    logger.info("Worker is running and polling for tasks. Press Ctrl+C to stop.")
    worker_task = asyncio.create_task(worker.run())
    stop_waiter = asyncio.create_task(stop_event.wait())

    _done, pending = await asyncio.wait(
        [worker_task, stop_waiter],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    logger.info("Worker shutdown complete.")


def main() -> NoReturn:
    """Entry point for python -m temporal_wonder.worker."""
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
