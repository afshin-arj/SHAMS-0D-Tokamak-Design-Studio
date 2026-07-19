"""Anti L0-opt import guardrails (Certified Optimizer Phase 0.3).

Frozen truth (`Evaluator` → `hot_ion`) must never import optimizer / search
packages. SearchDrivers, FoM contracts, and SciPy optimize live **outside** L0
and may call the evaluator; the reverse edge is forbidden.

This module lists forbidden import prefixes and provides an AST scanner used by
lock tests. It does not change L0 behavior.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

# Packages / modules that must not appear in L0 import graphs.
# Allow optimization / solvers / extopt themselves; forbid only L0 consumers.
FORBIDDEN_IMPORT_PREFIXES: Tuple[str, ...] = (
    "optimization",
    "src.optimization",
    "solvers.optimize",
    "src.solvers.optimize",
    "scipy.optimize",
    "extopt",
    "src.extopt",
)

# L0 truth files scanned by default (relative to SHAMS-0D repo root).
DEFAULT_L0_TRUTH_RELPATHS: Tuple[str, ...] = (
    "src/evaluator/core.py",
    "src/evaluator/__init__.py",
    "src/evaluator/derivatives.py",
    "src/evaluator/cache_key.py",
    "src/physics/hot_ion.py",
)


def _module_matches_forbidden(module: str, forbidden: Sequence[str]) -> bool:
    """True if ``module`` is equal to or a submodule of any forbidden prefix."""
    mod = (module or "").strip()
    if not mod:
        return False
    for prefix in forbidden:
        if mod == prefix or mod.startswith(prefix + "."):
            return True
    return False


def _import_from_target(node: ast.ImportFrom) -> str:
    """Resolve ImportFrom to a dotted module path (best-effort; relative → '')."""
    if node.level and not node.module:
        # Relative import of siblings only — not an absolute optimizer package.
        return ""
    if node.level and node.module:
        # e.g. from ..optimization import x — treat module part as absolute hint
        return str(node.module)
    return str(node.module or "")


def collect_forbidden_imports(
    source: str,
    *,
    filename: str = "<string>",
    forbidden: Sequence[str] = FORBIDDEN_IMPORT_PREFIXES,
) -> List[Tuple[int, str]]:
    """Return ``(lineno, imported_module)`` for each forbidden import in ``source``."""
    tree = ast.parse(source, filename=filename)
    hits: List[Tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = str(alias.name)
                if _module_matches_forbidden(name, forbidden):
                    hits.append((int(node.lineno), name))
        elif isinstance(node, ast.ImportFrom):
            # from scipy import optimize
            if node.module == "scipy":
                for alias in node.names:
                    if alias.name == "optimize" or str(alias.name).startswith("optimize."):
                        hits.append((int(node.lineno), f"scipy.{alias.name}"))
                continue
            # from solvers import optimize
            if node.module in ("solvers", "src.solvers"):
                for alias in node.names:
                    if alias.name == "optimize" or str(alias.name).startswith("optimize."):
                        hits.append((int(node.lineno), f"{node.module}.{alias.name}"))
                continue
            # from src import optimization / extopt
            if node.module == "src":
                for alias in node.names:
                    composed = f"src.{alias.name}"
                    if _module_matches_forbidden(composed, forbidden):
                        hits.append((int(node.lineno), composed))
                continue
            target = _import_from_target(node)
            if _module_matches_forbidden(target, forbidden):
                hits.append((int(node.lineno), target))

    return sorted(hits, key=lambda t: (t[0], t[1]))


def scan_paths_for_forbidden_imports(
    paths: Iterable[Path],
    *,
    forbidden: Sequence[str] = FORBIDDEN_IMPORT_PREFIXES,
    root: Path | None = None,
) -> List[str]:
    """Scan files; return human-readable violation strings (empty if clean)."""
    violations: List[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        hits = collect_forbidden_imports(text, filename=str(path), forbidden=forbidden)
        if not hits:
            continue
        try:
            label = str(path.relative_to(root)) if root is not None else str(path)
        except ValueError:
            label = str(path)
        for lineno, mod in hits:
            violations.append(f"{label}:{lineno}: forbidden import {mod!r}")
    return violations


def default_l0_truth_paths(repo_root: Path) -> List[Path]:
    """Absolute paths for the default L0 truth scan set."""
    return [repo_root / rel for rel in DEFAULT_L0_TRUTH_RELPATHS]
