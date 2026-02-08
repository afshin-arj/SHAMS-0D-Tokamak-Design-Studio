"""SHAMS Optimization Sandbox — Machine Finder (non-authoritative)

This module adds an *exploratory* machine-finding capability that is explicitly
locked behind the frozen SHAMS evaluator.

Core rules:
1) The evaluator (PointInputs -> hot_ion_point -> constraints) is the only source of truth.
2) No constraint relaxation or hidden penalties.
3) Candidates may be explored even if infeasible, but only *audited-feasible*
   candidates can be admitted into the final ranked set.

The algorithms here are intentionally simple, dependency-light, and deterministic
given a seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

import math
import numpy as np


@dataclass(frozen=True)
class Objective:
    key: str
    sense: str = "max"  # 'max' or 'min'
    weight: float = 1.0


@dataclass(frozen=True)
class VarSpec:
    key: str
    lo: float
    hi: float


def _safe_float(x: Any) -> float:
    try:
        if x is None:
            return float("nan")
        return float(x)
    except Exception:
        return float("nan")


def score_outputs(outputs: Dict[str, Any], objectives: List[Objective]) -> float:
    """Compute a weighted objective score from outputs.

    Missing objective keys contribute NaN -> treated as very poor score.
    """
    s = 0.0
    for o in objectives:
        v = _safe_float(outputs.get(o.key))
        if not math.isfinite(v):
            # hard punish missing values
            return -1e30
        if o.sense == "min":
            v = -v
        s += float(o.weight) * v
    return float(s)


def elite_random_search(
    *,
    evaluate_fn,
    anchor_inputs: Dict[str, Any],
    var_specs: List[VarSpec],
    objectives: List[Objective],
    n_iter: int = 2000,
    batch: int = 64,
    elite_frac: float = 0.15,
    seed: int = 1,
    jitter: float = 0.15,
    keep_infeasible_trace: bool = True,
) -> Dict[str, Any]:
    """A dependency-light machine finder.

    - Samples around an anchor within declared bounds.
    - Keeps an elite set of feasible candidates.
    - Refines sampling distribution around elites (simple mean/std update).

    evaluate_fn must accept a dict of inputs and return a dict with:
      {'feasible': bool, 'inputs': dict, 'outputs': dict, 'constraints': list, ...}
    """

    rng = np.random.default_rng(int(seed))
    var_keys = [v.key for v in var_specs]

    # Initialize sampling mean at anchor (clipped into bounds)
    mu = np.array([_safe_float(anchor_inputs.get(k)) for k in var_keys], dtype=float)
    lo = np.array([v.lo for v in var_specs], dtype=float)
    hi = np.array([v.hi for v in var_specs], dtype=float)
    mu = np.clip(mu, lo, hi)

    # Start with broad std based on bounds
    sigma = (hi - lo) / 4.0
    sigma = np.where(sigma <= 0, 1.0, sigma)

    best_feasible: Optional[Dict[str, Any]] = None
    elite: List[Dict[str, Any]] = []
    trace: List[Dict[str, Any]] = []

    def _sample_batch() -> np.ndarray:
        z = rng.normal(size=(batch, len(var_specs)))
        x = mu + z * sigma
        # Add small uniform jitter (helps explore edges)
        if jitter and jitter > 0:
            x += rng.uniform(-1.0, 1.0, size=x.shape) * (hi - lo) * float(jitter)
        return np.clip(x, lo, hi)

    for it in range(int(n_iter)):
        xs = _sample_batch()
        feas_batch: List[Tuple[float, Dict[str, Any]]] = []

        for j in range(xs.shape[0]):
            cand = dict(anchor_inputs)
            for kk, vv in zip(var_keys, xs[j].tolist()):
                cand[kk] = float(vv)
            res = evaluate_fn(cand)
            out = res.get("outputs", {}) or {}
            sc = score_outputs(out, objectives)
            res["_score"] = sc

            if keep_infeasible_trace:
                trace.append({
                    "iter": it,
                    "feasible": bool(res.get("feasible", False)),
                    "score": sc,
                    "failure_mode": res.get("failure_mode"),
                    "active_constraints": res.get("active_constraints", []),
                })

            if res.get("feasible", False):
                feas_batch.append((sc, res))
                if best_feasible is None or sc > float(best_feasible.get("_score", -1e30)):
                    best_feasible = res

        # Update elite pool
        feas_batch.sort(key=lambda t: t[0], reverse=True)
        if feas_batch:
            k_elite = max(1, int(len(feas_batch) * float(elite_frac)))
            elite_now = [r for _, r in feas_batch[:k_elite]]
            elite.extend(elite_now)

            # Keep elite bounded
            elite.sort(key=lambda r: float(r.get("_score", -1e30)), reverse=True)
            elite = elite[: max(20, k_elite * 5)]

            # Refit mu/sigma from elites
            X = np.array([[ _safe_float(e.get("inputs", {}).get(k, anchor_inputs.get(k))) for k in var_keys] for e in elite], dtype=float)
            if np.all(np.isfinite(X)) and X.shape[0] >= 3:
                mu = np.clip(X.mean(axis=0), lo, hi)
                sigma = np.clip(X.std(axis=0) + 1e-9, (hi - lo) / 200.0, (hi - lo) / 2.0)

    # Prepare outputs
    elite_sorted = sorted(elite, key=lambda r: float(r.get("_score", -1e30)), reverse=True)
    return {
        "kind": "optimization_sandbox_machine_finder_run",
        "seed": int(seed),
        "n_iter": int(n_iter),
        "batch": int(batch),
        "elite_frac": float(elite_frac),
        "var_specs": [v.__dict__ for v in var_specs],
        "objectives": [o.__dict__ for o in objectives],
        "best_feasible": best_feasible,
        "elite": elite_sorted,
        "trace": trace,
    }
