"""Legacy activities delegating work to external Azure Logic Apps via HTTP."""

import logging
from typing import Any

from temporalio import activity

logger = logging.getLogger(__name__)


@activity.defn
async def call_legacy_logic_app(
    step_id: str,
    action: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Execute a legacy Logic App step via HTTP invocation.

    Args:
        step_id: Unique step identifier from the integration manifest.
        action: Logic App action or endpoint name.
        parameters: Input payload and configuration for the Logic App.

    Returns:
        Execution result dictionary including status and response payload.
    """
    logger.info(
        "Invoking legacy Logic App step '%s' (action: %s) with %d parameters",
        step_id,
        action,
        len(parameters),
    )
    # Simulated execution for local dev and testing
    return {
        "step_id": step_id,
        "action": action,
        "status": "COMPLETED",
        "type": "legacy_logic_app",
        "message": f"Logic App '{action}' executed successfully",
        "output": {
            "statusCode": 200,
            "simulated": True,
            "parameters": parameters,
        },
    }
