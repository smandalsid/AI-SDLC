import json
from datetime import timedelta

import pytest
from app.core.config import AuthPolicy, Settings, get_settings
from pydantic import ValidationError

from .conftest import FAKE_ENV


def load_settings() -> Settings:
    return Settings(_env_file=None)


def test_loads_required_values_from_the_environment() -> None:
    settings = load_settings()

    assert (settings.db_name, settings.db_user) == ("unit_db", "unit_user")
    assert settings.db_password.get_secret_value() == "unit-password-123"


@pytest.mark.parametrize("name", ["DB_NAME", "DB_USER", "DB_PASSWORD", "JWT_SECRET"])
def test_missing_required_variable_fails_at_construction(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.delenv(name)

    with pytest.raises(ValidationError):
        load_settings()


def test_host_and_port_have_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DB_HOST")
    monkeypatch.delenv("DB_PORT")

    settings = load_settings()

    assert (settings.db_host, settings.db_port) == ("localhost", 1433)


def test_password_never_appears_in_repr_str_or_database_url_text() -> None:
    settings = load_settings()
    secret = settings.db_password.get_secret_value()
    url = settings.database_url("bus_db")

    for text in (repr(settings), str(settings), str(url), repr(url)):
        assert secret not in text
    assert url.password == secret


def test_database_url_targets_the_requested_database() -> None:
    url = load_settings().database_url("bus_db")

    assert (url.drivername, url.username, url.host, url.port, url.database) == (
        "mssql+pymssql",
        "unit_user",
        "localhost",
        1433,
        "bus_db",
    )


def test_test_database_name_is_derived_from_the_database_name() -> None:
    assert load_settings().test_database_name == "unit_db_test"


@pytest.mark.parametrize("value", ["*", "http://localhost:5173,*"])
def test_wildcard_cors_origin_is_rejected(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("CORS_ORIGINS", value)

    with pytest.raises(ValidationError):
        load_settings()


def test_cors_origins_are_a_comma_separated_list(monkeypatch: pytest.MonkeyPatch) -> None:
    assert load_settings().cors_origin_list == ["http://localhost:5173"]

    monkeypatch.setenv("CORS_ORIGINS", "http://a.example, http://b.example")

    assert load_settings().cors_origin_list == ["http://a.example", "http://b.example"]


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()


def test_jwt_secret_is_loaded_and_hidden_from_repr_and_str() -> None:
    settings = load_settings()
    secret = settings.jwt_secret.get_secret_value()

    assert secret == FAKE_ENV["JWT_SECRET"]
    for text in (repr(settings), str(settings)):
        assert secret not in text


def test_jwt_secret_needs_at_least_32_characters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "s" * 31)
    with pytest.raises(ValidationError):
        load_settings()

    monkeypatch.setenv("JWT_SECRET", "s" * 32)
    assert len(load_settings().jwt_secret.get_secret_value()) == 32


def test_mock_user_passwords_are_optional_and_default_to_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MOCK_USER_PASSWORDS")

    assert load_settings().mock_user_passwords == {}


def test_mock_user_passwords_parse_a_json_map_and_hide_their_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    passwords = {"asha": "pw-for-asha-1", "ravi": "pw-for-ravi-2"}
    monkeypatch.setenv("MOCK_USER_PASSWORDS", json.dumps(passwords))

    settings = load_settings()

    assert {
        name: value.get_secret_value() for name, value in settings.mock_user_passwords.items()
    } == (passwords)
    for text in (repr(settings), str(settings)):
        assert all(value not in text for value in passwords.values())


@pytest.mark.parametrize(
    "raw", ["{not json", '["a"]', '{"asha": ""}', json.dumps({"asha": "p" * 129})]
)
def test_mock_user_passwords_reject_bad_values(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("MOCK_USER_PASSWORDS", raw)

    with pytest.raises(ValueError):
        load_settings()


def test_mock_user_password_of_128_characters_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOCK_USER_PASSWORDS", json.dumps({"asha": "p" * 128}))

    assert len(load_settings().mock_user_passwords["asha"].get_secret_value()) == 128


def test_auth_policy_defaults_match_the_spec() -> None:
    policy = load_settings().auth_policy

    assert policy == AuthPolicy(
        session_lifetime=timedelta(minutes=30),
        max_failures=5,
        failure_window=timedelta(minutes=5),
        lockout=timedelta(seconds=60),
    )


def test_auth_policy_can_be_overridden_by_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGIN_MAX_FAILURES", "3")
    monkeypatch.setenv("SESSION_LIFETIME_MINUTES", "10")

    policy = load_settings().auth_policy

    assert (policy.max_failures, policy.session_lifetime) == (3, timedelta(minutes=10))
