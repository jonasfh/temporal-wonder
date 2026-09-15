"""Pydantic v2 domain models for declarative Temporal integration manifests."""

from __future__ import annotations

from collections import defaultdict, deque
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StepType(StrEnum):
    """Execution type for a manifest pipeline step."""

    LEGACY_LOGIC_APP = "legacy_logic_app"
    NATIVE = "native"


class ConditionType(StrEnum):
    """Supported condition comparison operators."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class ConditionConfig(BaseModel):
    """Precondition evaluated prior to scheduling a step."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    type: ConditionType = Field(description="Comparison operator")
    source: str = Field(description="JSONPath or dot-separated source path")
    value: Any = Field(default=None, description="Expected value or target list")


class RetryPolicyConfig(BaseModel):
    """Temporal activity retry policy."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    initial_interval: str | int | float | None = Field(
        default=None,
        alias="initialInterval",
        description="Initial retry interval (e.g., '1s' or 1)",
    )
    backoff_coefficient: float = Field(
        default=2.0,
        alias="backoffCoefficient",
        ge=1.0,
        description="Exponential backoff coefficient",
    )
    maximum_interval: str | int | float | None = Field(
        default=None,
        alias="maximumInterval",
        description="Maximum interval between retries",
    )
    maximum_attempts: int = Field(
        default=3,
        alias="maximumAttempts",
        ge=0,
        description="Max retry attempts (0 for unlimited)",
    )
    non_retryable_error_types: list[str] = Field(
        default_factory=list,
        alias="nonRetryableErrorTypes",
        description="Errors that should not be retried",
    )


class TimeoutConfig(BaseModel):
    """Temporal activity timeouts."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    start_to_close_timeout: str | int | float | None = Field(
        default=None,
        alias="startToCloseTimeout",
        description="Maximum execution time for a single activity attempt",
    )
    schedule_to_close_timeout: str | int | float | None = Field(
        default=None,
        alias="scheduleToCloseTimeout",
        description="Maximum total time from schedule to completion",
    )
    heartbeat_timeout: str | int | float | None = Field(
        default=None,
        alias="heartbeatTimeout",
        description="Maximum interval between activity progress heartbeats",
    )


class StepConfig(BaseModel):
    """Configuration for an individual step in the integration DAG."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: str = Field(..., pattern=r"^[a-zA-Z0-9_\-\.]+$", description="Unique step identifier")
    name: str = Field(..., description="Human-readable step name")
    type: StepType = Field(..., description="Step type: legacy_logic_app or native")
    action: str = Field(..., description="Target activity or Logic App action name")
    description: str | None = Field(default=None, description="Optional step description")
    depends_on: list[str] = Field(
        default_factory=list,
        alias="dependsOn",
        description="Step IDs this step depends on",
    )
    condition: ConditionConfig | None = Field(
        default=None,
        description="Optional execution condition",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Input parameters, payload templates, or configuration",
    )
    retry_policy: RetryPolicyConfig | None = Field(
        default=None,
        alias="retryPolicy",
        description="Custom retry policy",
    )
    timeout: TimeoutConfig | None = Field(
        default=None,
        description="Custom activity timeouts",
    )


class TriggerConfig(BaseModel):
    """Trigger initiating the integration pipeline."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    type: str = Field(..., description="Trigger type (e.g., altinn3_instance, cron, manual)")
    name: str | None = Field(default=None, description="Descriptive trigger name")
    config: dict[str, Any] = Field(default_factory=dict, description="Trigger parameters")


class Manifest(BaseModel):
    """Declarative DAG manifest for a Temporal integration pipeline."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    identifier: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_\-\.]+$",
        description="Unique manifest identifier",
    )
    version: str = Field(default="1.0.0", description="Manifest schema version")
    title: str | None = Field(default=None, description="Human-readable title")
    description: str | None = Field(default=None, description="Workflow description")
    domain: str | None = Field(default=None, description="Business domain (e.g. bank)")
    classification: str | None = Field(default=None, description="Data classification (e.g. K2)")
    is_active: bool = Field(default=True, description="Whether workflow is enabled")
    system_options: dict[str, Any] = Field(
        default_factory=dict,
        description="System options (e.g. top_level_folder)",
    )
    trigger: TriggerConfig | None = Field(
        default=None,
        description="Trigger definition",
    )
    steps: list[StepConfig] = Field(
        ...,
        min_length=1,
        description="List of pipeline steps forming the DAG",
    )

    @model_validator(mode="after")
    def validate_dag(self) -> Manifest:
        """Validate DAG integrity: unique IDs, valid dependency references, and no cycles."""
        step_ids = {step.id for step in self.steps}

        # 1. Uniqueness
        if len(step_ids) != len(self.steps):
            counts: dict[str, int] = defaultdict(int)
            for step in self.steps:
                counts[step.id] += 1
            duplicates = [sid for sid, count in counts.items() if count > 1]
            raise ValueError(f"Duplicate step IDs found in manifest: {duplicates}")

        # 2. Reference validation
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise ValueError(f"Step '{step.id}' depends on non-existent step '{dep}'")
                if dep == step.id:
                    raise ValueError(f"Step '{step.id}' cannot depend on itself (self-cycle)")

        # 3. Cycle detection using Kahn's algorithm
        in_degree: dict[str, int] = dict.fromkeys(step_ids, 0)
        adjacency: dict[str, list[str]] = defaultdict(list)

        for step in self.steps:
            for dep in step.depends_on:
                adjacency[dep].append(step.id)
                in_degree[step.id] += 1

        queue: deque[str] = deque([sid for sid, degree in in_degree.items() if degree == 0])
        visited_count = 0

        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(self.steps):
            unresolved = [sid for sid, degree in in_degree.items() if degree > 0]
            raise ValueError(f"Circular dependency detected involving steps: {unresolved}")

        return self

    def get_step_by_id(self, step_id: str) -> StepConfig:
        """Retrieve a step by its unique ID. Raises KeyError if not found."""
        for step in self.steps:
            if step.id == step_id:
                return step
        raise KeyError(f"Step with id '{step_id}' not found in manifest")

    def get_execution_layers(self) -> list[list[str]]:
        """Return steps partitioned into parallel topological execution layers."""
        step_ids = {step.id for step in self.steps}
        in_degree: dict[str, int] = dict.fromkeys(step_ids, 0)
        adjacency: dict[str, list[str]] = defaultdict(list)

        for step in self.steps:
            for dep in step.depends_on:
                adjacency[dep].append(step.id)
                in_degree[step.id] += 1

        current_layer: list[str] = [sid for sid, degree in in_degree.items() if degree == 0]
        layers: list[list[str]] = []

        while current_layer:
            layers.append(sorted(current_layer))
            next_layer: list[str] = []
            for node in current_layer:
                for neighbor in adjacency[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_layer.append(neighbor)
            current_layer = next_layer

        return layers


def load_manifest(source: str | Path | dict[str, Any]) -> Manifest:
    """Load and validate a Manifest from a YAML/JSON file, string, or dictionary.

    Args:
        source: File path (str or Path), raw YAML/JSON content string, or dictionary.

    Returns:
        Validated Manifest instance.
    """
    if isinstance(source, dict):
        return Manifest.model_validate(source)

    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            return Manifest.model_validate(data)
        # Otherwise parse as raw string content
        data = yaml.safe_load(str(source))
        return Manifest.model_validate(data)

    raise TypeError(f"Unsupported manifest source type: {type(source)}")
