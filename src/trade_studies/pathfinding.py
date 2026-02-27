from __future__ import annotations

"""Mirage pathfinding utilities (v303.0).

Given a candidate that passes an Optimistic lane but fails Robust,
this module performs deterministic one-knob improvement scans to find
the smallest declared improvement that restores Robust feasibility.

This is *not* a solver. It is a bounded, logged parameter scan.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import asdict
from typing import Any, Dict, List, Tuple

import math

from models.inputs import PointInputs
from evaluator.core import Evaluator
from uq_contracts.runner import run_uncertainty_contract_for_point
from uq_contracts.spec import robust_uncertainty_contract


def _robust_pass(ev: Evaluator, inp: PointInputs) -> Tuple[bool, float, Dict[str, Any]]:
    spec = robust_uncertainty_contract(inp)
    uq = run_uncertainty_contract_for_point(inp, spec, label_prefix="laneR", include_corner_artifacts=False)
    summ = dict(uq.get("summary", {}) or {})
    verdict = str(summ.get("verdict", ""))
    wm = summ.get("worst_hard_margin_frac", None)
    try:
        wm_f = float(wm) if wm is not None else float("nan")
    except Exception:
        wm_f = float("nan")
    return (verdict == "ROBUST_PASS"), float(wm_f), uq


def one_knob_path_scan(
    ev: Evaluator,
    base: PointInputs,
    knob: str,
    *,
    lo: float,
    hi: float,
    n: int = 17,
) -> Dict[str, Any]:
    """Scan a single knob and report the first robust-pass point.

    The scan is linear in the knob value and deterministic.
    """
    base_d = asdict(base)
    if knob not in base_d:
        raise KeyError(f"Unknown PointInputs knob: {knob}")

    lo = float(lo)
    hi = float(hi)
    n = max(3, int(n))

    rows: List[Dict[str, Any]] = []
    first_pass = None
    for i in range(n):
        t = float(i) / float(n - 1)
        val = lo + t * (hi - lo)
        dd = dict(base_d)
        dd[knob] = float(val)
        inp = PointInputs(**dd)
        ok, worst, _uq = _robust_pass(ev, inp)
        rows.append({"i": int(i), knob: float(val), "robust_pass": bool(ok), "worst_margin_frac": float(worst)})
        if ok and first_pass is None:
            first_pass = {"i": int(i), knob: float(val), "worst_margin_frac": float(worst)}

    return {
        "schema": "mirage_path_scan.v1",
        "knob": str(knob),
        "range": {"lo": float(lo), "hi": float(hi), "n": int(n)},
        "first_robust_pass": first_pass,
        "rows": rows,
    }


def default_pathfinding_levers(base: PointInputs) -> List[Tuple[str, float, float]]:
    """Return canonical improvement levers (deterministic).

    Ranges are declared relative to current value and clamped to reasonable intervals.
    """
    def _g(k: str, default: float) -> float:
        try:
            return float(getattr(base, k))
        except Exception:
            return float(default)

    c = _g("confinement_mult", 1.0)
    lq = _g("lambda_q_mult", 1.0)
    jc = _g("hts_Jc_mult", 1.0)

    return [
        ("confinement_mult", max(0.5, c), min(2.0, 1.30 * c)),
        ("lambda_q_mult", max(0.4, lq), min(3.0, 1.50 * lq)),
        ("hts_Jc_mult", max(0.5, jc), min(2.0, 1.30 * jc)),
    ]
