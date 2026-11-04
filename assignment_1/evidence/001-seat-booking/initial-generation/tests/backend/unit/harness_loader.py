"""Loads a script from .harness/ as a module so unit tests can call it without a subprocess."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

HARNESS_DIR = Path(__file__).resolve().parents[3] / ".harness"


def load_harness_module(name: str) -> ModuleType:
    path = HARNESS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"harness_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    if str(HARNESS_DIR) not in sys.path:
        sys.path.insert(0, str(HARNESS_DIR))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
