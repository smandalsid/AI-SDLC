from pathlib import Path

import pytest

from .harness_loader import load_harness_module


def write_function(path: Path, name: str, body_lines: int) -> None:
    body = "\n".join("    x = 1" for _ in range(body_lines))
    path.write_text(f"def {name}() -> None:\n{body}\n", encoding="utf-8")


def run_check(source_dir: Path, limit: str = "40") -> int:
    module = load_harness_module("check_function_length")
    code: int = module.main([str(source_dir)], {"FUNCTION_MAX_LINES": limit})
    return code


def test_function_of_41_lines_fails_and_is_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_function(tmp_path / "long_module.py", "too_long", 40)  # def line + 40 body = 41 lines

    code = run_check(tmp_path)

    output = capsys.readouterr().out
    assert code == 1
    assert "too_long" in output
    assert "41" in output
    assert "long_module.py" in output


def test_function_of_40_lines_passes(tmp_path: Path) -> None:
    write_function(tmp_path / "ok_module.py", "just_fits", 39)  # def line + 39 body = 40 lines

    assert run_check(tmp_path) == 0


def test_missing_limit_is_an_error(tmp_path: Path) -> None:
    module = load_harness_module("check_function_length")
    code: int = module.main([str(tmp_path)], {})
    assert code == 2


def test_methods_and_nested_functions_are_checked(tmp_path: Path) -> None:
    body = "\n".join("        x = 1" for _ in range(41))
    (tmp_path / "cls.py").write_text(
        f"class Service:\n    def run(self) -> None:\n{body}\n", encoding="utf-8"
    )

    assert run_check(tmp_path) == 1
