"""Unit tests for LogicAppMockServer."""

from __future__ import annotations

import httpx
import pytest

from temporal_wonder.testing.mock_server import LogicAppMockServer


def test_mock_server_lifecycle() -> None:
    """Verify mock server start, base_url access, and clean stop."""
    server = LogicAppMockServer()
    with pytest.raises(RuntimeError):
        _ = server.base_url

    base_url = server.start()
    assert base_url.startswith("http://127.0.0.1:")
    assert server.actual_port > 0

    server.stop()
    assert server.actual_port == 0


@pytest.mark.asyncio
async def test_mock_server_default_response() -> None:
    """Verify default response for unregistered action."""
    async with LogicAppMockServer() as server:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{server.base_url}/api/logicapps/conf_teamspost",
                json={"message": "Hello Teams"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["action"] == "conf_teamspost"
            assert data["status"] == "COMPLETED"

        requests = server.get_requests_for_action("conf_teamspost")
        assert len(requests) == 1
        assert requests[0].method == "POST"
        assert requests[0].action == "conf_teamspost"
        assert requests[0].body == {"message": "Hello Teams"}


@pytest.mark.asyncio
async def test_mock_server_custom_response() -> None:
    """Verify configuring custom status code and body for an action."""
    async with LogicAppMockServer() as server:
        server.set_response(
            action="custom_action",
            status_code=201,
            body={"created_id": 12345},
            headers={"X-Custom-Header": "WonderTest"},
        )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{server.base_url}/api/logicapps/custom_action",
                json={"key": "val"},
            )
            assert resp.status_code == 201
            assert resp.json() == {"created_id": 12345}
            assert resp.headers.get("x-custom-header") == "WonderTest"


@pytest.mark.asyncio
async def test_mock_server_error_response() -> None:
    """Verify 500 Internal Server Error response configuration."""
    async with LogicAppMockServer() as server:
        server.set_response(
            action="faulty_action",
            status_code=500,
            body={"error": "Service temporarily unavailable"},
        )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{server.base_url}/api/logicapps/faulty_action",
                json={},
            )
            assert resp.status_code == 500
            assert resp.json()["error"] == "Service temporarily unavailable"


@pytest.mark.asyncio
async def test_mock_server_sequence_responses() -> None:
    """Verify sequential response handling for retry testing."""
    async with LogicAppMockServer() as server:
        server.set_response_sequence(
            action="flaky_action",
            responses=[
                500,
                (503, {"error": "Gateway Timeout"}),
                200,
            ],
        )

        async with httpx.AsyncClient() as client:
            url = f"{server.base_url}/api/logicapps/flaky_action"

            resp1 = await client.post(url, json={})
            assert resp1.status_code == 500

            resp2 = await client.post(url, json={})
            assert resp2.status_code == 503
            assert resp2.json()["error"] == "Gateway Timeout"

            resp3 = await client.post(url, json={})
            assert resp3.status_code == 200

        assert len(server.get_requests_for_action("flaky_action")) == 3


@pytest.mark.asyncio
async def test_mock_server_reset() -> None:
    """Verify that reset clears both routes and recorded requests."""
    async with LogicAppMockServer() as server:
        server.set_response("action1", status_code=500)
        async with httpx.AsyncClient() as client:
            await client.post(f"{server.base_url}/api/logicapps/action1", json={})

        assert len(server.recorded_requests) == 1
        server.reset()
        assert len(server.recorded_requests) == 0

        # Now should return default 200 response since routes were cleared
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{server.base_url}/api/logicapps/action1", json={})
            assert resp.status_code == 200
