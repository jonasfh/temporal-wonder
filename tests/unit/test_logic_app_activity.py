"""Unit tests for call_legacy_logic_app activity."""

from __future__ import annotations

import pytest
from temporalio.exceptions import ApplicationError

from temporal_wonder.activities.legacy.logic_app import call_legacy_logic_app
from temporal_wonder.testing.mock_server import LogicAppMockServer


@pytest.mark.asyncio
async def test_call_legacy_logic_app_success(logic_app_mock: LogicAppMockServer) -> None:
    """Verify successful Logic App invocation returns status COMPLETED and output."""
    logic_app_mock.set_response(
        "conf_teamspost",
        status_code=200,
        body={"delivered": True, "channel": "Finanstilsynet-Dev"},
    )

    result = await call_legacy_logic_app(
        step_id="step_teams_1",
        action="conf_teamspost",
        parameters={"message": "Alert triggered"},
    )

    assert result["status"] == "COMPLETED"
    assert result["step_id"] == "step_teams_1"
    assert result["action"] == "conf_teamspost"
    assert result["type"] == "legacy_logic_app"
    assert result["output"]["statusCode"] == 200
    assert result["output"]["response"]["delivered"] is True

    # Verify mock server recorded the request
    requests = logic_app_mock.get_requests_for_action("conf_teamspost")
    assert len(requests) == 1
    req = requests[0]
    assert req.method == "POST"
    assert req.body == {
        "step_id": "step_teams_1",
        "action": "conf_teamspost",
        "parameters": {"message": "Alert triggered"},
    }


@pytest.mark.asyncio
async def test_call_legacy_logic_app_500_server_error(
    logic_app_mock: LogicAppMockServer,
) -> None:
    """Verify 500 error raises a retryable ApplicationError."""
    logic_app_mock.set_response(
        "conf_fail",
        status_code=500,
        body={"error": "Internal Logic App Error"},
    )

    with pytest.raises(ApplicationError) as exc_info:
        await call_legacy_logic_app(
            step_id="step_fail_1",
            action="conf_fail",
            parameters={},
        )

    assert "HTTP 500" in str(exc_info.value)
    # Server error must be retryable (non_retryable is False)
    assert exc_info.value.non_retryable is False


@pytest.mark.asyncio
async def test_call_legacy_logic_app_400_client_error(
    logic_app_mock: LogicAppMockServer,
) -> None:
    """Verify 400 client error raises a non-retryable ApplicationError."""
    logic_app_mock.set_response(
        "conf_bad_req",
        status_code=400,
        body={"error": "Missing required field: schema_id"},
    )

    with pytest.raises(ApplicationError) as exc_info:
        await call_legacy_logic_app(
            step_id="step_bad_1",
            action="conf_bad_req",
            parameters={},
        )

    assert "HTTP 400" in str(exc_info.value)
    # 400 is non-retryable
    assert exc_info.value.non_retryable is True


@pytest.mark.asyncio
async def test_call_legacy_logic_app_network_error() -> None:
    """Verify connection failure to unreachable endpoint raises a retryable ApplicationError."""
    # Point to an unused loopback port where no server is listening
    with pytest.raises(ApplicationError) as exc_info:
        await call_legacy_logic_app(
            step_id="step_net_1",
            action="conf_unreachable",
            parameters={"endpoint_url": "http://127.0.0.1:59999/api/unreachable"},
        )

    assert "Network error" in str(exc_info.value)
    assert exc_info.value.non_retryable is False


@pytest.mark.asyncio
async def test_call_legacy_logic_app_custom_url(logic_app_mock: LogicAppMockServer) -> None:
    """Verify endpoint_url parameter overrides the default base URL."""
    custom_url = f"{logic_app_mock.base_url}/custom/path/action"
    logic_app_mock.set_response("action", status_code=200, body={"custom": True})

    result = await call_legacy_logic_app(
        step_id="step_custom_1",
        action="action",
        parameters={"endpoint_url": custom_url},
    )

    assert result["status"] == "COMPLETED"
    assert result["output"]["statusCode"] == 200
