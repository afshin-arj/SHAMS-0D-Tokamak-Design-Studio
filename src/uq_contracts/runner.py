from __future__ import annotations

import copy
from dataclasses import asdict
import itertools
from typing import Any, Dict, List, Optional, Tuple

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore

from physics.hot_ion import hot_ion_point
from constraints.constraints import evaluate_constraints
from constraints.bookkeeping import summarize as summarize_constraints
from shams_io.run_artifact import build_run_artifact

from .spec import Interval, UncertaintyContractSpec


def _merged_policy(base_out: Dict[str, Any], overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    try:
        pol = base_out.get("_policy_contract") if isinstance(base_out, dict) else None
        base = pol if isinstance(pol, dict) else {}
    except Exception:
        base = {}
    merged = dict(base or {})
    if overrides:
        merged.update(dict(overrides))
    return merged


def enumerate_corners(intervals: Dict[str, Interval]) -> List[Dict[str, float]]:
    """Deterministically enumerate 2^N corners in stable order.

    Ordering: lexicographic over sorted variable names, with (lo, hi) mapped to (0,1).
    """
    keys = sorted(list(intervals.keys()))
    bounds = [intervals[k].normalized() for k in keys]
    corners: List[Dict[str, float]] = []
    for bits in itertools.product([0, 1], repeat=len(keys)):
        d: Dict[str, float] = {}
        for k, it, b in zip(keys, bounds, bits):
            d[k] = float(it.lo if b == 0 else it.hi)
        corners.append(d)
    return corners


def run_uncertainty_contract_for_point(
    base_inputs: PointInputs,
    spec: UncertaintyContractSpec,
    *,
    label_prefix: str = "uq",
    max_dims: int = 16,
    include_corner_artifacts: bool = True,
) -> Dict[str, Any]:
    """Evaluate feasibility across deterministic interval corners.

    Performance / determinism:
    - When include_corner_artifacts=False, the function still evaluates every
      corner deterministically, but avoids building full per-corner run artifacts.
      This is useful for diagnostic probes (e.g., mirage pathfinding scans) where
      only the summary verdict + worst margin is required.
    """
    intervals = dict(spec.intervals or {})
    if not intervals:
        raise ValueError("spec.intervals must be non-empty")

    if len(intervals) > int(max_dims):
        raise ValueError(f"Too many uncertain dimensions: {len(intervals)} > {int(max_dims)}. "
                         "Reduce dimensions or increase max_dims explicitly.")

    base_out = hot_ion_point(base_inputs)
    policy = _merged_policy(base_out if isinstance(base_out, dict) else {}, spec.policy_overrides)

    corners = enumerate_corners(intervals)
    corner_arts: List[Dict[str, Any]] = []
    feas_flags: List[bool] = []
    worst_margin = None
    worst_corner = None

    for i, corner in enumerate(corners):
        base_d = asdict(base_inputs)
        for k, v in corner.items():
            if k in base_d:
                base_d[k] = v
        inp = PointInputs(**base_d)

        out = hot_ion_point(inp)
        cons = evaluate_constraints(out, policy=policy)
        cs = summarize_constraints(cons).to_dict()
        feasible = bool(cs.get("feasible", False))
        feas_flags.append(feasible)

        try:
            wm = cs.get("worst_hard_margin_frac", None)
            wmf = float(wm) if wm is not None else 0.0
        except Exception:
            wmf = 0.0

        # Worst = most negative margin (smallest)
        if worst_margin is None or wmf < float(worst_margin):
            worst_margin = float(wmf)
            worst_corner = i

        if include_corner_artifacts:
            art = build_run_artifact(
                inputs=dict(inp.__dict__),
                outputs=dict(out),
                constraints=cons,
                meta={"mode": "uncertainty_contract", "label": f"{label_prefix}:{spec.name}:corner{i:04d}"},
                solver={"message": "uncertainty_contract_corner"},
                economics=dict((out or {}).get("_economics", {})) if isinstance(out, dict) else {},
            )
            art["uncertainty_contract"] = spec.to_dict()
            art["corner_index"] = int(i)
            art["corner_overrides"] = dict(corner)
            art["corner_constraints_summary"] = cs
            corner_arts.append(art)

    n = len(corners)
    n_feas = sum(1 for f in feas_flags if f)
    if n_feas == n:
        verdict = "ROBUST_PASS"
    elif n_feas == 0:
        verdict = "FAIL"
    else:
        verdict = "FRAGILE"

    summary = {
        "schema_version": "uncertainty_contract_summary.v1",
        "name": str(spec.name),
        "n_dims": int(len(intervals)),
        "n_corners": int(n),
        "n_feasible": int(n_feas),
        "verdict": verdict,
        "worst_corner_index": int(worst_corner) if worst_corner is not None else None,
        "worst_hard_margin_frac": float(worst_margin) if worst_margin is not None else None,
    }

    return {
        "schema_version": "uncertainty_contract.v1",
        "label_prefix": str(label_prefix),
        "spec": spec.to_dict(),
        "base_inputs": dict(base_inputs.__dict__),
        "policy_used": dict(policy),
        "summary": summary,
        "corners": corner_arts,
    }
