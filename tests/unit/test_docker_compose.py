"""Unit tests validating docker-compose.yml structure and service definitions."""

from pathlib import Path
from typing import Any

import yaml


def test_docker_compose_valid_yaml() -> None:
    """Verify docker-compose.yml exists and is valid YAML."""
    compose_path = Path("docker-compose.yml")
    assert compose_path.is_file(), "docker-compose.yml must exist at repository root"

    content = compose_path.read_text(encoding="utf-8")
    data: dict[str, Any] = yaml.safe_load(content)

    assert "services" in data, "docker-compose.yml must define 'services'"
    assert "volumes" in data, "docker-compose.yml must define 'volumes'"


def test_docker_compose_temporal_service() -> None:
    """Verify Temporal dev-server service configuration and ports."""
    compose_path = Path("docker-compose.yml")
    data: dict[str, Any] = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    services = data["services"]

    assert "temporal" in services, "Must include 'temporal' service"
    temporal = services["temporal"]

    assert "temporalio/temporal" in temporal["image"]
    ports = [str(p) for p in temporal.get("ports", [])]
    assert any("7233" in p for p in ports), "Temporal gRPC port 7233 must be exposed"
    assert any("8233" in p for p in ports), "Temporal Web UI port 8233 must be exposed"

    assert "healthcheck" in temporal, "Temporal service should specify a healthcheck"


def test_docker_compose_azurite_service() -> None:
    """Verify Azurite blob emulator service configuration and ports."""
    compose_path = Path("docker-compose.yml")
    data: dict[str, Any] = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    services = data["services"]

    assert "azurite" in services, "Must include 'azurite' service"
    azurite = services["azurite"]

    assert "azure-storage/azurite" in azurite["image"]
    ports = [str(p) for p in azurite.get("ports", [])]
    assert any("10000" in p for p in ports), "Azurite Blob port 10000 must be exposed"


def test_docker_compose_wiremock_service() -> None:
    """Verify WireMock service configuration and ports."""
    compose_path = Path("docker-compose.yml")
    data: dict[str, Any] = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    services = data["services"]

    assert "wiremock" in services, "Must include 'wiremock' service"
    wiremock = services["wiremock"]

    assert "wiremock/wiremock" in wiremock["image"]
    ports = [str(p) for p in wiremock.get("ports", [])]
    assert any("8080" in p for p in ports), "WireMock port 8080 must be exposed"


def test_env_example_matches_compose() -> None:
    """Verify .env.example exists and contains expected local endpoints."""
    env_path = Path(".env.example")
    assert env_path.is_file(), ".env.example must exist at repository root"

    content = env_path.read_text(encoding="utf-8")
    assert "TEMPORAL_HOST_URL=localhost:7233" in content
    assert "10000" in content
    assert "TEMPORAL_TASK_QUEUE" in content
    assert "LOGIC_APP_BASE_URL=http://localhost:8080" in content
