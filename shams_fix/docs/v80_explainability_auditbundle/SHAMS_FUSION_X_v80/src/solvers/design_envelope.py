from __future__ import annotations
"""Design-envelope solve utilities (SPARC-like workflows).

A "design envelope" solve adjusts a small set of variables to meet high-level targets
(Q, H98, P_net, pulse length) while respecting constraints.

This module wraps the generic constraint solver with sensible defaults for SPARC/HTS-style studies.
"""
from typing import Dict, Tuple, List, Optional

from models.inputs import PointInputs
from solvers.constraint_solver import solve_for_targets


def solve_sparc_envelope(
    base: PointInputs,
    targets: Dict[str, float],
    vary: Optional[List[str]] = None,
    bounds: Optional[Dict[str, Tuple[float, float]]] = None,
    x0: Optional[Dict[str, float]] = None,
    tol: float = 1e-3,
    max_iter: int = 30,
):
    """High-level SPARC-like design envelope solve.

    This is a convenience wrapper around `solve_for_targets` that:
      - uses SHAMS hot_ion_point internally (via constraint_solver)
      - lets UI specify a list of variables and bounds

    Parameters
    ----------
    base:
        Starting PointInputs.
    targets:
        Output targets, e.g. {"Q_DT_eqv": 10.0, "H98": 1.0}
    vary:
        Variables to vary. Default: ["Ip_MA","fG","Paux_MW"]
    bounds:
        Optional bounds dict {var:(lo,hi)}.
    x0:
        Optional initial guess dict {var:x0}; default taken from base.
    """
    if vary is None:
        vary = ["Ip_MA", "fG", "Paux_MW"]
    if bounds is None:
        bounds = {
            "Ip_MA": (0.1, 50.0),
            "fG": (0.1, 1.2),
            "Paux_MW": (0.0, 300.0),
        }
    if x0 is None:
        x0 = {}

    variables: Dict[str, Tuple[float, float, float]] = {}
    for v in vary:
        lo, hi = bounds.get(v, (-1e9, 1e9))
        x0v = float(x0.get(v, getattr(base, v)))
        variables[v] = (x0v, float(lo), float(hi))

    res = solve_for_targets(base=base, targets=targets, variables=variables, max_iter=max_iter, tol=tol)
    return res.inp, res.out, res.ok, res.message
