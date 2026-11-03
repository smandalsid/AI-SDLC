"""scripts/dev.sh decision logic, exercised with stub `docker` and `colima` commands on PATH."""

import os
import signal
import socket
import subprocess
import sys
from collections.abc import Iterator
from contextlib import closing, suppress
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEV_SH = ROOT / "scripts" / "dev.sh"
SECRET = "S3cret-pass-for-tests"
STATE_CHANGING = ("rm", "stop", "kill", "restart", "compose up", "run", "start")

DOCKER_STUB = r"""#!/usr/bin/env bash
echo "docker $*" >> "$STUB_DIR/calls.log"
state() { cat "$STUB_DIR/$1" 2>/dev/null || echo "$2"; }
listen() {
  "$STUB_PYTHON" -c '
import socket, sys, time
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", int(sys.argv[1]))); s.listen(); time.sleep(6)' "$STUB_PORT" \
    >/dev/null 2>&1 &
  echo $! >> "$STUB_DIR/listeners.pid"
}
case "$1" in
  info) [ "$(state daemon up)" = up ] ;;
  inspect)
    c="$(state container none)"
    [ "$c" = none ] && exit 1
    if [ "${2:-}" = "-f" ]; then [ "$c" = running ] && echo true || echo false; fi ;;
  compose)
    if [ "$2" = version ]; then [ "$(state compose no)" = yes ]; exit $?; fi
    echo running > "$STUB_DIR/container"; listen ;;
  start|run) echo running > "$STUB_DIR/container"; listen ;;
  *) exit 0 ;;
esac
"""
COLIMA_STUB = """#!/usr/bin/env bash
echo "colima $*" >> "$STUB_DIR/calls.log"
[ "$(cat "$STUB_DIR/colima_works" 2>/dev/null || echo yes)" = yes ] && echo up > "$STUB_DIR/daemon"
exit 0
"""


@dataclass
class Sandbox:
    directory: Path
    port: int

    def set_state(self, **values: str) -> None:
        for name, value in values.items():
            (self.directory / name).write_text(value)

    def calls(self) -> list[str]:
        log = self.directory / "calls.log"
        return log.read_text().splitlines() if log.exists() else []

    def run(self, *args: str, wait_seconds: int = 1) -> subprocess.CompletedProcess[str]:
        env = {
            "PATH": f"{self.directory / 'bin'}:/usr/bin:/bin",
            "HOME": str(self.directory),
            "ENV_FILE": str(self.directory / "env"),
            "STUB_DIR": str(self.directory),
            "STUB_PYTHON": sys.executable,
            "STUB_PORT": str(self.port),
            "DB_WAIT_SECONDS": str(wait_seconds),
        }
        # Runs this repository's own script with test-controlled arguments.
        return subprocess.run(  # noqa: S603
            ["/bin/bash", str(DEV_SH), *args], env=env, capture_output=True, text=True, timeout=60
        )

    def occupy_port(self) -> socket.socket:
        listener = socket.socket()
        listener.bind(("127.0.0.1", self.port))
        listener.listen()
        return listener


def free_port() -> int:
    with closing(socket.socket()) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture
def sandbox(tmp_path: Path) -> Iterator[Sandbox]:
    port = free_port()
    (tmp_path / "bin").mkdir()
    for name, body in (("docker", DOCKER_STUB), ("colima", COLIMA_STUB)):
        stub = tmp_path / "bin" / name
        stub.write_text(body)
        stub.chmod(0o755)
    (tmp_path / "env").write_text(
        f"DB_NAME=bus_db\nDB_USER=sa\nDB_PASSWORD={SECRET}\nDB_HOST=127.0.0.1\nDB_PORT={port}\n"
    )
    yield Sandbox(tmp_path, port)
    pids = tmp_path / "listeners.pid"
    for pid in pids.read_text().split() if pids.exists() else []:
        with suppress(ProcessLookupError):
            os.kill(int(pid), signal.SIGTERM)


def assert_never_destroys(box: Sandbox) -> None:
    joined = [call.removeprefix("docker ") for call in box.calls()]
    assert not [call for call in joined if call.split()[0] in ("rm", "stop", "kill", "restart")]


def assert_read_only(box: Sandbox) -> None:
    changed = [c for c in box.calls() if c.removeprefix("docker ").startswith(STATE_CHANGING)]
    assert changed == [], "a read-only run must not change anything"
    assert not any(call.startswith("colima") for call in box.calls())


@pytest.mark.parametrize(
    ("setup", "branch"),
    [
        ({"daemon": "down"}, "start-docker-daemon"),
        ({"container": "running"}, "reuse-running"),
        ({"container": "stopped"}, "start-stopped"),
        ({}, "create"),
    ],
)
def test_check_reports_the_branch_without_acting(
    sandbox: Sandbox, setup: dict[str, str], branch: str
) -> None:
    sandbox.set_state(**setup)
    listener = sandbox.occupy_port() if branch == "reuse-running" else None
    try:
        result = sandbox.run("--check")
    finally:
        if listener is not None:
            listener.close()

    assert result.returncode == 0, result.stderr
    assert f"branch: {branch}" in result.stdout
    assert_read_only(sandbox)


def test_check_reports_a_running_container_whose_port_is_not_ready(sandbox: Sandbox) -> None:
    sandbox.set_state(container="running")

    result = sandbox.run("--check")

    assert "branch: wait-for-running" in result.stdout
    assert_read_only(sandbox)


def test_check_names_the_creation_method(sandbox: Sandbox) -> None:
    assert "docker run" in sandbox.run("--check").stdout
    sandbox.set_state(compose="yes")

    assert "docker compose up" in sandbox.run("--check").stdout


def test_check_fails_when_a_foreign_process_holds_the_port(sandbox: Sandbox) -> None:
    listener = sandbox.occupy_port()
    try:
        result = sandbox.run("--check")
    finally:
        listener.close()

    assert result.returncode == 1
    assert "branch: port-conflict" in result.stdout
    assert str(sandbox.port) in result.stdout + result.stderr
    assert_read_only(sandbox)


def test_a_running_reachable_container_is_reused_untouched(sandbox: Sandbox) -> None:
    sandbox.set_state(container="running")
    listener = sandbox.occupy_port()
    try:
        result = sandbox.run("--db-only")
    finally:
        listener.close()

    assert result.returncode == 0, result.stderr
    assert "database already running, reusing it" in result.stdout
    assert_read_only(sandbox)


def test_a_stopped_docker_daemon_is_started_through_colima(sandbox: Sandbox) -> None:
    sandbox.set_state(daemon="down", container="running")
    listener = sandbox.occupy_port()
    try:
        result = sandbox.run("--db-only")
    finally:
        listener.close()

    assert result.returncode == 0, result.stderr
    assert "colima start" in sandbox.calls()
    assert "database already running, reusing it" in result.stdout


def test_it_fails_clearly_when_colima_cannot_bring_docker_up(sandbox: Sandbox) -> None:
    sandbox.set_state(daemon="down", colima_works="no")

    result = sandbox.run("--db-only")

    assert result.returncode != 0
    assert "Docker daemon" in result.stdout + result.stderr
    assert_never_destroys(sandbox)


def test_a_running_container_that_never_opens_its_port_times_out(sandbox: Sandbox) -> None:
    sandbox.set_state(container="running")

    result = sandbox.run("--db-only", wait_seconds=1)

    assert result.returncode != 0
    assert "did not accept connections" in result.stdout + result.stderr
    assert_read_only(sandbox)


def test_a_stopped_container_is_started_not_recreated(sandbox: Sandbox) -> None:
    sandbox.set_state(container="stopped")

    result = sandbox.run("--db-only", wait_seconds=5)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "docker start azure-sql-edge" in sandbox.calls()
    assert not any(call.startswith("docker run") for call in sandbox.calls())
    assert_never_destroys(sandbox)


def test_a_foreign_listener_on_the_port_blocks_creation(sandbox: Sandbox) -> None:
    listener = sandbox.occupy_port()
    try:
        result = sandbox.run("--db-only")
    finally:
        listener.close()

    assert result.returncode != 0
    assert str(sandbox.port) in result.stdout + result.stderr
    assert_read_only(sandbox)


@pytest.mark.parametrize("compose", ["no", "yes"])
def test_a_missing_container_is_created_without_the_password_on_the_command_line(
    sandbox: Sandbox, compose: str
) -> None:
    sandbox.set_state(compose=compose)

    result = sandbox.run("--db-only", wait_seconds=5)

    assert result.returncode == 0, result.stdout + result.stderr
    creation = "docker compose up -d" if compose == "yes" else "docker run"
    assert any(call.startswith(creation) for call in sandbox.calls())
    assert SECRET not in "\n".join(sandbox.calls())
    assert SECRET not in result.stdout + result.stderr
    assert_never_destroys(sandbox)


def test_docker_run_publishes_the_port_and_passes_the_secret_by_name(sandbox: Sandbox) -> None:
    sandbox.run("--db-only", wait_seconds=5)

    command = next(call for call in sandbox.calls() if call.startswith("docker run"))
    assert "-e ACCEPT_EULA=1" in command
    assert "-e MSSQL_SA_PASSWORD " in command + " "
    assert "MSSQL_SA_PASSWORD=" not in command
    assert f"-p {sandbox.port}:1433" in command
    assert "mcr.microsoft.com/azure-sql-edge" in command


def test_an_unknown_flag_is_rejected(sandbox: Sandbox) -> None:
    result = sandbox.run("--bogus")

    assert result.returncode == 2
    assert "usage" in (result.stdout + result.stderr).lower()
