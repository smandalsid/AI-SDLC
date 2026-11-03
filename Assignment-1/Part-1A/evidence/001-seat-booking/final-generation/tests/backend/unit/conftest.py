import sys
from collections.abc import Iterator

import pytest

FAKE_ENV = {
    "DB_NAME": "unit_db",
    "DB_USER": "unit_user",
    "DB_PASSWORD": "unit-password-123",
    "DB_HOST": "localhost",
    "DB_PORT": "1433",
    "CORS_ORIGINS": "http://localhost:5173",
}


def clear_settings_cache() -> None:
    module = sys.modules.get("app.core.config")
    if module is not None:
        module.get_settings.cache_clear()


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Unit tests never read the real .env: settings come from fake environment variables."""
    for name, value in FAKE_ENV.items():
        monkeypatch.setenv(name, value)
    clear_settings_cache()
    yield
    clear_settings_cache()
