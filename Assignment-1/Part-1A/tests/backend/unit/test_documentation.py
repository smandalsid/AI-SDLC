import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLACEHOLDER = "change_me"
REQUIRED_NAMES = {
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "JWT_SECRET",
    "MOCK_USER_PASSWORDS",
}


def example_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            name, _, value = line.partition("=")
            values[name] = value
    return values


def test_the_example_environment_file_lists_the_names_with_placeholders_only() -> None:
    values = example_values()

    assert REQUIRED_NAMES <= set(values)
    assert values["JWT_SECRET"].startswith(PLACEHOLDER)
    assert values["DB_PASSWORD"].startswith(PLACEHOLDER)
    passwords = json.loads(values["MOCK_USER_PASSWORDS"])
    assert set(passwords) == {"asha", "ravi", "meera"}
    assert set(passwords.values()) == {PLACEHOLDER}


def test_the_real_environment_file_is_never_committed() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in ignored


def test_the_readme_documents_the_names_the_commands_and_the_rules() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for expected in (
        "JWT_SECRET",
        "MOCK_USER_PASSWORDS",
        "scripts/dev.sh",
        "scripts/db-init.sh",
        ".harness/run.sh",
        "Sign out",
        "30 minutes",
        "60 seconds",
        "asha",
        "ravi",
        "meera",
    ):
        assert expected in readme, expected
