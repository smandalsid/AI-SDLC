"""Constitution IX: every `Any` and `# type: ignore` carries a one-line justification."""

import io
import re
import tokenize
from pathlib import Path

import pytest

from harness_helpers import ROOT

pytestmark = pytest.mark.covers("GR-5")

SCANNED = (ROOT / "src/backend/app", ROOT / "tests/backend")
IMPORT_PREFIXES = ("from typing import", "from typing_extensions import")
IGNORE_WITH_REASON = re.compile(r"^#\s*type: ignore(\[[^\]]*\])?\s+#\s*\S")


def _justified(comment: str | None) -> bool:
    if comment is None:
        return False
    if "type: ignore" in comment:
        return bool(IGNORE_WITH_REASON.match(comment))
    return bool(comment.lstrip("# "))


def _offending_lines(path: Path) -> list[int]:
    tokens = list(tokenize.generate_tokens(io.StringIO(path.read_text()).readline))
    comments = {t.start[0]: t.string for t in tokens if t.type == tokenize.COMMENT}
    lines = set()
    for token in tokens:
        uses_any = token.type == tokenize.NAME and token.string == "Any"
        if uses_any and token.line.lstrip().startswith(IMPORT_PREFIXES):
            continue
        ignores = token.type == tokenize.COMMENT and "type: ignore" in token.string
        if (uses_any or ignores) and not _justified(comments.get(token.start[0])):
            lines.add(token.start[0])
    return sorted(lines)


def test_the_checker_accepts_justified_lines_and_rejects_bare_ones(tmp_path: Path) -> None:
    good = tmp_path / "good.py"
    good.write_text(
        "from typing import Any\n"
        "Json = dict[str, Any]  # parsed JSON has no static type\n"
        "x: int = 'a'  # type: ignore[assignment]  # deliberate\n"
    )
    bad = tmp_path / "bad.py"
    bad.write_text(
        "def f(a: Any) -> None: ...\n"
        "y: int = 'a'  # type: ignore[assignment]\n"
        "z: int = 'a'  # type: ignore\n"
    )
    assert _offending_lines(good) == []
    assert _offending_lines(bad) == [1, 2, 3]


def test_every_any_and_type_ignore_in_the_code_is_justified_on_its_line() -> None:
    offenders = [
        f"{path.relative_to(ROOT)}:{line}"
        for root in SCANNED
        for path in sorted(root.rglob("*.py"))
        for line in _offending_lines(path)
    ]
    assert offenders == []
