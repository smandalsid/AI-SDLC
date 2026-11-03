"""NFR-007: the build gate's bundle-size check (.harness/check_bundle_size.mjs) on a fake dist."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

CHECK = Path(__file__).resolve().parents[3] / ".harness" / "check_bundle_size.mjs"
KB = 1024


def write_dist(root: Path, script_bytes: int, *, with_script: bool = True) -> None:
    dist = root / "src" / "frontend" / "dist"
    (dist / "assets").mkdir(parents=True)
    tag = '<script type="module" src="/assets/app.js"></script>' if with_script else ""
    (dist / "index.html").write_text(f"<html><head>{tag}</head></html>")
    # Random bytes do not compress, so the gzipped size is about the raw size.
    (dist / "assets" / "app.js").write_bytes(os.urandom(script_bytes))


def run_check(root: Path, limit_kb: str | None) -> subprocess.CompletedProcess[str]:
    node = shutil.which("node")
    assert node is not None, "node is required for the frontend build gate"
    env = {"PATH": os.environ["PATH"]}
    if limit_kb is not None:
        env["BUNDLE_MAX_KB_GZIP"] = limit_kb
    # Runs this repository's own harness script on a temporary directory.
    return subprocess.run(  # noqa: S603
        [node, str(CHECK)], cwd=root, env=env, capture_output=True, text=True, timeout=60
    )


def test_a_bundle_under_the_limit_passes(tmp_path: Path) -> None:
    write_dist(tmp_path, 50 * KB)

    result = run_check(tmp_path, "200")

    assert result.returncode == 0, result.stderr
    assert "initial JS total" in result.stdout


def test_a_bundle_over_the_limit_fails(tmp_path: Path) -> None:
    write_dist(tmp_path, 250 * KB)

    result = run_check(tmp_path, "200")

    assert result.returncode == 1
    assert "budget exceeded" in result.stderr


def test_the_limit_is_exactly_the_configured_number(tmp_path: Path) -> None:
    write_dist(tmp_path, 120 * KB)

    assert run_check(tmp_path, "200").returncode == 0
    assert run_check(tmp_path, "100").returncode == 1


def test_an_index_without_scripts_fails(tmp_path: Path) -> None:
    write_dist(tmp_path, 1 * KB, with_script=False)

    result = run_check(tmp_path, "200")

    assert result.returncode == 1
    assert "no initial JS" in result.stderr


def test_a_missing_limit_is_an_error(tmp_path: Path) -> None:
    write_dist(tmp_path, 1 * KB)

    assert run_check(tmp_path, None).returncode == 2


def test_a_missing_build_is_an_error(tmp_path: Path) -> None:
    assert run_check(tmp_path, "200").returncode == 2


@pytest.mark.parametrize("limit", ["abc", "0", "-5"])
def test_an_unusable_limit_is_an_error(tmp_path: Path, limit: str) -> None:
    write_dist(tmp_path, 1 * KB)

    assert run_check(tmp_path, limit).returncode == 2
