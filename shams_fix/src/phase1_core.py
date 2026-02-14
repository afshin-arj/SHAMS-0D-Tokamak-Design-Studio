"""phase1_core.py

Compatibility layer.

The Phase‑1 codebase has been refactored into clearer modules:
- models/ (data containers)
- physics/ (0‑D point physics + screening proxies)
- solvers/ (root finders + nested solves)
- plotters/ (plot-data helpers; UI uses these where convenient)

This file preserves the original import surface so existing scripts and the UI keep working.
"""

from __future__ import annotations

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore
from physics.radiation import bremsstrahlung_W
from physics.hot_ion import hot_ion_point
from solvers.root import bisect
from solvers.constraint_solver import solve_for_targets, solve_for_targets_stream, SolveResult
from solvers.point_solver import (
    solve_Ip_for_H98_with_Q_match_stream,
    solve_fG_for_QDTeqv,
    solve_Ip_for_H98_with_Q_match,
)

__all__ = [
    # Data containers
    "PointInputs",

    # Core physics
    "hot_ion_point",
    "bremsstrahlung_W",

    # Low-level numerics
    "bisect",

    # Legacy (nested) point solvers used by the existing UI
    "solve_Ip_for_H98_with_Q_match_stream",
    "solve_fG_for_QDTeqv",
    "solve_Ip_for_H98_with_Q_match",

    # PROCESS-inspired system/constraint solvers (bounded, vector targets)
    "solve_Ip_fG_for_H98_Q",
    "solve_Ip_fG_for_H98_Q_stream",
    "solve_for_targets",
    "solve_for_targets_stream",
    "SolveResult",

    # SPARC-like design-envelope convenience wrapper
    "solve_sparc_envelope",

    # Lightweight constrained optimization
    "optimize_design",

    # Feasibility frontier
    "find_nearest_feasible",
]

from solvers.system_solver import solve_Ip_fG_for_H98_Q, solve_Ip_fG_for_H98_Q_stream
from solvers.design_envelope import solve_sparc_envelope

from solvers.optimize import optimize_design

from frontier.frontier import find_nearest_feasible