from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    """The only place environment variables are read."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    db_name: str
    db_user: str
    db_password: SecretStr
    db_host: str = "localhost"
    db_port: int = 1433
    cors_origins: str = "http://localhost:5173"

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_origin(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins or "*" in origins:
            raise ValueError("CORS_ORIGINS must list explicit origins; a wildcard is not allowed")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def test_database_name(self) -> str:
        return f"{self.db_name}_test"

    def database_url(self, database: str) -> URL:
        return URL.create(
            "mssql+pymssql",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=database,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
