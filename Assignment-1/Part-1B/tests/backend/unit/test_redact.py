"""Redaction of secrets in captured output (Principle VII)."""

from pathlib import Path

import pytest

from redact import find_secrets, main, redact_json, redact_text, secrets_from_env

pytestmark = pytest.mark.covers("MEC-15")

PAT = "ghp_" + "A" * 36
FINE = "github_pat_" + "B" * 30


def test_token_shaped_strings_are_redacted() -> None:
    text = f"token {PAT} and {FINE} end"
    out = redact_text(text)
    assert PAT not in out and FINE not in out and out.count("<redacted>") == 2


def test_authorization_header_is_redacted() -> None:
    out = redact_text("Authorization: Bearer abc.def.ghi\nnext")
    assert "abc.def.ghi" not in out and "next" in out


def test_values_of_configured_secrets_are_redacted() -> None:
    secrets = secrets_from_env(
        {"GH_TOKEN": "s3cret-value-1", "COPILOT_GITHUB_TOKEN": "", "OTHER": "x"}
    )
    assert secrets == ["s3cret-value-1"]
    assert redact_text("key=s3cret-value-1;", secrets) == "key=<redacted>;"


def test_benign_text_is_unchanged() -> None:
    text = "remind me to pay rent next Monday at 9am"
    assert redact_text(text) == text


def test_json_values_are_redacted_recursively() -> None:
    data = {"a": [PAT, {"b": f"x {PAT}"}], "n": 3}
    out = redact_json(data)
    assert PAT not in str(out) and out["n"] == 3


def test_find_secrets_reports_matches() -> None:
    assert find_secrets(f"x {PAT}") == [PAT]
    assert find_secrets("nothing here") == []


def test_scan_exits_nonzero_when_a_file_holds_a_secret(tmp_path: Path) -> None:
    (tmp_path / "ok.txt").write_text("clean")
    assert main(["--scan", str(tmp_path)]) == 0
    (tmp_path / "bad.txt").write_text(f"oops {PAT}")
    assert main(["--scan", str(tmp_path)]) == 1


def test_filter_mode_masks_stdin(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(f"a {PAT} b\n"))
    assert main([]) == 0
    assert capsys.readouterr().out == "a <redacted> b\n"
