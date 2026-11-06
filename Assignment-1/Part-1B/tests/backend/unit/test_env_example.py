"""`.env.example` lists every setting with placeholders only; `.env` is ignored (Principle VII)."""

from pathlib import Path

import pytest

from app.settings import Settings

pytestmark = pytest.mark.covers("GR-4")

ROOT = Path(__file__).resolve().parents[3]
SECRET_FIELDS = {"gh_token", "copilot_github_token"}


def _example() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            name, _, value = line.partition("=")
            values[name] = value
    return values


@pytest.mark.parametrize("field", sorted(Settings.model_fields))
def test_every_setting_has_its_variable_in_the_example(field: str) -> None:
    assert field.upper() in _example()


def test_the_example_lists_no_variable_the_settings_do_not_read() -> None:
    assert set(_example()) == {f.upper() for f in Settings.model_fields}


@pytest.mark.parametrize("field", sorted(SECRET_FIELDS))
def test_secret_values_in_the_example_are_empty_or_a_bracketed_placeholder(field: str) -> None:
    value = _example()[field.upper()]
    assert value == "" or (value.startswith("<") and value.endswith(">"))


def test_the_example_loads_into_valid_settings() -> None:
    values = {name.lower(): value for name, value in _example().items() if value}
    settings = Settings(_env_file=None, **values)  # type: ignore[arg-type]  # the values are strings that pydantic-settings parses
    assert settings.model_id and settings.secret_values() == []


def test_the_real_env_file_is_gitignored() -> None:
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in (line.strip() for line in lines)
