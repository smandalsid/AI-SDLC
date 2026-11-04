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
# The gate middleware only checks a signature; it must never reach the data layers.
FORBIDDEN_BY_SUBPACKAGE: dict[tuple[str, str], set[str]] = {
    ("api", "middleware"): {"repositories", "services", "db"},
}
MUTABLE_CONSTRUCTORS = {"dict", "list", "set", "defaultdict", "deque", "OrderedDict"}


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
        forbidden = FORBIDDEN_IMPORTS.get(layer, set()) | FORBIDDEN_BY_SUBPACKAGE.get(
            (relative.parts[0], relative.parts[1]) if len(relative.parts) > 2 else ("", ""), set()
        )

        for module in imported_modules(tree, package, location):
            target = module[1] if len(module) > 1 and module[0] == package else ""
            if target in forbidden:
                violations.append(
                    f"{relative.as_posix()}: layer '{layer}' must not import '{target}' "
                    f"({'.'.join(module)})"
                )
        if relative.as_posix() != SETTINGS_MODULE and reads_environment(tree):
            violations.append(
                f"{relative.as_posix()}: environment variables are read outside {SETTINGS_MODULE}"
            )
    return violations


def _is_mutable_value(value: ast.expr | None) -> bool:
    if isinstance(value, ast.Dict | ast.List | ast.Set | ast.DictComp | ast.ListComp | ast.SetComp):
        return True
    if isinstance(value, ast.Call):
        func = value.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        return name in MUTABLE_CONSTRUCTORS
    return False


def _assigned_names(node: ast.stmt) -> list[str]:
    if isinstance(node, ast.Assign):
        return [target.id for target in node.targets if isinstance(target, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def find_mutable_state(root: Path) -> list[str]:
    """Module-level mutable containers with a non-constant name hold hidden state (NFR-009)."""
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            value = node.value if isinstance(node, ast.Assign | ast.AnnAssign) else None
            if not _is_mutable_value(value):
                continue
            for name in _assigned_names(node):
                if not name.isupper() and not (name.startswith("__") and name.endswith("__")):
                    violations.append(
                        f"{path.relative_to(root).as_posix()}: module-level mutable state '{name}'"
                    )
    return violations


SWITCH_WORDS = ("auth", "debug", "bypass", "disable")
# Derived from the session and throttle numbers; it switches nothing off.
ALLOWED_SETTING_NAMES = {"auth_policy"}
CREDENTIAL_WORDS = ("username", "password")


def _is_switch_name(name: str) -> bool:
    lowered = name.lower()
    return lowered not in ALLOWED_SETTING_NAMES and any(word in lowered for word in SWITCH_WORDS)


def _environment_key(node: ast.AST) -> str | None:
    """The literal variable name of os.getenv("X"), os.environ.get("X") or os.environ["X"]."""
    if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"getenv", "get"}:
            return str(node.args[0].value)
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        value = node.value
        if isinstance(value, ast.Attribute) and value.attr == "environ":
            return str(node.slice.value)
    return None


def _setting_reads(tree: ast.AST) -> Iterator[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.endswith("Settings"):
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    yield item.target.id
        elif isinstance(node, ast.Attribute):
            owner = node.value
            if isinstance(owner, ast.Name) and owner.id == "settings":
                yield node.attr
            elif isinstance(owner, ast.Call) and getattr(owner.func, "id", "") == "get_settings":
                yield node.attr
        else:
            key = _environment_key(node)
            if key is not None:
                yield key


def _string_default(value: ast.expr | None) -> bool:
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value != ""
    if isinstance(value, ast.Call):
        return any(
            _string_default(keyword.value) for keyword in value.keywords if keyword.arg == "default"
        )
    return False


def _default_credentials(tree: ast.AST) -> Iterator[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign | ast.AnnAssign):
            if _string_default(node.value):
                for name in _assigned_names(node):
                    if any(word in name.lower() for word in CREDENTIAL_WORDS):
                        yield name
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            positional = [*node.args.posonlyargs, *node.args.args]
            defaults = [None] * (len(positional) - len(node.args.defaults)) + list(
                node.args.defaults
            )
            pairs = list(zip(positional, defaults, strict=True))
            pairs += list(zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True))
            for argument, default in pairs:
                if _string_default(default) and any(
                    word in argument.arg.lower() for word in CREDENTIAL_WORDS
                ):
                    yield argument.arg


def find_auth_switches(root: Path) -> list[str]:
    """Settings that could turn authentication off, and any built-in default credential (FR-016)."""
    findings: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative = path.relative_to(root).as_posix()
        findings += [
            f"{relative}: setting '{name}' reads like an authentication switch"
            for name in _setting_reads(tree)
            if _is_switch_name(name)
        ]
        findings += [
            f"{relative}: default credential in '{name}'" for name in _default_credentials(tree)
        ]
    return findings
