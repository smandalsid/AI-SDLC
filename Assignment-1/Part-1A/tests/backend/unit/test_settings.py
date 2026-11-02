import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def load_settings() -> Settings:
    return Settings(_env_file=None)


def test_loads_required_values_from_the_environment() -> None:
    settings = load_settings()

    assert (settings.db_name, settings.db_user) == ("unit_db", "unit_user")
    assert settings.db_password.get_secret_value() == "unit-password-123"


@pytest.mark.parametrize("name", ["DB_NAME", "DB_USER", "DB_PASSWORD"])
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
