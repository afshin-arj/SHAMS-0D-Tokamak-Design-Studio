from __future__ import annotations

"""Feasibility frontier tools.

PROCESS users often run into: "this point failed, what should I tweak?".
This module provides a simple, deterministic *frontier* search that tries to
find a nearby feasible point by varying a small set of levers within bounds.

This is intentionally dependency-light (no SciPy). It uses:
- corner + midpoint probes
- random multistart sampling
- feasibility-first ranking

It emits a JSON-serializable report suitable for artifacts + UI.
"""

from dataclasses import dataclass
from dataclasses import replace
from typing import Any, Dict, List, Tuple, Optional
import math
import random

from models.inputs import PointInputs
from evaluator.core import Evaluator
from constraints.constraints import evaluate_constraints
from constraints.bookkeeping import summarize as summarize_constraints


@dataclass(frozen=True)
class FrontierResult:
    ok: bool
    best_inputs: PointInputs
    best_out: Dict[str, float]
    best_score: float
    report: Dict[str, Any]


def _l2_scaled_delta(base: PointInputs, cand: PointInputs, scales: Dict[str, float]) -> float:
    s = 0.0
    n = 0
    for k, sc in scales.items():
        try:
            b = float(getattr(base, k))
            c = float(getattr(cand, k))
        except Exception:
            continue
        denom = float(sc) if float(sc) != 0 else 1.0
        d = (c - b) / denom
        if math.isfinite(d):
            s += d * d
            n += 1
    return math.sqrt(s / max(n, 1)) if n else float("inf")


def find_nearest_feasible(
    base: PointInputs,
    *,
    levers: Dict[str, Tuple[float, float]],
    targets: Optional[Dict[str, float]] = None,
    n_random: int = 60,
    seed: int = 0,
) -> FrontierResult:
    """Search for a nearby feasible point by varying `levers` within bounds.

    Parameters
    ----------
    base:
        Starting point.
    levers:
        Mapping lever -> (lo, hi).
    targets:
        Optional output targets to rank "best achieved" among feasible points.
    n_random:
        Random samples in addition to corners/midpoint.
    seed:
        RNG seed for reproducibility.
    """

    rng = random.Random(seed)
    evaluator = Evaluator()
    lever_keys = list(levers.keys())

    # scaling for distance: use lever span
    scales = {k: max(abs(hi - lo), 1e-9) for k, (lo, hi) in levers.items()}

    def clamp(k: str, v: float) -> float:
        lo, hi = levers[k]
        return max(lo, min(hi, float(v)))

    def make(**upd: float) -> PointInputs:
        d = base.to_dict()
        for k, v in upd.items():
            d[k] = clamp(k, v)
        return PointInputs.from_dict(d)

    def score(inp: PointInputs, out: Dict[str, float]) -> Tuple[bool, float, Dict[str, Any]]:
        cs = evaluate_constraints(out)
        summ = summarize_constraints(cs)
        feasible = bool(summ.feasible)
        # hard-first penalty: violations dominate
        hard_fail = int(summ.n_hard_failed)
        worst = float(summ.worst_hard_margin_frac) if summ.worst_hard_margin_frac is not None else 0.0
        soft_pen = float(summ.soft_penalty_sum)
        targ_err = 0.0
        if targets:
            for k, t in targets.items():
                v = float(out.get(k, float("nan")))
                if math.isfinite(v):
                    targ_err += (v - float(t)) ** 2
                else:
                    targ_err += 1e6
            targ_err = math.sqrt(targ_err / max(len(targets), 1))

        # distance from base in scaled lever space
        dist = _l2_scaled_delta(base, inp, scales)
        # Composite score: violations dominate, then targets, then distance, then soft
        comp = (
            1e4 * hard_fail
            + 1e3 * max(0.0, -worst)
            + 10.0 * targ_err
            + 1.0 * dist
            + 0.1 * soft_pen
        )
        meta = {
            "feasible": feasible,
            "hard_failed": hard_fail,
            "worst_hard_margin_frac": worst,
            "soft_penalty_sum": soft_pen,
            "target_rmse": targ_err,
            "scaled_distance": dist,
            "constraints_summary": summ.to_dict(),
        }
        return feasible, float(comp), meta

    # Candidate generator: midpoint + corners
    candidates: List[PointInputs] = []
    mid = {k: 0.5 * (lo + hi) for k, (lo, hi) in levers.items()}
    candidates.append(make(**mid))
    # corners (2^n, capped)
    if len(lever_keys) <= 10:
        for mask in range(1 << len(lever_keys)):
            upd = {}
            for i, k in enumerate(lever_keys):
                lo, hi = levers[k]
                upd[k] = hi if (mask & (1 << i)) else lo
            candidates.append(make(**upd))
    # random
    for _ in range(max(n_random, 0)):
        upd = {}
        for k, (lo, hi) in levers.items():
            upd[k] = lo + (hi - lo) * rng.random()
        candidates.append(make(**upd))

    best_inp = base
    best_out: Dict[str, float] = evaluator.evaluate(base).out
    best_ok, best_score = False, float("inf")
    trace: List[Dict[str, Any]] = []

    for idx, inp in enumerate(candidates):
        ev = evaluator.evaluate(inp)
        out = ev.out
        ok, sc, meta = score(inp, out)
        trace.append({
            "i": idx,
            "inputs": {k: float(getattr(inp, k)) for k in lever_keys},
            "ok": bool(ok),
            "score": float(sc),
            "meta": meta,
            "achieved": {k: float(out.get(k, float("nan"))) for k in (targets or {}).keys()},
        })
        if sc < best_score:
            best_score = sc
            best_ok = ok
            best_inp = inp
            best_out = out

    report = {
        "status": "success" if best_ok else "best_effort",
        "best_ok": bool(best_ok),
        "best_score": float(best_score),
        "best_levers": {k: float(getattr(best_inp, k)) for k in lever_keys},
        "targets": targets or {},
        "best_achieved": {k: float(best_out.get(k, float("nan"))) for k in (targets or {}).keys()},
        "trace": trace,
    }
    return FrontierResult(ok=best_ok, best_inputs=best_inp, best_out=best_out, best_score=best_score, report=report)
