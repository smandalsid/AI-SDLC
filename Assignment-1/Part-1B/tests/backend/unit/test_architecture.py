"""Architecture rules enforced from the source tree (Principles VII, VIII, IX)."""

import ast
from pathlib import Path

import pytest

from harness_helpers import ROOT

pytestmark = pytest.mark.covers("GR-5", "GR-4")

APP = ROOT / "src" / "backend" / "app"
LAYER = {"models": 0, "llm": 1, "services": 2, "api": 3}
TOP = 4


def _modules() -> list[Path]:
    return sorted(p for p in APP.rglob("*.py") if "__pycache__" not in p.parts)


def _layer(path: Path) -> int | None:
    rel = path.relative_to(APP)
    if rel.name == "eval_adapter.py":
        return TOP
    return LAYER.get(rel.parts[0]) if len(rel.parts) > 1 else None


def _imports(path: Path) -> list[str]:
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def _layer_of_import(name: str) -> int | None:
    parts = name.split(".")
    if parts[0] != "app" or len(parts) < 2:
        return None
    if parts[1] == "eval_adapter":
        return TOP
    return LAYER.get(parts[1])


def test_layers_only_import_downwards() -> None:
    problems = []
    for path in _modules():
        own = _layer(path)
        if own is None:
            continue
        for name in _imports(path):
            target = _layer_of_import(name)
            if target is not None and target > own:
                problems.append(f"{path.relative_to(APP)} imports {name}")
    assert problems == []


def test_only_the_sdk_adapter_imports_copilot() -> None:
    offenders = [
        str(p.relative_to(APP))
        for p in _modules()
        if any(n.split(".")[0] == "copilot" for n in _imports(p))
    ]
    assert offenders == [str(Path("llm") / "copilot_client.py")]


def test_nothing_in_the_app_reads_the_environment() -> None:
    offenders = [
        str(p.relative_to(APP))
        for p in _modules()
        if "os.environ" in p.read_text() or "os.getenv" in p.read_text()
    ]
    assert offenders == []


def test_no_bare_or_blanket_exception_handlers() -> None:
    offenders = []
    for path in _modules():
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.ExceptHandler):
                continue
            blanket = node.type is None or (
                isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}
            )
            if blanket:
                offenders.append(f"{path.relative_to(APP)}:{node.lineno}")
    assert offenders == []


def test_routes_do_not_import_the_llm_layer_and_services_do_not_import_fastapi() -> None:
    routes = APP / "api" / "routes.py"
    assert not [n for n in _imports(routes) if n.startswith("app.llm")]
    for path in (APP / "services").glob("*.py"):
        assert not [n for n in _imports(path) if n.split(".")[0] in {"fastapi", "starlette"}]


def test_nothing_in_the_app_imports_the_eval_adapter() -> None:
    offenders = [
        str(p.relative_to(APP))
        for p in _modules()
        if p.name != "eval_adapter.py"
        and any(n.startswith("app.eval_adapter") for n in _imports(p))
    ]
    assert offenders == []
