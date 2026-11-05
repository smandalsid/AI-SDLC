"""Settings are the only reader of the environment and never expose secrets."""

import pytest
from pydantic import ValidationError

from app.api.main import create_app
from app.settings import Settings

pytestmark = pytest.mark.covers("GR-4")

ENV_NAMES = (
    "MODEL_ID",
    "REASONING_EFFORT",
    "SDK_TIMEOUT_SECONDS",
    "REQUEST_BODY_MAX_BYTES",
    "CORS_ORIGINS",
    "LOG_LEVEL",
    "GH_TOKEN",
    "COPILOT_GITHUB_TOKEN",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.model_id == "gpt-6-luna"
    assert settings.reasoning_effort == "low"
    assert settings.sdk_timeout_seconds == 60
    assert settings.request_body_max_bytes == 1048576
    assert settings.cors_origin_list == []


def test_environment_overrides_the_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDK_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("MODEL_ID", "other-model")
    settings = Settings(_env_file=None)
    assert settings.sdk_timeout_seconds == 45 and settings.model_id == "other-model"


@pytest.mark.parametrize(
    ("name", "value"),
    [("REASONING_EFFORT", "turbo"), ("SDK_TIMEOUT_SECONDS", "0"), ("REQUEST_BODY_MAX_BYTES", "-1")],
)
def test_invalid_values_fail_at_construction(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_tokens_never_appear_in_repr_or_dump(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GH_TOKEN", "tok-secret-value-1")
    monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "tok-secret-value-2")
    settings = Settings(_env_file=None)
    assert "tok-secret-value" not in repr(settings)
    assert "tok-secret-value" not in str(settings.model_dump())
    assert settings.secret_values() == ["tok-secret-value-1", "tok-secret-value-2"]


def test_cors_origins_are_split_and_trimmed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
    assert Settings(_env_file=None).cors_origin_list == ["http://a.test", "http://b.test"]


def test_the_app_factory_builds_settings_at_startup_so_bad_config_fails_fast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REASONING_EFFORT", "turbo")
    with pytest.raises(ValidationError):
        create_app()
