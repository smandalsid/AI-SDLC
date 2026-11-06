"""`.harness/redact.sh` masks every secret kept in .env (fake values in a temporary env file)."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
REDACT_SH = ROOT / ".harness" / "redact.sh"

SECRETS = {
    "DB_PASSWORD": "fake-db-pass-for-redact-test",
    "JWT_SECRET": "fake-jwt-secret-for-redact-test-0123456789",
    "MOCK_PASSWORD_ASHA": "fake-asha-pw-1",
    "MOCK_PASSWORD_RAVI": "fake-ravi-pw-2",
    "MOCK_PASSWORD_MEERA": "fake-meera-pw-3",
}
ENV_TEXT = (
    f"DB_NAME=bus_db\nDB_USER=sa\nDB_PASSWORD={SECRETS['DB_PASSWORD']}\n"
    f"JWT_SECRET={SECRETS['JWT_SECRET']}\n"
    'MOCK_USER_PASSWORDS={"asha":"%s","ravi":"%s","meera":"%s"}\n'
    % (SECRETS["MOCK_PASSWORD_ASHA"], SECRETS["MOCK_PASSWORD_RAVI"], SECRETS["MOCK_PASSWORD_MEERA"])
)


def redact(text: str, env_file: Path) -> str:
    result = subprocess.run(  # noqa: S603 - fixed script path, test input only
        ["bash", str(REDACT_SH)],  # noqa: S607
        input=text,
        capture_output=True,
        text=True,
        env={"REDACT_ENV_FILE": str(env_file), "PATH": "/usr/bin:/bin"},
        check=True,
    )
    return result.stdout


def assert_masked(output: str, names: list[str]) -> None:
    """Fails with the secret's name only, so a failing run never prints a value."""
    leaked = [name for name in names if SECRETS[name] in output]
    if leaked:
        pytest.fail(f"not redacted: {', '.join(leaked)}")


@pytest.fixture
def env_file(tmp_path: Path) -> Path:
    path = tmp_path / "env"
    path.write_text(ENV_TEXT, encoding="utf-8")
    return path


def test_db_password_is_masked(env_file: Path) -> None:
    output = redact(f"connect with {SECRETS['DB_PASSWORD']} now\n", env_file)
    assert_masked(output, ["DB_PASSWORD"])
    assert "<redacted>" in output


def test_jwt_secret_is_masked(env_file: Path) -> None:
    output = redact(f"token key {SECRETS['JWT_SECRET']} leaked\n", env_file)
    assert_masked(output, ["JWT_SECRET"])
    assert "<redacted>" in output


def test_every_mock_password_is_masked(env_file: Path) -> None:
    names = ["MOCK_PASSWORD_ASHA", "MOCK_PASSWORD_RAVI", "MOCK_PASSWORD_MEERA"]
    text = "".join(f"user pw {SECRETS[name]}\n" for name in names)
    output = redact(text, env_file)
    assert_masked(output, names)
    assert output.count("<redacted>") == len(names)


def test_all_secrets_on_one_line_are_masked(env_file: Path) -> None:
    output = redact(" ".join(SECRETS.values()) + "\n", env_file)
    assert_masked(output, list(SECRETS))


def test_longer_password_containing_a_shorter_one_leaves_no_remainder(tmp_path: Path) -> None:
    path = tmp_path / "env"
    path.write_text('MOCK_USER_PASSWORDS={"a":"abcd","b":"abcdefgh"}\n', encoding="utf-8")
    assert redact("x abcdefgh y\n", path) == "x <redacted> y\n"


def test_unrelated_text_is_unchanged(env_file: Path) -> None:
    text = "PASSED 12 tests\nstatus 401 unauthenticated\n"
    assert redact(text, env_file) == text


def test_missing_env_file_passes_text_through(tmp_path: Path) -> None:
    text = "nothing to hide\n"
    assert redact(text, tmp_path / "does-not-exist") == text


def test_malformed_mock_password_json_does_not_break_other_masking(tmp_path: Path) -> None:
    path = tmp_path / "env"
    path.write_text(
        f"JWT_SECRET={SECRETS['JWT_SECRET']}\nMOCK_USER_PASSWORDS={{not json\n", encoding="utf-8"
    )
    output = redact(f"{SECRETS['JWT_SECRET']}\n", path)
    assert_masked(output, ["JWT_SECRET"])
