"""LOG_LEVEL configures the app logger; one request logs its intent and operation only."""

import logging

import pytest
from app_helpers import FixedClock, create_dict
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.llm.stub_client import StubLLMClient
from app.settings import Settings

pytestmark = pytest.mark.covers("GR-4")

TITLE = "pay the confidential invoice"
REMINDER = {"id": "r1", "title": "Secret dentist visit", "time": "2026-11-06T10:00:00+00:00"}


def _app(level: str = "INFO") -> TestClient:
    app = create_app(
        settings=Settings(_env_file=None, log_level=level),
        llm_client=StubLLMClient(create_dict(title="pay rent")),
        clock=FixedClock(),
    )
    return TestClient(app)


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR"])
def test_the_log_level_setting_sets_the_app_logger_level(level: str) -> None:
    _app(level)
    assert logging.getLogger("app").level == getattr(logging, level)


def test_an_unknown_log_level_fails_at_startup() -> None:
    with pytest.raises(ValueError, match="LOUD"):
        _app("LOUD")


def test_one_request_logs_one_line_with_the_intent_and_the_operation(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = _app("INFO")
    caplog.set_level(logging.INFO)
    body = {"text": TITLE, "now": "2026-11-05T10:00:00+00:00", "reminders": [REMINDER]}
    assert client.post("/api/v1/actions", json=body).status_code == 200
    records = [r for r in caplog.records if r.name.startswith("app")]
    assert len(records) == 1 and records[0].levelno == logging.INFO
    message = records[0].getMessage()
    assert "intent=create" in message and "operation=created" in message
    for private in (TITLE, "pay rent", REMINDER["title"], "confidential"):
        assert private not in message


def test_a_warning_level_hides_the_request_line(caplog: pytest.LogCaptureFixture) -> None:
    client = _app("WARNING")
    caplog.set_level(logging.DEBUG)
    client.post("/api/v1/actions", json={"text": TITLE, "now": "2026-11-05T10:00:00+00:00"})
    assert [r for r in caplog.records if r.name.startswith("app")] == []
