"""Load repo-root ``analysis/*`` modules without circular import via ``src/analysis`` shims."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_REPO_ROOT = Path(__file__).resolve().parents[2]


def load_canonical(module_basename: str) -> ModuleType:
    path = _REPO_ROOT / "analysis" / f"{module_basename}.py"
    mod_name = f"_shams_canonical_{module_basename}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load canonical analysis module: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod
