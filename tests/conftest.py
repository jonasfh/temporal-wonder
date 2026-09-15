"""Shared pytest fixtures for schema, mock server, and Temporal test suites."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
from temporalio.testing import WorkflowEnvironment

from temporal_wonder.config import get_settings
from temporal_wonder.testing.harness import get_test_runtime
from temporal_wonder.testing.mock_server import LogicAppMockServer


@pytest.fixture
def repo_root() -> Path:
    """Return the absolute path to the repository root."""
    return Path(__file__).parent.parent


@pytest.fixture
def schema_path(repo_root: Path) -> Path:
    """Return path to manifest.schema.json."""
    return repo_root / "schemas" / "manifest.schema.json"


@pytest.fixture
def manifest_schema(schema_path: Path) -> dict[str, Any]:
    """Return parsed JSON schema dictionary."""
    return json.loads(schema_path.read_text(encoding="utf-8"))


@pytest.fixture
def sample_manifest_yaml_path(repo_root: Path) -> Path:
    """Return path to sample-manifest.yaml."""
    return repo_root / "examples" / "sample-manifest.yaml"


@pytest.fixture
def sample_manifest_json_path(repo_root: Path) -> Path:
    """Return path to sample-manifest.json."""
    return repo_root / "examples" / "sample-manifest.json"


@pytest.fixture
def legacy_manifest_example_path(repo_root: Path) -> Path:
    """Return path to legacy manifest-example.json."""
    return repo_root / "manifest-example.json"


@pytest.fixture
def logic_app_mock() -> Iterator[LogicAppMockServer]:
    """Start in-process Logic App mock HTTP server and point configuration to it."""
    old_base_url = os.environ.get("LOGIC_APP_BASE_URL")
    with LogicAppMockServer() as server:
        os.environ["LOGIC_APP_BASE_URL"] = server.base_url
        get_settings.cache_clear()
        yield server

    if old_base_url is not None:
        os.environ["LOGIC_APP_BASE_URL"] = old_base_url
    else:
        os.environ.pop("LOGIC_APP_BASE_URL", None)
    get_settings.cache_clear()


@pytest.fixture
async def temporal_env() -> AsyncIterator[WorkflowEnvironment]:
    """Provide a Temporal WorkflowEnvironment with time skipping enabled."""
    async with await WorkflowEnvironment.start_time_skipping(runtime=get_test_runtime()) as env:
        yield env
