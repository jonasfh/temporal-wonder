"""Configuration management using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and optional .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    temporal_host_url: str = Field(
        default="localhost:7233",
        description="Temporal gRPC server host and port.",
    )
    temporal_namespace: str = Field(
        default="default",
        description="Temporal namespace.",
    )
    temporal_task_queue: str = Field(
        default="temporal-wonder-queue",
        description="Default Temporal task queue name.",
    )
    azure_storage_connection_string: str = Field(
        default=(
            "DefaultEndpointsProtocol=http;"
            "AccountName=devstoreaccount1;"
            "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
            "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
        ),
        description="Connection string for Azure Blob Storage or Azurite emulator.",
    )
    azure_blob_container: str = Field(
        default="integration-files",
        description="Azure Blob Storage container name for pipeline files.",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR).",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
