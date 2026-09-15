"""Native activities executing direct integrations (Altinn 3, transformations, storage)."""

import logging
from typing import Any

from temporalio import activity

logger = logging.getLogger(__name__)


@activity.defn
async def execute_native_step(
    step_id: str,
    action: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Execute a modernized native activity.

    Args:
        step_id: Unique step identifier from the integration manifest.
        action: Target native method or handler identifier.
        parameters: Step arguments and configuration.

    Returns:
        Execution result dictionary including status and output data.
    """
    logger.info(
        "Executing native activity step '%s' (action: %s) with %d parameters",
        step_id,
        action,
        len(parameters),
    )
    # Simulated execution for local dev and testing
    return {
        "step_id": step_id,
        "action": action,
        "status": "COMPLETED",
        "type": "native",
        "message": f"Native action '{action}' executed successfully",
        "output": {
            "processed": True,
            "simulated": True,
            "parameters": parameters,
        },
    }
