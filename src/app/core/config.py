from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Snack Builders Bakery API"
    environment: str = "development"

    log_level: str = "INFO"
    log_json: bool = True

    otel_enabled: bool = False
    otel_service_name: str = ""
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_headers: str = ""

    postgres_user: str = "bakery"
    postgres_password: str = ""
    postgres_db: str = "bakery"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
