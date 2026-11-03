"""AST scan of the backend package for layering and environment-access violations."""

import ast
from collections.abc import Iterator
from pathlib import Path

FORBIDDEN_IMPORTS: dict[str, set[str]] = {
    "models": {"repositories", "services", "api", "db"},
    "repositories": {"services", "api"},
    "services": {"api", "db"},
    "core": {"models", "repositories", "services", "api", "db"},
}
SETTINGS_MODULE = "core/config.py"


def imported_modules(tree: ast.AST, package: str, location: list[str]) -> Iterator[list[str]]:
    """Yield every imported module as an absolute dotted path split into parts."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")
        elif isinstance(node, ast.ImportFrom):
            base = node.module.split(".") if node.module else []
            if node.level:
                base = location[: len(location) - (node.level - 1)] + base
            if base == [package]:
                for alias in node.names:
                    yield [*base, alias.name]
            else:
                yield base


def reads_environment(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "os" and node.attr in {"environ", "getenv"}:
                return True
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            if any(alias.name in {"environ", "getenv"} for alias in node.names):
                return True
    return False


def find_violations(root: Path, package: str = "app") -> list[str]:
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        layer = relative.parts[0] if len(relative.parts) > 1 else ""
        location = [package, *relative.parts[:-1]]

        for module in imported_modules(tree, package, location):
            target = module[1] if len(module) > 1 and module[0] == package else ""
            if target in FORBIDDEN_IMPORTS.get(layer, set()):
                violations.append(
                    f"{relative.as_posix()}: layer '{layer}' must not import '{target}' "
                    f"({'.'.join(module)})"
                )
        if relative.as_posix() != SETTINGS_MODULE and reads_environment(tree):
            violations.append(
                f"{relative.as_posix()}: environment variables are read outside {SETTINGS_MODULE}"
            )
    return violations
