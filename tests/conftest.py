"""Shared pytest fixtures for schema and manifest test suites."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


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
