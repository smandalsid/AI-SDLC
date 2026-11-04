from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

ENV_FILE = Path(__file__).resolve().parents[4] / ".env"
MIN_JWT_SECRET_LENGTH = 32
MAX_PASSWORD_LENGTH = 128


@dataclass(frozen=True)
class AuthPolicy:
    session_lifetime: timedelta
    max_failures: int
    failure_window: timedelta
    lockout: timedelta


class Settings(BaseSettings):
    """The only place environment variables are read."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    db_name: str
    db_user: str
    db_password: SecretStr
    db_host: str = "localhost"
    db_port: int = 1433
    cors_origins: str = "http://localhost:5173"
    jwt_secret: SecretStr
    # Only the seed command needs these; the running API never reads them.
    mock_user_passwords: dict[str, SecretStr] = Field(default_factory=dict)
    session_lifetime_minutes: int = Field(default=30, ge=1)
    login_max_failures: int = Field(default=5, ge=1)
    login_failure_window_minutes: int = Field(default=5, ge=1)
    login_lockout_seconds: int = Field(default=60, ge=1)

    @field_validator("jwt_secret")
    @classmethod
    def require_long_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(f"JWT_SECRET must have at least {MIN_JWT_SECRET_LENGTH} characters")
        return value

    @field_validator("mock_user_passwords")
    @classmethod
    def limit_password_length(cls, value: dict[str, SecretStr]) -> dict[str, SecretStr]:
        for username, password in value.items():
            if not 1 <= len(password.get_secret_value()) <= MAX_PASSWORD_LENGTH:
                raise ValueError(f"mock password for '{username}' must have 1 to 128 characters")
        return value

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

    @property
    def auth_policy(self) -> AuthPolicy:
        return AuthPolicy(
            session_lifetime=timedelta(minutes=self.session_lifetime_minutes),
            max_failures=self.login_max_failures,
            failure_window=timedelta(minutes=self.login_failure_window_minutes),
            lockout=timedelta(seconds=self.login_lockout_seconds),
        )

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
