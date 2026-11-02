import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import LogCaptureFixture
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings

MARKER_HOST = "db-secret-host.internal"


def test_500_and_503_responses_and_logs_do_not_leak_secrets(
    app: FastAPI, client: TestClient, caplog: LogCaptureFixture
) -> None:
    settings = get_settings()
    password = settings.db_password.get_secret_value()
    url = settings.database_url(settings.db_name).render_as_string(hide_password=False)

    def unexpected() -> None:
        raise RuntimeError(f"connect failed {url} password={password}")

    def unreachable() -> None:
        raise OperationalError("SELECT 1", {}, Exception(f"cannot reach {MARKER_HOST}"))

    app.add_api_route("/__unexpected", unexpected)
    app.add_api_route("/__unreachable", unreachable)
    caplog.set_level(logging.DEBUG)

    responses = [client.get("/__unexpected"), client.get("/__unreachable")]

    assert [response.status_code for response in responses] == [500, 503]
    everything = "\n".join([response.text for response in responses]) + caplog.text
    for secret in (password, url, MARKER_HOST):
        assert secret not in everything
