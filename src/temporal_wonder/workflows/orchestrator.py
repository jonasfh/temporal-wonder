"""Master integration orchestrator workflow for Temporal Wonder."""

from __future__ import annotations

import asyncio
import re
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    import yaml

    from temporal_wonder.activities.legacy.logic_app import call_legacy_logic_app
    from temporal_wonder.activities.native.native_step import execute_native_step
    from temporal_wonder.models.manifest import Manifest, StepConfig, StepType


def _parse_duration(val: str | int | float | None) -> timedelta | None:
    """Parse duration value (int/float seconds or string like '60s', '2m') into timedelta."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return timedelta(seconds=float(val))

    s = str(val).strip().lower()
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(ms|s|m|h)?$", s)
    if not match:
        try:
            return timedelta(seconds=float(s))
        except ValueError:
            return None

    num = float(match.group(1))
    unit = match.group(2) or "s"

    if unit == "ms":
        return timedelta(milliseconds=num)
    if unit == "s":
        return timedelta(seconds=num)
    if unit == "m":
        return timedelta(minutes=num)
    if unit == "h":
        return timedelta(hours=num)
    return timedelta(seconds=num)


@workflow.defn
class IntegrationOrchestratorWorkflow:
    """Master orchestrator workflow executing an integration DAG manifest."""

    @workflow.run
    async def run(self, manifest_input: dict[str, Any] | str) -> dict[str, Any]:
        """Execute integration pipeline according to manifest DAG topology.

        Args:
            manifest_input: Serialized manifest dictionary or raw YAML/JSON string.

        Returns:
            Structured execution summary containing statuses of all steps.
        """
        start_time = workflow.now()

        # In-memory validation to ensure determinism
        if isinstance(manifest_input, str):
            raw_data = yaml.safe_load(manifest_input)
            manifest = Manifest.model_validate(raw_data)
        elif isinstance(manifest_input, dict):
            manifest = Manifest.model_validate(manifest_input)
        else:
            raise ValueError(f"Invalid manifest input type: {type(manifest_input)}")

        layers = manifest.get_execution_layers()
        all_step_results: dict[str, dict[str, Any]] = {}

        for layer_index, layer in enumerate(layers):
            workflow.logger.info(
                "Executing DAG layer %d/%d with %d step(s): %s",
                layer_index + 1,
                len(layers),
                len(layer),
                layer,
            )
            # Execute steps in current topological layer concurrently
            tasks = [self._execute_step(manifest.get_step_by_id(step_id)) for step_id in layer]
            results = await asyncio.gather(*tasks)

            for step_id, res in zip(layer, results, strict=True):
                all_step_results[step_id] = res

        end_time = workflow.now()
        duration_seconds = (end_time - start_time).total_seconds()

        workflow.logger.info(
            "Workflow for manifest '%s' completed successfully in %.2fs",
            manifest.identifier,
            duration_seconds,
        )

        return {
            "manifest_id": manifest.identifier,
            "version": manifest.version,
            "status": "COMPLETED",
            "total_steps": len(manifest.steps),
            "executed_layers": len(layers),
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": duration_seconds,
            "step_results": all_step_results,
        }

    async def _execute_step(self, step: StepConfig) -> dict[str, Any]:
        """Execute a single pipeline step via its registered activity."""
        # Determine timeouts
        start_to_close: timedelta | None = None
        if step.timeout and step.timeout.start_to_close_timeout:
            start_to_close = _parse_duration(step.timeout.start_to_close_timeout)
        if start_to_close is None:
            start_to_close = timedelta(seconds=120)

        schedule_to_close: timedelta | None = None
        if step.timeout and step.timeout.schedule_to_close_timeout:
            schedule_to_close = _parse_duration(step.timeout.schedule_to_close_timeout)

        # Determine retry policy
        retry_policy: RetryPolicy | None = None
        if step.retry_policy:
            initial = _parse_duration(step.retry_policy.initial_interval)
            maximum = _parse_duration(step.retry_policy.maximum_interval)
            retry_policy = RetryPolicy(
                initial_interval=initial if initial else timedelta(seconds=1),
                backoff_coefficient=step.retry_policy.backoff_coefficient,
                maximum_attempts=step.retry_policy.maximum_attempts,
                maximum_interval=maximum,
                non_retryable_error_types=step.retry_policy.non_retryable_error_types,
            )

        # Dispatch based on Strangler Fig step type
        if step.type == StepType.LEGACY_LOGIC_APP:
            result = await workflow.execute_activity(
                call_legacy_logic_app,
                args=[step.id, step.action, step.parameters],
                start_to_close_timeout=start_to_close,
                schedule_to_close_timeout=schedule_to_close,
                retry_policy=retry_policy,
            )
        else:
            result = await workflow.execute_activity(
                execute_native_step,
                args=[step.id, step.action, step.parameters],
                start_to_close_timeout=start_to_close,
                schedule_to_close_timeout=schedule_to_close,
                retry_policy=retry_policy,
            )

        return result
