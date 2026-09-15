"""Unit tests for migrating legacy Logic App manifests to Temporal DAG manifests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema

from temporal_wonder.models.legacy import LegacyManifest
from temporal_wonder.models.manifest import StepType
from temporal_wonder.models.migration import migrate_legacy_manifest


def test_load_legacy_manifest_example(legacy_manifest_example_path: Path) -> None:
    """Ensure existing manifest-example.json loads successfully into LegacyManifest model."""
    legacy = LegacyManifest.load(legacy_manifest_example_path)

    assert legacy.identifier == "krt-0000a-1"
    assert legacy.classification == "K2"
    assert legacy.domain == "bank"
    assert legacy.title == "Åpen test skjema"
    assert len(legacy.integrations) == 14


def test_migrate_legacy_manifest_to_temporal_dag(
    legacy_manifest_example_path: Path,
    manifest_schema: dict[str, Any],
) -> None:
    """Ensure legacy manifest transforms into a valid Temporal DAG manifest."""
    legacy = LegacyManifest.load(legacy_manifest_example_path)
    migrated = migrate_legacy_manifest(
        legacy,
        native_actions={"conf_rename_xml", "conf_zip"},
    )

    assert migrated.identifier == "krt-0000a-1"
    assert migrated.version == "1.0.0"
    assert migrated.domain == "bank"
    assert len(migrated.steps) == 14

    # Check that native_actions were marked as native and others as legacy_logic_app
    steps_by_action: dict[str, list] = {}
    for step in migrated.steps:
        steps_by_action.setdefault(step.action, []).append(step)

    assert steps_by_action["conf_rename_xml"][0].type == StepType.NATIVE
    assert steps_by_action["conf_zip"][0].type == StepType.NATIVE
    assert steps_by_action["conf_teamspost"][0].type == StepType.LEGACY_LOGIC_APP

    # Check dependency chaining (wf_rename_xml -> conf_zip -> wf_zip -> conf_dist_hubex)
    rename_step = steps_by_action["conf_rename_xml"][0]
    zip_step = steps_by_action["conf_zip"][0]
    hubex_step = steps_by_action["conf_dist_hubex"][0]

    assert zip_step.depends_on == [rename_step.id]
    assert hubex_step.depends_on == [zip_step.id]

    # Verify that the migrated model conforms to the JSON Schema
    migrated_dict = migrated.model_dump(by_alias=True, exclude_none=True)
    jsonschema.validate(instance=migrated_dict, schema=manifest_schema)


def test_migrated_manifest_dag_execution_layers(legacy_manifest_example_path: Path) -> None:
    """Verify that topological execution layers can be generated for the migrated manifest."""
    legacy = LegacyManifest.load(legacy_manifest_example_path)
    migrated = migrate_legacy_manifest(legacy)

    layers = migrated.get_execution_layers()
    assert len(layers) >= 3

    # The first layer should contain root steps (triggered by wf_altinn_instance_handling_shared)
    # The second layer contains steps waiting on layer 1 (e.g. conf_zip waiting on conf_rename_xml)
    # The third layer contains steps waiting on layer 2 (e.g. conf_dist_hubex waiting on conf_zip)
    all_step_ids = [step.id for step in migrated.steps]
    flattened_layer_ids = [sid for layer in layers for sid in layer]
    assert sorted(all_step_ids) == sorted(flattened_layer_ids)
