import pytest
from app.core.config import Settings
from app.core.passwords import Argon2Hasher
from app.db import seed
from app.db.seed import MissingMockPasswordError, password_hashes_from_settings
from pydantic import SecretStr

USERNAMES = ["asha", "ravi", "meera"]
PASSWORDS = {
    "asha": SecretStr("pw-for-asha-unit-1"),
    "ravi": SecretStr("pw-for-ravi-unit-2"),
    "meera": SecretStr("pw-for-meera-unit-3"),
}


@pytest.fixture
def hasher() -> Argon2Hasher:
    return Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1)


def test_seeded_usernames_are_asha_ravi_and_meera() -> None:
    assert [user["username"] for user in seed.USERS] == USERNAMES
    assert [user["id"] for user in seed.USERS] == [1, 2, 3]


def test_every_seeded_user_gets_a_hash_that_verifies_with_its_password(
    hasher: Argon2Hasher,
) -> None:
    hashes = password_hashes_from_settings(PASSWORDS, USERNAMES, hasher)

    assert list(hashes) == USERNAMES
    for username in USERNAMES:
        assert hasher.verify(hashes[username], PASSWORDS[username].get_secret_value())
        assert PASSWORDS[username].get_secret_value() not in hashes[username]


def test_a_missing_entry_names_only_the_usernames(hasher: Argon2Hasher) -> None:
    passwords = {"asha": PASSWORDS["asha"]}

    with pytest.raises(MissingMockPasswordError) as raised:
        password_hashes_from_settings(passwords, USERNAMES, hasher)

    message = str(raised.value)
    assert "ravi" in message and "meera" in message and "asha" not in message
    assert PASSWORDS["asha"].get_secret_value() not in message


def test_extra_usernames_in_the_map_are_ignored(hasher: Argon2Hasher) -> None:
    passwords = {**PASSWORDS, "zed": SecretStr("pw-for-zed-unit-4")}

    assert list(password_hashes_from_settings(passwords, USERNAMES, hasher)) == USERNAMES


def test_seed_cli_exits_non_zero_and_prints_no_password_when_an_entry_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MOCK_USER_PASSWORDS", '{"asha": "pw-for-asha-unit-1"}')
    # The real .env must not leak in: dict settings are merged across sources.
    monkeypatch.setattr(seed, "get_settings", lambda: Settings(_env_file=None))

    exit_code = seed.main(["--database", "unused_test"])

    output = capsys.readouterr()
    assert exit_code == 2
    assert "ravi" in output.err + output.out and "meera" in output.err + output.out
    assert "pw-for-asha-unit-1" not in output.err + output.out
