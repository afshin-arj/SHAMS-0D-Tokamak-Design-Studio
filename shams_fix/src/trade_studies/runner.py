from __future__ import annotations

"""Deterministic trade study runner (v303.0).

Implements a reproducible, feasibility-first trade study pipeline:
  - deterministic LHS sampling under a knob set
  - evaluator verification (frozen truth)
  - constraint-ledger feasibility annotations
  - multi-objective Pareto extraction over *feasible* points only

No internal optimization is performed in this module.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import asdict, replace
from typing import Any, Dict, List, Optional, Tuple

import math
import random

from models.inputs import PointInputs
from evaluator.core import Evaluator
from constraints.constraints import evaluate_constraints
from constraints.bookkeeping import summarize as summarize_constraints
from optimization.objectives import get_objective, list_objectives


def latin_hypercube_samples(n: int, bounds: Dict[str, Tuple[float, float]], seed: int) -> List[Dict[str, float]]:
    """Deterministic Latin hypercube sampling in given bounds.

    Determinism: fixed (seed, bounds, n) => identical samples.
    """
    rng = random.Random(int(seed))
    keys = list(bounds.keys())
    strata = list(range(n))
    samples = [{k: 0.0 for k in keys} for _ in range(n)]
    for k in keys:
        rng.shuffle(strata)
        lo, hi = bounds[k]
        lo = float(lo)
        hi = float(hi)
        for i, s in enumerate(strata):
            u = (float(s) + rng.random()) / float(n)
            samples[i][k] = lo + u * (hi - lo)
    return samples


def _objective_value(out: Dict[str, Any], name: str) -> float:
    spec = get_objective(name)
    if spec is None:
        raise KeyError(f"Unknown objective: {name}. Available: {sorted(list_objectives().keys())}")
    try:
        v = float(spec.fn(out))
    except Exception:
        v = float("nan")
    return v


def _dominates(a: Dict[str, float], b: Dict[str, float], senses: Dict[str, str]) -> bool:
    """Return True if a dominates b for objectives dict {name: 'min'|'max'}."""
    better_or_equal = True
    strictly_better = False
    for name, sense in senses.items():
        va = float(a.get(name, float("nan")))
        vb = float(b.get(name, float("nan")))
        if not (math.isfinite(va) and math.isfinite(vb)):
            return False
        if sense == "min":
            if va > vb:
                better_or_equal = False
            if va < vb:
                strictly_better = True
        else:
            if va < vb:
                better_or_equal = False
            if va > vb:
                strictly_better = True
    return bool(better_or_equal and strictly_better)


def pareto_front(points: List[Dict[str, float]], senses: Dict[str, str]) -> List[Dict[str, float]]:
    front: List[Dict[str, float]] = []
    for p in points:
        dominated = False
        for q in points:
            if q is p:
                continue
            if _dominates(q, p, senses):
                dominated = True
                break
        if not dominated:
            front.append(p)
    return front


def run_trade_study(
    evaluator: Evaluator,
    base_inputs: PointInputs,
    bounds: Dict[str, Tuple[float, float]],
    objectives: List[str],
    objective_senses: Dict[str, str],
    *,
    n_samples: int,
    seed: int,
    policy: Optional[Dict[str, Any]] = None,
    include_outputs: bool = False,
) -> Dict[str, Any]:
    """Run a deterministic trade study.

    Returns:
      - records: all samples with feasibility + objective values
      - feasible: feasible subset
      - pareto: nondominated feasible subset
      - meta: study parameters
    """
    n = max(1, int(n_samples))
    samples = latin_hypercube_samples(n=n, bounds=bounds, seed=int(seed))
    base_d = asdict(base_inputs)

    records: List[Dict[str, Any]] = []
    feasible: List[Dict[str, Any]] = []

    for i, s in enumerate(samples):
        dd = dict(base_d)
        for k, v in s.items():
            if k in dd:
                dd[k] = float(v)
        inp = PointInputs(**dd)
        res = evaluator.evaluate(inp)
        out = dict(res.out or {})
        cons = evaluate_constraints(out, policy=policy)
        summ = summarize_constraints(cons).to_dict()
        feas = bool(summ.get("feasible", False))
        mmin = summ.get("worst_hard_margin_frac", None)
        try:
            mmin_f = float(mmin) if mmin is not None else float("nan")
        except Exception:
            mmin_f = float("nan")

        row: Dict[str, Any] = {
            "i": int(i),
            "is_feasible": bool(feas),
            "min_margin_frac": float(mmin_f),
        }
        row.update({k: float(v) for k, v in s.items()})

        for obj in objectives:
            row[obj] = float(_objective_value(out, obj))

        # Minimal diagnosis fields
        row["dominant_mechanism"] = str(summ.get("dominant_mechanism", ""))
        row["dominant_constraint"] = str(summ.get("dominant_constraint", ""))

        if include_outputs:
            row["outputs"] = out
            row["constraints_summary"] = summ

        records.append(row)
        if feas:
            feasible.append(row)

    pareto = pareto_front(
        points=[{k: float(v) for k, v in r.items() if k in objectives} for r in feasible],
        senses=objective_senses,
    )

    # Map pareto objective-only dicts back to rows (deterministic stable match)
    pareto_rows: List[Dict[str, Any]] = []
    for r in feasible:
        key = tuple(float(r.get(o, float("nan"))) for o in objectives)
        for p in pareto:
            if key == tuple(float(p.get(o, float("nan"))) for o in objectives):
                pareto_rows.append(r)
                break

    meta = {
        "schema": "trade_study.v1",
        "n_samples": int(n),
        "seed": int(seed),
        "bounds": {k: [float(v[0]), float(v[1])] for k, v in bounds.items()},
        "objectives": list(objectives),
        "objective_senses": dict(objective_senses),
    }
    return {
        "meta": meta,
        "records": records,
        "feasible": feasible,
        "pareto": pareto_rows,
    }
