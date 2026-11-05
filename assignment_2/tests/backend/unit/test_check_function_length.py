"""Function length gate (MEC-9)."""

from pathlib import Path

import pytest

from check_function_length import find_long_functions, main

pytestmark = pytest.mark.covers("MEC-9")


def _source(name: str, lines: int, prefix: str = "") -> str:
    body = "\n".join(f"{prefix}    x = {i}" for i in range(lines - 1))
    return f"{prefix}def {name}():\n{body}\n"


def test_a_41_line_function_fails_and_a_40_line_function_passes(tmp_path: Path) -> None:
    long_file = tmp_path / "long.py"
    long_file.write_text(_source("too_long", 41))
    ok_file = tmp_path / "ok.py"
    ok_file.write_text(_source("just_right", 40))
    found = find_long_functions(long_file, 40)
    assert [(v.name, v.length) for v in found] == [("too_long", 41)]
    assert find_long_functions(ok_file, 40) == []


def test_methods_and_async_functions_are_measured(tmp_path: Path) -> None:
    file = tmp_path / "cls.py"
    file.write_text(
        "class A:\n"
        + _source("m", 41, "    ")
        + "\nasync def a():\n"
        + "\n".join("    x = 1" for _ in range(45))
        + "\n"
    )
    names = {v.name for v in find_long_functions(file, 40)}
    assert names == {"m", "a"}


def test_main_prints_the_offender_and_returns_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = tmp_path / "long.py"
    file.write_text(_source("too_long", 41))
    assert main(["--limit", "40", str(file)]) == 1
    out = capsys.readouterr().out
    assert "too_long" in out and "41" in out


def test_main_returns_zero_for_short_functions(tmp_path: Path) -> None:
    file = tmp_path / "ok.py"
    file.write_text(_source("fine", 5))
    assert main(["--limit", "40", str(file)]) == 0


def test_main_reads_the_limit_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file = tmp_path / "f.py"
    file.write_text(_source("f", 12))
    monkeypatch.setenv("FUNC_LEN_MAX", "10")
    assert main([str(file)]) == 1
