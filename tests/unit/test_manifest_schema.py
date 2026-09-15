"""Unit tests for JSON Schema and Pydantic v2 validation of manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
import yaml

from temporal_wonder.models.manifest import (
    Manifest,
    StepConfig,
    StepType,
    load_manifest,
)


def test_sample_manifest_json_validates_against_schema(
    manifest_schema: dict[str, Any],
    sample_manifest_json_path: Path,
) -> None:
    """Ensure sample-manifest.json strictly conforms to schemas/manifest.schema.json."""
    data = json.loads(sample_manifest_json_path.read_text(encoding="utf-8"))
    # jsonschema.validate raises ValidationError if invalid
    jsonschema.validate(instance=data, schema=manifest_schema)


def test_sample_manifest_yaml_validates_against_schema(
    manifest_schema: dict[str, Any],
    sample_manifest_yaml_path: Path,
) -> None:
    """Ensure sample-manifest.yaml strictly conforms to schemas/manifest.schema.json."""
    data = yaml.safe_load(sample_manifest_yaml_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=data, schema=manifest_schema)


def test_load_manifest_from_yaml_file(sample_manifest_yaml_path: Path) -> None:
    """Test loading Manifest Pydantic model directly from YAML file."""
    manifest = load_manifest(sample_manifest_yaml_path)

    assert manifest.identifier == "krt-0000a-1-modernized"
    assert manifest.version == "1.0.0"
    assert manifest.domain == "bank"
    assert manifest.classification == "K2"
    assert len(manifest.steps) == 5

    step_teams = manifest.get_step_by_id("step_teams_notification")
    assert step_teams.type == StepType.LEGACY_LOGIC_APP
    assert step_teams.action == "conf_teamspost"

    step_fetch = manifest.get_step_by_id("step_fetch_altinn_data")
    assert step_fetch.type == StepType.NATIVE


def test_manifest_execution_layers_topological_sort(sample_manifest_yaml_path: Path) -> None:
    """Verify that topological execution layers correctly group parallel and dependent steps."""
    manifest = load_manifest(sample_manifest_yaml_path)
    layers = manifest.get_execution_layers()

    # Layer 0: Root steps without dependencies (step_teams_notification, step_fetch_altinn_data)
    assert set(layers[0]) == {"step_fetch_altinn_data", "step_teams_notification"}

    # Layer 1: step_process_xml (depends on step_fetch_altinn_data)
    assert layers[1] == ["step_process_xml"]

    # Layer 2: step_archive_websak (depends on step_process_xml)
    assert layers[2] == ["step_archive_websak"]

    # Layer 3: step_send_receipt (depends on step_archive_websak)
    assert layers[3] == ["step_send_receipt"]


def test_manifest_rejects_duplicate_step_ids() -> None:
    """Verify ValueError is raised when two steps share the same ID."""
    with pytest.raises(ValueError, match="Duplicate step IDs found"):
        Manifest(
            identifier="test-dup",
            version="1.0.0",
            steps=[
                StepConfig(
                    id="step_a",
                    name="Step A",
                    type=StepType.NATIVE,
                    action="act_a",
                ),
                StepConfig(
                    id="step_a",
                    name="Step A Duplicate",
                    type=StepType.NATIVE,
                    action="act_b",
                ),
            ],
        )


def test_manifest_rejects_missing_dependency() -> None:
    """Verify ValueError is raised when a step depends on a non-existent step ID."""
    with pytest.raises(ValueError, match="depends on non-existent step 'step_ghost'"):
        Manifest(
            identifier="test-missing-dep",
            version="1.0.0",
            steps=[
                StepConfig(
                    id="step_a",
                    name="Step A",
                    type=StepType.NATIVE,
                    action="act_a",
                    dependsOn=["step_ghost"],
                ),
            ],
        )


def test_manifest_rejects_self_dependency() -> None:
    """Verify ValueError is raised when a step depends on itself."""
    with pytest.raises(ValueError, match="cannot depend on itself"):
        Manifest(
            identifier="test-self-cycle",
            version="1.0.0",
            steps=[
                StepConfig(
                    id="step_self",
                    name="Step Self",
                    type=StepType.NATIVE,
                    action="act_a",
                    dependsOn=["step_self"],
                ),
            ],
        )


def test_manifest_rejects_circular_dependencies() -> None:
    """Verify ValueError is raised when a circular dependency exists in DAG."""
    with pytest.raises(ValueError, match="Circular dependency detected"):
        Manifest(
            identifier="test-cycle",
            version="1.0.0",
            steps=[
                StepConfig(
                    id="step_1",
                    name="Step 1",
                    type=StepType.NATIVE,
                    action="act_1",
                    dependsOn=["step_3"],
                ),
                StepConfig(
                    id="step_2",
                    name="Step 2",
                    type=StepType.NATIVE,
                    action="act_2",
                    dependsOn=["step_1"],
                ),
                StepConfig(
                    id="step_3",
                    name="Step 3",
                    type=StepType.NATIVE,
                    action="act_3",
                    dependsOn=["step_2"],
                ),
            ],
        )
