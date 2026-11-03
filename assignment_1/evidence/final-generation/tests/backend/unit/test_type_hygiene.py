"""Constitution III: `Any` and `# type: ignore` need a one-line justification comment."""

import io
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCANNED = (ROOT / "src" / "backend" / "app", ROOT / "tests" / "backend")
IGNORE_MARKER = re.compile(r"#\s*type:\s*ignore(\[[^\]]*\])?")


def has_reason(comment: str) -> bool:
    """A comment justifies when text remains after removing the ignore marker itself."""
    remainder = IGNORE_MARKER.sub("", comment).replace("#", "")
    return re.search(r"[A-Za-z]{3,}", remainder) is not None


def unjustified_lines(source: str) -> list[int]:
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    comments = {t.start[0]: t.string for t in tokens if t.type == tokenize.COMMENT}
    own_line = {
        t.start[0] for t in tokens if t.type == tokenize.COMMENT and t.line.lstrip()[0] == "#"
    }

    def justified(line: int, same_line_counts: bool) -> bool:
        if same_line_counts and has_reason(comments.get(line, "")):
            return True
        previous = comments.get(line - 1, "")
        return line - 1 in own_line and has_reason(previous) and not IGNORE_MARKER.search(previous)

    flagged: set[int] = set()
    in_import = False
    at_start = True
    for token in tokens:
        if token.type == tokenize.COMMENT:
            if IGNORE_MARKER.search(token.string) and not justified(token.start[0], True):
                flagged.add(token.start[0])
        elif token.type in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT):
            at_start = at_start or token.type == tokenize.NEWLINE
            in_import = in_import and token.type != tokenize.NEWLINE
        else:
            if at_start:
                in_import = token.string in ("from", "import")
                at_start = False
            is_any = token.type == tokenize.NAME and token.string == "Any" and not in_import
            if is_any and not justified(token.start[0], True):
                flagged.add(token.start[0])
    return sorted(flagged)


def test_any_without_a_comment_is_flagged() -> None:
    assert unjustified_lines("x: Any = 1\n") == [1]


def test_any_with_a_same_line_comment_passes() -> None:
    assert unjustified_lines("x: Any = 1  # JSON payload of unknown shape\n") == []


def test_any_with_a_comment_on_the_preceding_line_passes() -> None:
    assert unjustified_lines("# JSON payload of unknown shape\nx: Any = 1\n") == []


def test_a_comment_two_lines_above_does_not_count() -> None:
    assert unjustified_lines("# JSON payload\n\nx: Any = 1\n") == [3]


def test_imports_of_any_are_not_usages() -> None:
    source = "from typing import Any\nfrom typing import (\n    Annotated,\n    Any,\n)\n"

    assert unjustified_lines(source) == []


def test_any_inside_strings_and_comments_is_ignored() -> None:
    assert unjustified_lines('x = "Any"  \n# Any here\n') == []


def test_a_bare_type_ignore_is_flagged() -> None:
    assert unjustified_lines("x = f()  # type: ignore\n") == [1]
    assert unjustified_lines("x = f()  # type: ignore[no-untyped-call]\n") == [1]


def test_a_type_ignore_with_a_reason_passes() -> None:
    same = "x = f()  # type: ignore[no-untyped-call]  # the library ships no stubs\n"
    above = "# the library ships no stubs\nx = f()  # type: ignore[no-untyped-call]\n"

    assert unjustified_lines(same) == []
    assert unjustified_lines(above) == []


def test_every_any_and_type_ignore_in_the_codebase_is_justified() -> None:
    offenders = [
        f"{path.relative_to(ROOT)}:{line}"
        for directory in SCANNED
        for path in sorted(directory.rglob("*.py"))
        for line in unjustified_lines(path.read_text(encoding="utf-8"))
    ]

    assert offenders == []
