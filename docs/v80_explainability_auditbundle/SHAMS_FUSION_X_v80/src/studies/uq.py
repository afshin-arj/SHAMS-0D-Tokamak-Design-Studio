from __future__ import annotations

"""Uncertainty quantification utilities.

This provides PROCESS-like batch robustness features:
- sample distributions of inputs
- compute probability of feasibility
- compute output quantiles
- rank risk contributors (simple correlation-based sensitivity)

No heavy dependencies are required.
"""

from dataclasses import replace
from typing import Any, Dict, List, Tuple
import math
import random

from models.inputs import PointInputs
from evaluator.core import Evaluator
from constraints.constraints import evaluate_constraints
from constraints.bookkeeping import summarize as summarize_constraints
from .spec import DistributionSpec


def _sample_one(rng: random.Random, ds: DistributionSpec) -> float:
    p = ds.params or {}
    dist = (ds.dist or "uniform").lower().strip()
    if dist == "uniform":
        lo = float(p.get("lo", 0.0))
        hi = float(p.get("hi", 1.0))
        return lo + (hi - lo) * rng.random()
    if dist == "normal":
        mu = float(p.get("mu", 0.0))
        sigma = float(p.get("sigma", 1.0))
        return rng.gauss(mu, sigma)
    if dist == "lognormal":
        mu = float(p.get("mu", 0.0))
        sigma = float(p.get("sigma", 1.0))
        return math.exp(rng.gauss(mu, sigma))
    # unknown -> treat as constant
    return float(p.get("value", 0.0))


def run_uq(
    base: PointInputs,
    *,
    distributions: List[DistributionSpec],
    n_samples: int,
    outputs: List[str],
    seed: int = 0,
) -> Dict[str, Any]:
    """Run a Monte-Carlo UQ sweep and return an aggregate report."""
    rng = random.Random(seed)
    evaluator = Evaluator()

    X: Dict[str, List[float]] = {ds.name: [] for ds in distributions}
    Y: Dict[str, List[float]] = {k: [] for k in (outputs or [])}
    feasible_flags: List[int] = []

    for _ in range(max(int(n_samples), 0)):
        inp = base
        upd = {}
        for ds in distributions:
            upd[ds.name] = _sample_one(rng, ds)
        inp = PointInputs.from_dict({**base.to_dict(), **upd})
        out = evaluator.evaluate(inp).out
        cs = evaluate_constraints(out)
        summ = summarize_constraints(cs)
        feasible_flags.append(1 if summ.feasible else 0)
        for k in X:
            X[k].append(float(getattr(inp, k)))
        for k in Y:
            Y[k].append(float(out.get(k, float("nan"))))

    def quantiles(vals: List[float], qs: List[float]) -> Dict[str, float]:
        vv = [v for v in vals if isinstance(v, (int, float)) and v == v and math.isfinite(v)]
        if not vv:
            return {f"q{int(q*100)}": float("nan") for q in qs}
        vv.sort()
        outq: Dict[str, float] = {}
        for q in qs:
            i = int(round(q * (len(vv) - 1)))
            outq[f"q{int(q*100)}"] = float(vv[max(0, min(len(vv)-1, i))])
        return outq

    # basic correlation sensitivity ranking (Pearson)
    def pearson(x: List[float], y: List[float]) -> float:
        pairs = [(a, b) for a, b in zip(x, y) if a == a and b == b and math.isfinite(a) and math.isfinite(b)]
        if len(pairs) < 3:
            return float("nan")
        xs = [a for a, _ in pairs]
        ys = [b for _, b in pairs]
        mx = sum(xs) / len(xs)
        my = sum(ys) / len(ys)
        num = sum((a-mx)*(b-my) for a, b in pairs)
        denx = math.sqrt(sum((a-mx)**2 for a in xs))
        deny = math.sqrt(sum((b-my)**2 for b in ys))
        if denx == 0 or deny == 0:
            return float("nan")
        return num / (denx * deny)

    out_quantiles: Dict[str, Any] = {}
    for k, vals in Y.items():
        out_quantiles[k] = {
            "mean": float(sum(v for v in vals if v == v and math.isfinite(v)) / max(1, sum(1 for v in vals if v == v and math.isfinite(v)))),
            **quantiles(vals, [0.05, 0.5, 0.95]),
        }

    sens: Dict[str, Any] = {}
    for yk in Y.keys():
        rows = []
        for xk in X.keys():
            r = pearson(X[xk], Y[yk])
            rows.append({"input": xk, "r": float(r)})
        rows.sort(key=lambda d: abs(d.get("r", 0.0)) if d.get("r") == d.get("r") else -1.0, reverse=True)
        sens[yk] = rows

    p_feas = sum(feasible_flags) / max(1, len(feasible_flags))

    return {
        "n_samples": int(n_samples),
        "seed": int(seed),
        "p_feasible": float(p_feas),
        "outputs": list(Y.keys()),
        "quantiles": out_quantiles,
        "sensitivity": sens,
    }
