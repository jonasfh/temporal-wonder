"""Legacy activities delegating work to external Azure Logic Apps via HTTP."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from temporalio import activity
from temporalio.exceptions import ApplicationError

from temporal_wonder.config import get_settings

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

    Raises:
        ApplicationError: On HTTP error response or network failure.
    """
    settings = get_settings()

    # Determine endpoint URL
    url = parameters.get("endpoint_url") or parameters.get("url")
    if not url:
        base_url = settings.logic_app_base_url.rstrip("/")
        url = f"{base_url}/api/logicapps/{action}"

    logger.info(
        "Invoking legacy Logic App step '%s' (action: %s) at %s with %d parameter(s)",
        step_id,
        action,
        url,
        len(parameters),
    )

    payload = {
        "step_id": step_id,
        "action": action,
        "parameters": parameters,
    }

    timeout_seconds = settings.logic_app_timeout_seconds

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
    except httpx.RequestError as exc:
        logger.error(
            "Network error connecting to Logic App for step '%s' (action: %s): %s",
            step_id,
            action,
            exc,
        )
        raise ApplicationError(
            f"Network error calling Logic App action '{action}' for step '{step_id}': {exc}",
            non_retryable=False,
        ) from exc

    # Success handling (2xx)
    if 200 <= response.status_code < 300:
        try:
            output_data = response.json()
        except Exception:
            output_data = {"raw": response.text}

        logger.info(
            "Logic App step '%s' (action: %s) succeeded with HTTP %d",
            step_id,
            action,
            response.status_code,
        )
        return {
            "step_id": step_id,
            "action": action,
            "status": "COMPLETED",
            "type": "legacy_logic_app",
            "message": f"Logic App '{action}' executed successfully",
            "output": {
                "statusCode": response.status_code,
                "response": output_data,
                "parameters": parameters,
            },
        }

    # Error handling
    err_message = (
        f"Logic App action '{action}' (step '{step_id}') failed with HTTP {response.status_code}: "
        f"{response.text}"
    )
    logger.warning(err_message)

    # 4xx client errors (except 408 Request Timeout and 429 Too Many Requests) are non-retryable
    is_transient = response.status_code in (408, 429) or response.status_code >= 500
    is_client_error = 400 <= response.status_code < 500

    raise ApplicationError(
        err_message,
        non_retryable=not is_transient and is_client_error,
    )
