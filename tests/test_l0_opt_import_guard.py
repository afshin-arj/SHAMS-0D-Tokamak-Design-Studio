"""Certified Optimizer Phase 0.3 — anti L0-opt import guardrails.

Hard gate: ``src/evaluator/*`` and ``src/physics/hot_ion.py`` must not import
optimizer / SearchDriver packages. Tests FAIL if someone adds e.g.
``from optimization...`` or ``import scipy.optimize`` into the truth path.

Allowed: ``optimization``, ``solvers``, ``extopt`` packages themselves (they
may call the evaluator). Forbidden: only L0 consumers importing those edges.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.optimization.l0_opt_guards import (
    FORBIDDEN_IMPORT_PREFIXES,
    collect_forbidden_imports,
    default_l0_truth_paths,
    scan_paths_for_forbidden_imports,
)

ROOT = Path(__file__).resolve().parents[1]


def test_forbidden_prefix_inventory() -> None:
    """Documented forbidden edges must be present (regression lock)."""
    required = {
        "optimization",
        "src.optimization",
        "solvers.optimize",
        "src.solvers.optimize",
        "scipy.optimize",
        "extopt",
        "src.extopt",
    }
    assert required.issubset(set(FORBIDDEN_IMPORT_PREFIXES))


@pytest.mark.parametrize(
    "source,expect_mod",
    [
        ("import scipy.optimize\n", "scipy.optimize"),
        ("from scipy.optimize import minimize\n", "scipy.optimize"),
        ("from scipy import optimize\n", "scipy.optimize"),
        ("from optimization.objectives import get_objective\n", "optimization.objectives"),
        ("from src.optimization import objective_contract\n", "src.optimization"),
        ("import src.optimization.objectives\n", "src.optimization.objectives"),
        ("from solvers.optimize import run_lhs\n", "solvers.optimize"),
        ("from src.solvers.optimize import run_lhs\n", "src.solvers.optimize"),
        ("from solvers import optimize\n", "solvers.optimize"),
        ("import extopt.certified_solve\n", "extopt.certified_solve"),
        ("from src.extopt.orchestrator import Orchestrator\n", "src.extopt.orchestrator"),
        ("from src import optimization\n", "src.optimization"),
        ("from src import extopt\n", "src.extopt"),
    ],
)
def test_scanner_flags_forbidden_shapes(source: str, expect_mod: str) -> None:
    hits = collect_forbidden_imports(source)
    assert hits, f"expected hit for {expect_mod!r} in {source!r}"
    mods = [m for _, m in hits]
    assert any(
        m == expect_mod or m.startswith(expect_mod + ".") or expect_mod.startswith(m)
        for m in mods
    ), f"expected {expect_mod!r} among {mods}"


@pytest.mark.parametrize(
    "source",
    [
        "import math\nfrom typing import Any\n",
        "from physics.hot_ion import hot_ion_point\n",
        "from src.physics.hot_ion import hot_ion_point\n",
        "from .derivatives import get_derivative\n",
        "import scipy\nfrom scipy import linalg\n",  # scipy OK; only scipy.optimize forbidden
        "from solvers import constraints\n",  # other solvers.* OK
        "import numpy as np\n",
    ],
)
def test_scanner_allows_non_optimizer_imports(source: str) -> None:
    assert collect_forbidden_imports(source) == []


def test_l0_truth_paths_exist() -> None:
    paths = default_l0_truth_paths(ROOT)
    assert paths, "expected default L0 scan set"
    missing = [p for p in paths if not p.is_file()]
    assert not missing, f"missing L0 truth files: {missing}"


def test_l0_truth_has_no_optimizer_imports() -> None:
    """Hard gate: evaluator + hot_ion must not import optimizer packages."""
    paths = default_l0_truth_paths(ROOT)
    violations = scan_paths_for_forbidden_imports(paths, root=ROOT)
    assert not violations, (
        "Optimizer import path into L0 truth (forbidden):\n"
        + "\n".join(violations)
        + "\n\nSearchDrivers / FoM / scipy.optimize belong outside L0; "
        "they may call Evaluator, never the reverse."
    )


def test_helper_lives_outside_l0() -> None:
    """Guard helper itself is under optimization/ (studio), not evaluator/physics."""
    helper = ROOT / "src" / "optimization" / "l0_opt_guards.py"
    assert helper.is_file()
    # Must not be imported by L0 (covered by scan); and must document prefixes.
    text = helper.read_text(encoding="utf-8")
    assert "FORBIDDEN_IMPORT_PREFIXES" in text
    assert "scipy.optimize" in text
