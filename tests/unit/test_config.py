"""Unit tests for configuration loading and settings."""

import pytest

from temporal_wonder.config import Settings, get_settings


def test_default_settings() -> None:
    """Verify default settings point to local dev services."""
    settings = Settings()
    assert settings.temporal_host_url == "localhost:7233"
    assert settings.temporal_namespace == "default"
    assert settings.temporal_task_queue == "temporal-wonder-queue"
    assert "10000" in settings.azure_storage_connection_string
    assert settings.azure_blob_container == "integration-files"
    assert settings.logic_app_base_url == "http://localhost:8080"
    assert settings.logic_app_timeout_seconds == 30.0
    assert settings.log_level == "INFO"


def test_env_var_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify settings can be overridden via environment variables."""
    monkeypatch.setenv("TEMPORAL_HOST_URL", "10.0.0.1:7233")
    monkeypatch.setenv("TEMPORAL_NAMESPACE", "custom-ns")
    monkeypatch.setenv("TEMPORAL_TASK_QUEUE", "custom-queue")
    monkeypatch.setenv("LOGIC_APP_BASE_URL", "http://10.0.0.2:9090")
    monkeypatch.setenv("LOGIC_APP_TIMEOUT_SECONDS", "45.5")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings()
    assert settings.temporal_host_url == "10.0.0.1:7233"
    assert settings.temporal_namespace == "custom-ns"
    assert settings.temporal_task_queue == "custom-queue"
    assert settings.logic_app_base_url == "http://10.0.0.2:9090"
    assert settings.logic_app_timeout_seconds == 45.5
    assert settings.log_level == "DEBUG"


def test_get_settings_cached() -> None:
    """Verify get_settings returns a valid Settings instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
