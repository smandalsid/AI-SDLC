"""Tests never depend on the caller's environment: every setting starts unset."""

import pytest

from app.settings import Settings


@pytest.fixture(autouse=True)
def _unset_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for field in Settings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)
