"""Every endpoint needs a success and a failure contract test; no unexplained skips."""

from pathlib import Path

import pytest

from check_endpoint_tests import main, missing_markers, skips_without_reason

pytestmark = pytest.mark.covers("MEC-20", "MEC-21")

OPENAPI = """openapi: 3.1.0
info: {title: t, version: '1'}
paths:
  /api/v1/actions:
    post: {responses: {'200': {description: ok}}}
  /api/v1/health:
    get: {responses: {'200': {description: ok}}}
"""

TEST_FILE = """import pytest

@pytest.mark.endpoint("POST", "/api/v1/actions", "success")
def test_a() -> None: ...

@pytest.mark.endpoint("POST", "/api/v1/actions", "failure")
def test_b() -> None: ...

@pytest.mark.endpoint("GET", "/api/v1/health", "success")
def test_c() -> None: ...
"""


FAILURE_TEST = (
    "import pytest\n\n"
    '@pytest.mark.endpoint("GET", "/api/v1/health", "failure")\n'
    "def test_d() -> None: ...\n"
)


def _setup(tmp_path: Path, tests: str) -> tuple[Path, Path]:
    spec = tmp_path / "openapi.yaml"
    spec.write_text(OPENAPI)
    tests_dir = tmp_path / "contract"
    tests_dir.mkdir()
    (tests_dir / "test_x.py").write_text(tests)
    return spec, tests_dir


def test_a_missing_failure_test_is_named(tmp_path: Path) -> None:
    spec, tests_dir = _setup(tmp_path, TEST_FILE)
    assert missing_markers(spec, tests_dir) == ["GET /api/v1/health failure"]


def test_all_markers_present_passes(tmp_path: Path) -> None:
    spec, tests_dir = _setup(
        tmp_path, TEST_FILE + "\n" + FAILURE_TEST.replace("import pytest\n\n", "")
    )
    assert missing_markers(spec, tests_dir) == []


def test_skips_need_a_documented_reason(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    skip = '<skipped type="pytest.skip" message="{}"/>'
    junit.write_text(
        "<testsuites><testsuite>"
        f'<testcase classname="a" name="t1">{skip.format("")}</testcase>'
        f'<testcase classname="a" name="t2">{skip.format("unconditional skip")}</testcase>'
        f'<testcase classname="a" name="t3">{skip.format("needs network")}</testcase>'
        "</testsuite></testsuites>"
    )
    assert skips_without_reason(junit) == ["a::t1", "a::t2"]


def test_main_fails_on_missing_markers_and_passes_when_complete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    spec, tests_dir = _setup(tmp_path, TEST_FILE)
    assert main(["--openapi", str(spec), "--tests-dir", str(tests_dir)]) == 1
    assert "GET /api/v1/health failure" in capsys.readouterr().out
    (tests_dir / "test_y.py").write_text(FAILURE_TEST)
    assert main(["--openapi", str(spec), "--tests-dir", str(tests_dir)]) == 0
