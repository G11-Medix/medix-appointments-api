from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    supabase_url: str = Field(validation_alias="SUPABASE_URL")
    supabase_key: str = Field(validation_alias="SUPABASE_KEY")
    supabase_service_role_key: str | None = Field(
        default=None,
        validation_alias="SUPABASE_SERVICE_ROLE_KEY",
    )
    ips_routes_json: str = Field(default="{}", validation_alias="IPS_ROUTES_JSON")
    ips_timeout_seconds: float = Field(default=10, validation_alias="IPS_TIMEOUT_SECONDS", gt=0)
    nats_enabled: bool = Field(default=False, validation_alias="NATS_ENABLED")
    nats_url: str = Field(default="nats://localhost:4222", validation_alias="NATS_URL")
    nats_subject_prefix: str = Field(
        default="medix.appointments",
        validation_alias="NATS_SUBJECT_PREFIX",
    )
    nats_queue_group: str = Field(default="medix-api", validation_alias="NATS_QUEUE_GROUP")
    nats_connect_timeout_seconds: float = Field(
        default=2,
        validation_alias="NATS_CONNECT_TIMEOUT_SECONDS",
        gt=0,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
