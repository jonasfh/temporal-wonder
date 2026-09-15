"""In-process mock HTTP server simulating Azure Logic Apps endpoints for CI/CD and tests."""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class RecordedRequest:
    """Record of an incoming HTTP request received by the mock server."""

    method: str
    path: str
    action: str
    headers: dict[str, str]
    body: dict[str, Any] | str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ResponseConfig:
    """Configuration for a mock HTTP response."""

    status_code: int = 200
    body: dict[str, Any] | str | None = None
    headers: dict[str, str] = field(default_factory=dict)


class _MockRequestHandler(BaseHTTPRequestHandler):
    """Internal HTTP request handler routing requests to LogicAppMockServer state."""

    server: _MockThreadingHTTPServer  # type: ignore[assignment]

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default stderr logging."""
        logger.debug("LogicAppMockServer: " + format, *args)

    def do_POST(self) -> None:
        """Handle incoming POST requests to mock Logic App endpoints."""
        self._handle_request("POST")

    def do_GET(self) -> None:
        """Handle incoming GET requests (health checks or queries)."""
        self._handle_request("GET")

    def _handle_request(self, method: str) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""
        parsed_body: dict[str, Any] | str
        try:
            parsed_body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception:
            parsed_body = raw_body.decode("utf-8", errors="replace")

        # Extract action from path (e.g. /api/logicapps/conf_teamspost -> conf_teamspost)
        action = path.rstrip("/").split("/")[-1] if path.strip("/") else ""
        if isinstance(parsed_body, dict) and "action" in parsed_body:
            action = str(parsed_body["action"])

        headers_dict = dict(self.headers.items())
        recorded = RecordedRequest(
            method=method,
            path=path,
            action=action,
            headers=headers_dict,
            body=parsed_body,
        )

        mock_server = self.server.mock_server
        mock_server._record_request(recorded)

        response = mock_server._resolve_response(action, path)

        self.send_response(response.status_code)
        # Default content type to application/json unless specified
        resp_headers = dict(response.headers)
        if "Content-Type" not in resp_headers:
            resp_headers["Content-Type"] = "application/json"

        for header_name, header_value in resp_headers.items():
            self.send_header(header_name, header_value)
        self.end_headers()

        if response.body is not None:
            if isinstance(response.body, (dict, list)):
                response_bytes = json.dumps(response.body).encode("utf-8")
            elif isinstance(response.body, str):
                response_bytes = response.body.encode("utf-8")
            else:
                response_bytes = str(response.body).encode("utf-8")
            self.wfile.write(response_bytes)


class _MockThreadingHTTPServer(ThreadingHTTPServer):
    """Threading HTTPServer with a back-reference to LogicAppMockServer."""

    def __init__(self, server_address: tuple[str, int], mock_server: LogicAppMockServer) -> None:
        super().__init__(server_address, _MockRequestHandler)
        self.mock_server = mock_server


class LogicAppMockServer:
    """Mock HTTP server simulating Azure Logic App endpoints for tests and CI/CD.

    Supports:
    - Dynamic port allocation on 127.0.0.1
    - Response customization per Logic App action (status code, body, headers)
    - Sequential responses (e.g. return 500 twice, then 200, to test retries)
    - Recording all received requests for post-execution assertions
    - Sync and async context managers
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self.host = host
        self.requested_port = port
        self.actual_port: int = 0
        self._server: _MockThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._recorded_requests: list[RecordedRequest] = []
        self._action_routes: dict[str, ResponseConfig] = {}
        self._action_sequences: dict[str, list[ResponseConfig]] = {}
        self._default_response = ResponseConfig(
            status_code=200,
            body=None,
        )

    @property
    def base_url(self) -> str:
        """Return base URL of running mock server."""
        if not self._server or self.actual_port == 0:
            raise RuntimeError("Mock server is not running. Call start() first.")
        return f"http://{self.host}:{self.actual_port}"

    @property
    def recorded_requests(self) -> list[RecordedRequest]:
        """Return copy of all recorded requests."""
        with self._lock:
            return list(self._recorded_requests)

    def start(self) -> str:
        """Start mock HTTP server on background thread and return base URL."""
        if self._server is not None:
            return self.base_url

        self._server = _MockThreadingHTTPServer((self.host, self.requested_port), self)
        self.actual_port = self._server.server_address[1]
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="LogicAppMockServerThread",
            daemon=True,
        )
        self._thread.start()
        logger.info("Started LogicAppMockServer at %s", self.base_url)
        return self.base_url

    def stop(self) -> None:
        """Stop mock HTTP server and cleanup thread."""
        if self._server:
            logger.info("Stopping LogicAppMockServer at %s", self.base_url)
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
            self._thread = None
        self.actual_port = 0

    def reset(self) -> None:
        """Clear recorded requests and custom route configurations."""
        with self._lock:
            self._recorded_requests.clear()
            self._action_routes.clear()
            self._action_sequences.clear()

    def set_response(
        self,
        action: str,
        status_code: int = 200,
        body: dict[str, Any] | str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Configure static response for a specific action."""
        if body is None and 200 <= status_code < 300:
            body = {
                "action": action,
                "status": "COMPLETED",
                "statusCode": status_code,
                "message": f"Logic App '{action}' mocked response",
            }
        elif body is None:
            body = {"error": f"Error {status_code} in Logic App '{action}'"}

        with self._lock:
            self._action_routes[action] = ResponseConfig(
                status_code=status_code,
                body=body,
                headers=headers or {},
            )

    def set_response_sequence(
        self,
        action: str,
        responses: list[ResponseConfig | tuple[int, Any] | int],
    ) -> None:
        """Configure sequential responses for an action to simulate errors and retries."""
        parsed_responses: list[ResponseConfig] = []
        for r in responses:
            if isinstance(r, ResponseConfig):
                parsed_responses.append(r)
            elif isinstance(r, tuple):
                status_code, body = r
                parsed_responses.append(ResponseConfig(status_code=status_code, body=body))
            elif isinstance(r, int):
                body = (
                    {"status": "COMPLETED", "statusCode": r}
                    if 200 <= r < 300
                    else {"error": f"Error {r}"}
                )
                parsed_responses.append(ResponseConfig(status_code=r, body=body))
            else:
                raise TypeError(f"Invalid response item in sequence: {r}")

        with self._lock:
            self._action_sequences[action] = parsed_responses

    def get_requests_for_action(self, action: str) -> list[RecordedRequest]:
        """Return list of recorded requests matching specific action."""
        with self._lock:
            return [req for req in self._recorded_requests if req.action == action]

    def _record_request(self, request: RecordedRequest) -> None:
        with self._lock:
            self._recorded_requests.append(request)

    def _resolve_response(self, action: str, path: str) -> ResponseConfig:
        with self._lock:
            # Check sequential responses first
            if self._action_sequences.get(action):
                return self._action_sequences[action].pop(0)

            # Check static route response
            if action in self._action_routes:
                return self._action_routes[action]

            # Return default response
            default_body = {
                "action": action,
                "path": path,
                "status": "COMPLETED",
                "statusCode": self._default_response.status_code,
                "message": f"Logic App '{action}' handled by default mock",
            }
            return ResponseConfig(
                status_code=self._default_response.status_code,
                body=self._default_response.body or default_body,
                headers=self._default_response.headers,
            )

    def __enter__(self) -> LogicAppMockServer:
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    async def __aenter__(self) -> LogicAppMockServer:
        self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()
