"""Migration utility converting legacy Logic App manifests to Temporal DAG manifests."""

from __future__ import annotations

import re
from typing import Any

from temporal_wonder.models.legacy import LegacyManifest
from temporal_wonder.models.manifest import (
    ConditionConfig,
    ConditionType,
    Manifest,
    StepConfig,
    StepType,
    TriggerConfig,
)


def _slugify(text: str) -> str:
    """Convert text into a valid identifier slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    return text.strip("_")


# Mapping of common legacy trigger aliases to producing step types
DEFAULT_TRIGGER_PRODUCER_MAP: dict[str, str] = {
    "wf_rename_xml": "conf_rename_xml",
    "wf_zip": "conf_zip",
    "wf_websak_opprett_shared": "conf_dist_websak",
}


def migrate_legacy_manifest(
    legacy: LegacyManifest | dict[str, Any],
    *,
    root_triggers: set[str] | None = None,
    native_actions: set[str] | None = None,
    trigger_producer_map: dict[str, str] | None = None,
) -> Manifest:
    """Migrate a legacy integration manifest into a modern Temporal DAG Manifest.

    Args:
        legacy: LegacyManifest instance or raw dictionary.
        root_triggers: Names of triggers treated as root pipeline triggers (default:
            {"wf_altinn_instance_handling_shared"}).
        native_actions: Set of action names that have already been migrated to native
            activities. All others remain 'legacy_logic_app'.
        trigger_producer_map: Optional mapping between legacy trigger names and
            the integration type producing them.

    Returns:
        Validated modern Manifest instance.
    """
    if isinstance(legacy, dict):
        legacy = LegacyManifest.model_validate(legacy)

    root_triggers = root_triggers or {"wf_altinn_instance_handling_shared"}
    native_actions = native_actions or set()
    producer_map = {**DEFAULT_TRIGGER_PRODUCER_MAP, **(trigger_producer_map or {})}

    # Determine primary root trigger
    primary_trigger_name = "wf_altinn_instance_handling_shared"
    for integration in legacy.integrations:
        if integration.triggered_by in root_triggers:
            primary_trigger_name = integration.triggered_by
            break

    trigger = TriggerConfig(
        type="altinn3_instance" if "altinn" in primary_trigger_name else "event",
        name=primary_trigger_name,
        config={},
    )

    # First pass: assign unique step IDs and index which step produces which trigger
    step_id_by_action: dict[str, str] = {}
    assigned_ids: set[str] = set()
    provisional_steps: list[dict[str, Any]] = []

    for index, integration in enumerate(legacy.integrations, start=1):
        slug_name = _slugify(integration.name)
        candidate_id = f"step_{index}_{integration.type}"
        if slug_name:
            candidate_id = f"step_{index}_{slug_name}"

        # Clean step ID according to pattern
        step_id = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", candidate_id)
        while step_id in assigned_ids:
            step_id = f"{step_id}_dup"
        assigned_ids.add(step_id)

        # Record action mapping for dependency resolution
        if integration.type not in step_id_by_action:
            step_id_by_action[integration.type] = step_id

        provisional_steps.append(
            {
                "step_id": step_id,
                "integration": integration,
            }
        )

    # Second pass: resolve dependencies and convert to StepConfig
    steps: list[StepConfig] = []
    for item in provisional_steps:
        step_id = item["step_id"]
        integration = item["integration"]

        depends_on: list[str] = []
        triggered_by = integration.triggered_by

        if triggered_by not in root_triggers:
            # Check if this trigger corresponds to a producer step
            producer_action = producer_map.get(triggered_by)
            if producer_action and producer_action in step_id_by_action:
                depends_on.append(step_id_by_action[producer_action])

        # Map condition if present
        condition: ConditionConfig | None = None
        if integration.condition:
            cond_type_str = integration.condition.type.lower()
            if cond_type_str == "in":
                cond_type = ConditionType.IN
            elif cond_type_str == "equals":
                cond_type = ConditionType.EQUALS
            elif cond_type_str == "not_equals":
                cond_type = ConditionType.NOT_EQUALS
            else:
                cond_type = ConditionType.EQUALS

            condition = ConditionConfig(
                type=cond_type,
                source=integration.condition.source,
                value=integration.condition.value,
            )

        step_type = (
            StepType.NATIVE if integration.type in native_actions else StepType.LEGACY_LOGIC_APP
        )

        steps.append(
            StepConfig(
                id=step_id,
                name=integration.name,
                type=step_type,
                action=integration.type,
                description=integration.description,
                dependsOn=depends_on,
                condition=condition,
                parameters=integration.config,
            )
        )

    return Manifest(
        identifier=legacy.identifier,
        version="1.0.0",
        title=legacy.title,
        description=legacy.description,
        domain=legacy.domain,
        classification=legacy.classification,
        is_active=legacy.is_active,
        system_options=legacy.system_options,
        trigger=trigger,
        steps=steps,
    )
