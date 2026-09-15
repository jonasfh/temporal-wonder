# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-09-15

### Added
- In-process HTTP mock server (`LogicAppMockServer`) with action route configuration, sequential responses (for retry simulation), and request tracking.
- Test harness helpers (`create_test_worker`, `execute_manifest_workflow`) for automated integration testing with Temporal `WorkflowEnvironment`.
- Shared pytest fixtures `logic_app_mock` and `temporal_env` in `tests/conftest.py`.
- End-to-end integration tests (`test_manifest_execution.py`) executing full DAG manifests locally without external network dependencies.
- Retry behavior integration tests (`test_retry_behavior.py`) validating Temporal's automatic retry policies upon HTTP 500 transient errors.
- Unit test suites for `LogicAppMockServer` and `call_legacy_logic_app` HTTP activity.
- WireMock service in `docker-compose.yml` (port 8080) with default response mappings for manual local testing.
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) automating Ruff, Mypy, and Pytest.
- New configuration settings `logic_app_base_url` and `logic_app_timeout_seconds`.

### Changed
- Refactored `call_legacy_logic_app` to perform real HTTP POST requests via `httpx.AsyncClient` with proper error classification (`ApplicationError` with retryable vs non-retryable flags).
- Bumped project version to `0.2.0` with `httpx>=0.27.0` dependency.

## [0.1.0] - 2026-09-15

### Added
- Initial proof-of-concept repository structure and agent instructions.
- Integration DAG manifest JSON Schema and Pydantic models.
- Temporal Master Orchestrator workflow with topological layer concurrency.
- Docker Compose setup for Temporal dev-server and Azurite blob storage emulator.
