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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
