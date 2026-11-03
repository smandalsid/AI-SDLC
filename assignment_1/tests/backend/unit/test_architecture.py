from pathlib import Path

from .layer_scan import find_mutable_state, find_violations

APP_DIR = Path(__file__).resolve().parents[3] / "src" / "backend" / "app"


def write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_scanner_flags_models_importing_a_higher_layer(tmp_path: Path) -> None:
    write(tmp_path, "models/bus.py", "from app.services import bus_service\n")

    violations = find_violations(tmp_path)

    assert len(violations) == 1
    assert "models/bus.py" in violations[0]
    assert "services" in violations[0]


def test_scanner_flags_each_forbidden_edge(tmp_path: Path) -> None:
    write(tmp_path, "repositories/r.py", "import app.api.deps\n")
    write(tmp_path, "services/s.py", "from app.db.session import get_session\n")
    write(tmp_path, "core/c.py", "from app.models.bus import Bus\n")

    assert len(find_violations(tmp_path)) == 3


def test_scanner_resolves_relative_imports(tmp_path: Path) -> None:
    write(tmp_path, "models/bus.py", "from ..services import bus_service\n")

    assert len(find_violations(tmp_path)) == 1


def test_scanner_allows_downward_and_same_layer_imports(tmp_path: Path) -> None:
    write(tmp_path, "services/s.py", "from app.repositories.protocols import BusReader\n")
    write(tmp_path, "repositories/r.py", "from app.models.bus import Bus\n")
    write(tmp_path, "api/a.py", "from app.services.bus_service import BusService\n")
    write(tmp_path, "db/d.py", "from app.models.base import Base\n")
    write(tmp_path, "core/c.py", "from app.core.errors import AppError\n")

    assert find_violations(tmp_path) == []


def test_scanner_flags_environment_reads_outside_the_settings_module(tmp_path: Path) -> None:
    write(tmp_path, "services/s.py", 'import os\nvalue = os.environ["X"]\n')
    write(tmp_path, "api/a.py", 'import os\nvalue = os.getenv("X")\n')
    write(tmp_path, "db/d.py", "from os import environ\n")

    assert len(find_violations(tmp_path)) == 3


def test_scanner_allows_environment_reads_in_the_settings_module(tmp_path: Path) -> None:
    write(tmp_path, "core/config.py", 'import os\nvalue = os.environ["X"]\n')

    assert find_violations(tmp_path) == []


def test_application_has_no_layer_violations() -> None:
    assert find_violations(APP_DIR) == []


def test_foundation_layers_are_populated() -> None:
    for layer in ("core", "models", "db", "api"):
        modules = [path for path in (APP_DIR / layer).rglob("*.py") if path.name != "__init__.py"]
        assert modules, f"layer {layer} has no modules"
    assert (APP_DIR / "main.py").exists()


def test_scanner_flags_middleware_importing_the_data_layers(tmp_path: Path) -> None:
    write(tmp_path, "api/middleware/a.py", "from app.repositories.user_repository import X\n")
    write(tmp_path, "api/middleware/b.py", "from app.services.auth_service import X\n")
    write(tmp_path, "api/middleware/c.py", "from app.db.session import X\n")

    assert len(find_violations(tmp_path)) == 3


def test_scanner_allows_middleware_to_use_core_and_the_error_handlers(tmp_path: Path) -> None:
    write(tmp_path, "api/middleware/a.py", "from app.core.errors import UnauthenticatedError\n")
    write(tmp_path, "api/middleware/b.py", "from app.api.error_handlers import response_for\n")

    assert find_violations(tmp_path) == []


def test_scanner_flags_module_level_mutable_state(tmp_path: Path) -> None:
    write(tmp_path, "services/a.py", "sessions = {}\n")
    write(tmp_path, "services/b.py", "counters: list[int] = []\n")
    write(
        tmp_path, "services/c.py", "from collections import defaultdict\nseen = defaultdict(list)\n"
    )
    write(tmp_path, "services/d.py", "cache = set()\n")

    assert len(find_mutable_state(tmp_path)) == 4


def test_scanner_allows_constants_and_non_container_values(tmp_path: Path) -> None:
    write(
        tmp_path,
        "core/a.py",
        'STATUS_BY_CODE = {"a": 1}\nBUSES: list[int] = [1]\n__all__ = ["x"]\n'
        "import logging\nlogger = logging.getLogger(__name__)\nlimit = 5\n",
    )

    assert find_mutable_state(tmp_path) == []


def test_application_holds_no_module_level_session_or_counter_state() -> None:
    assert find_mutable_state(APP_DIR) == []


def test_credential_modules_exist_and_import_no_other_application_layer() -> None:
    for name in ("passwords.py", "tokens.py"):
        assert (APP_DIR / "core" / name).exists(), f"core/{name} is missing"
    assert find_violations(APP_DIR) == []
