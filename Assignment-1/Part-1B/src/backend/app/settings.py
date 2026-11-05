"""Typed configuration: the single place the environment is read (Principle VII)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    model_id: str = "mai-code-1.1-flash"
    reasoning_effort: Literal["low", "medium", "high"] = "low"
    sdk_timeout_seconds: int = Field(default=60, gt=0)
    request_body_max_bytes: int = Field(default=1_048_576, gt=0)
    cors_origins: str = ""
    log_level: str = "INFO"
    gh_token: SecretStr | None = None
    copilot_github_token: SecretStr | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def secret_values(self) -> list[str]:
        """Non-empty secret values, used only to detect leaks."""
        tokens = (self.gh_token, self.copilot_github_token)
        return [t.get_secret_value() for t in tokens if t is not None and t.get_secret_value()]

    def token_value(self) -> str | None:
        values = [self.copilot_github_token, self.gh_token]
        return next((t.get_secret_value() for t in values if t and t.get_secret_value()), None)
