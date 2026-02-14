from __future__ import annotations
"""Feasibility Boundary Atlas builder (v103).

This builds a small 'atlas' of nearest-feasible solutions around a base point by sweeping target
directions and lever bounds using `src.frontier.find_nearest_feasible`.

It is SHAMS-native: feasibility-first, deterministic, and audit-ready.
"""

from dataclasses import asdict, replace
from typing import Any, Dict, List, Tuple, Optional
import time
from src.phase1_core import PointInputs
from src.frontier.frontier import find_nearest_feasible

def build_feasibility_atlas(
    base: PointInputs,
    *,
    levers: Dict[str, Tuple[float, float]],
    targets: Optional[Dict[str, float]] = None,
    n_random: int = 80,
    seed: int = 0,
    n_slices: int = 8,
) -> Dict[str, Any]:
    """Return JSON-serializable atlas."""
    created_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    reports: List[Dict[str, Any]] = []

    # Directional sweeps: shrink/expand lever bounds around base deterministically
    keys = sorted(levers.keys())
    for k in keys[:n_slices]:
        lo, hi = levers[k]
        # try 2 bound windows: tighten and widen (within original bounds)
        for frac in (0.5, 1.0):
            # centered around base value
            v0 = float(getattr(base, k))
            span_lo = max(lo, v0 - (v0 - lo) * frac)
            span_hi = min(hi, v0 + (hi - v0) * frac)
            local = dict(levers)
            local[k] = (span_lo, span_hi)
            r = find_nearest_feasible(base, levers=local, targets=targets, n_random=n_random, seed=seed)
            reports.append({"lever_focus": k, "frac": frac, "report": asdict(r)})

    # baseline full-lever search
    r0 = find_nearest_feasible(base, levers=levers, targets=targets, n_random=n_random, seed=seed)
    atlas = {
        "kind": "shams_feasibility_boundary_atlas",
        "created_utc": created_utc,
        "seed": seed,
        "n_random": n_random,
        "n_reports": len(reports) + 1,
        "base": asdict(base),
        "levers": {k: [float(a), float(b)] for k,(a,b) in levers.items()},
        "targets": targets or {},
        "baseline": asdict(r0),
        "reports": reports,
    }
    return atlas
