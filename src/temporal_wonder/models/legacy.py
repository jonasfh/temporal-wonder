"""Pydantic v2 models representing the legacy Logic App manifest format."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class LegacyCondition(BaseModel):
    """Condition in legacy manifest."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(description="Condition operator (e.g. in, equals)")
    source: str = Field(description="Data path expression")
    value: Any = Field(default=None, description="Target value")


class LegacyIntegration(BaseModel):
    """Integration configuration item in legacy manifest."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(..., description="Integration type (e.g., conf_send_email, conf_zip)")
    triggered_by: str = Field(..., description="Parent workflow or trigger identifier")
    name: str = Field(..., description="Human readable integration name")
    description: str | None = Field(default=None, description="Description")
    condition: LegacyCondition | None = Field(default=None, description="Optional condition")
    config: dict[str, Any] = Field(default_factory=dict, description="Integration config")


class LegacyManifest(BaseModel):
    """Legacy integration manifest schema (e.g., krt-0000a-1)."""

    model_config = ConfigDict(extra="allow")

    identifier: str = Field(..., description="Schema identifier (e.g., krt-0000a-1)")
    classification: str | None = Field(default=None, description="Classification (e.g. K2)")
    domain: str | None = Field(default=None, description="Domain (e.g. bank)")
    title: str | None = Field(default=None, description="Title")
    description: str | None = Field(default=None, description="Description")
    is_active: bool = Field(default=True, description="Active status")
    system_options: dict[str, Any] = Field(default_factory=dict, description="System options")
    integrations: list[LegacyIntegration] = Field(
        default_factory=list,
        description="List of integration definitions",
    )

    @classmethod
    def load(cls, path_or_content: str | Path | dict[str, Any]) -> LegacyManifest:
        """Load legacy manifest from file path, raw string, or dict."""
        if isinstance(path_or_content, dict):
            return cls.model_validate(path_or_content)
        path = Path(str(path_or_content))
        if path.is_file():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return cls.model_validate(data)
        data = yaml.safe_load(str(path_or_content))
        return cls.model_validate(data)
