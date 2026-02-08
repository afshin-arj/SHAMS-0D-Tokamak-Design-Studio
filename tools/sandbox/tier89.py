"""Optimization Sandbox — Tier 8–9 (world-class differentiators)

This module intentionally implements *instrumentation* and *reasoned verdicts*
around the frozen evaluator outputs.

It never relaxes constraints and never changes the physics truth.

Tier 8
  - Design-space jurisprudence: Allowed / Forbidden / Undecidable.
  - Epistemic confidence bounds on feasibility rates.
  - Intent-conditional design laws (comparative relations).

Tier 9
  - Machine genealogy (ancestry reconstruction from archive).
  - Counter-optimization reports (boundary-limited / no interior optimum).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import math


def _sf(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


# ---------------------------------------------------------------------------
# Epistemic confidence bounds (Wilson interval)
# ---------------------------------------------------------------------------

def wilson_interval(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Args:
        k: successes
        n: trials
        z: standard normal quantile (1.96 ~ 95%)
    """
    if n <= 0:
        return (0.0, 1.0)
    phat = k / n
    denom = 1.0 + (z * z) / n
    center = (phat + (z * z) / (2.0 * n)) / denom
    half = (z / denom) * math.sqrt((phat * (1.0 - phat) / n) + (z * z) / (4.0 * n * n))
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return (float(lo), float(hi))


def feasibility_confidence_from_trace(trace: List[Dict[str, Any]], window: int = 500) -> Dict[str, Any]:
    """Compute feasibility rate + confidence bounds over the last window of trace rows."""
    t = list(trace or [])
    if window and len(t) > window:
        t = t[-window:]
    n = len(t)
    k = 0
    for r in t:
        if bool(r.get("feasible", False)):
            k += 1
    lo, hi = wilson_interval(k, n)
    return {
        "window": int(window),
        "n": int(n),
        "k": int(k),
        "rate": float(k / n) if n > 0 else float("nan"),
        "ci_lo": float(lo),
        "ci_hi": float(hi),
    }


# ---------------------------------------------------------------------------
# Design-space verdicts
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Verdict:
    label: str  # Allowed / Forbidden / Undecidable
    confidence: float
    rationale: str


def candidate_verdict(
    candidate: Dict[str, Any],
    archive: List[Dict[str, Any]],
    var_keys: List[str],
    robust_margin: float = 0.0,
    neighbor_k: int = 12,
) -> Verdict:
    """Verdict for a candidate relative to a local neighborhood in the archive.

    Heuristic but disciplined:
      - Allowed: feasible + margin above threshold.
      - Forbidden: infeasible and its local neighborhood is also uniformly infeasible.
      - Undecidable: anything else (e.g., cliff/fragile).
    """
    feas = bool(candidate.get("feasible", False))
    mm = _sf(candidate.get("min_signed_margin"))
    if feas and (math.isfinite(mm) and mm >= robust_margin):
        # Confidence grows with margin (softly)
        conf = float(max(0.55, min(0.99, 0.55 + 0.4 * math.tanh(mm / max(1e-6, robust_margin + 0.05)))))
        return Verdict("Allowed", conf, f"Feasible with min signed margin {mm:.3g} ≥ {robust_margin:.3g}.")

    # Neighborhood-based forbiddenness
    # Build candidate vector
    x = [_sf(candidate.get("inputs", {}).get(k)) for k in var_keys]
    if not all(math.isfinite(v) for v in x):
        return Verdict("Undecidable", 0.5, "Insufficient numeric information for a local verdict.")

    neigh = []
    for a in archive or []:
        xi = [_sf(a.get("inputs", {}).get(k)) for k in var_keys]
        if not all(math.isfinite(v) for v in xi):
            continue
        d2 = 0.0
        for u, v in zip(x, xi):
            d2 += (u - v) ** 2
        neigh.append((d2, a))
    neigh.sort(key=lambda t: t[0])
    neigh = [a for _, a in neigh[: max(3, int(neighbor_k))]]
    if not neigh:
        return Verdict("Undecidable", 0.5, "No neighborhood evidence available.")

    feas_n = sum(1 for a in neigh if bool(a.get("feasible", False)))
    if (not feas) and feas_n == 0:
        # "Forbidden" here means: locally infeasible within explored neighborhood.
        # Confidence increases with neighborhood size.
        conf = float(min(0.95, 0.55 + 0.4 * (len(neigh) / max(1.0, float(neighbor_k)))))
        fm = candidate.get("failure_mode") or "infeasible"
        return Verdict("Forbidden", conf, f"Candidate and its {len(neigh)} nearest explored neighbors are infeasible (local). Failure mode: {fm}.")

    # Otherwise, we are on a cliff or data is mixed.
    if feas:
        return Verdict("Undecidable", 0.65, f"Feasible but fragile/near a cliff (min signed margin {mm:.3g} < {robust_margin:.3g}).")
    return Verdict("Undecidable", 0.6, f"Neighborhood contains feasible points (feasible neighbors: {feas_n}/{len(neigh)}); this region is not proven forbidden.")


def region_verdict(trace: List[Dict[str, Any]], window: int = 500, z: float = 1.96) -> Verdict:
    """Verdict for the explored region based on recent feasibility rate."""
    ci = feasibility_confidence_from_trace(trace, window=window)
    n = int(ci.get("n", 0))
    k = int(ci.get("k", 0))
    if n <= 0:
        return Verdict("Undecidable", 0.5, "No evaluations recorded yet.")
    # If zero feasible in a sizeable window, we treat the explored region as locally forbidden.
    if k == 0 and n >= 80:
        # Upper bound from Wilson
        conf = float(min(0.95, 0.6 + 0.35 * (n / 500.0)))
        return Verdict("Forbidden", conf, f"No feasible points in the last {n} evaluations (95% upper CI on feasible rate ≈ {ci['ci_hi']:.3g}).")
    if k > 0:
        return Verdict("Allowed", float(max(0.6, min(0.98, ci['rate'] + 0.25))), f"Feasible points exist in the explored region (recent feasible rate {ci['rate']:.3g} with 95% CI [{ci['ci_lo']:.3g}, {ci['ci_hi']:.3g}]).")
    return Verdict("Undecidable", 0.6, f"Few/no feasible points in the last {n} evaluations; insufficient evidence to declare forbidden.")


# ---------------------------------------------------------------------------
# Intent-conditional design laws (comparative)
# ---------------------------------------------------------------------------

def intent_conditional_laws(
    evaluate_fn_other_intent,
    archive: List[Dict[str, Any]],
    var_keys: List[str],
    key_y: str,
    top_n: int = 40,
) -> Dict[str, Any]:
    """Compare a simple relation under primary intent vs other intent.

    This is a conservative, explainable method:
    - Select top_n feasible candidates from archive.
    - Evaluate them under the other intent.
    - Compute correlations (Pearson) between each var and y under both intents.
    """

    # pick best feasible by score if available, else by margin
    feas = [a for a in (archive or []) if bool(a.get("feasible", False))]
    feas.sort(key=lambda a: float(a.get("_score", -1e30)), reverse=True)
    feas = feas[: int(max(5, top_n))]

    def _collect(rows: List[Dict[str, Any]]) -> Tuple[List[float], Dict[str, List[float]]]:
        ys = []
        xs: Dict[str, List[float]] = {k: [] for k in var_keys}
        for r in rows:
            y = _sf((r.get("outputs") or {}).get(key_y))
            if not math.isfinite(y):
                continue
            ok = True
            vals = {}
            for k in var_keys:
                v = _sf((r.get("inputs") or {}).get(k))
                if not math.isfinite(v):
                    ok = False
                    break
                vals[k] = v
            if not ok:
                continue
            ys.append(y)
            for k in var_keys:
                xs[k].append(vals[k])
        return ys, xs

    # primary intent data
    y1, x1 = _collect(feas)
    # other intent evaluation
    other_rows = []
    for r in feas:
        try:
            other_rows.append(evaluate_fn_other_intent(dict((r.get("inputs") or {}))))
        except Exception:
            continue
    other_rows = [r for r in other_rows if isinstance(r, dict)]
    y2, x2 = _collect(other_rows)

    def _corr(a: List[float], b: List[float]) -> float:
        if len(a) < 5 or len(b) < 5 or len(a) != len(b):
            return float("nan")
        ma = sum(a) / len(a)
        mb = sum(b) / len(b)
        num = sum((u - ma) * (v - mb) for u, v in zip(a, b))
        da = math.sqrt(sum((u - ma) ** 2 for u in a))
        db = math.sqrt(sum((v - mb) ** 2 for v in b))
        if da <= 0 or db <= 0:
            return float("nan")
        return float(num / (da * db))

    out = []
    for k in var_keys:
        c1 = _corr(x1.get(k, []), y1)
        c2 = _corr(x2.get(k, []), y2)
        out.append({"var": k, "corr_primary": c1, "corr_other": c2, "delta": (c2 - c1) if (math.isfinite(c1) and math.isfinite(c2)) else float("nan")})
    out.sort(key=lambda r: abs(float(r.get("delta", 0.0))) if math.isfinite(_sf(r.get("delta"))) else -1.0, reverse=True)
    return {
        "key_y": str(key_y),
        "n_primary": int(len(y1)),
        "n_other": int(len(y2)),
        "rows": out,
    }


# ---------------------------------------------------------------------------
# Genealogy (ancestry reconstruction)
# ---------------------------------------------------------------------------

def reconstruct_genealogy(
    archive: List[Dict[str, Any]],
    var_keys: List[str],
    max_children_per_parent: int = 12,
) -> Dict[str, Any]:
    """Reconstruct an ancestry graph from the archive.

    Since not all engines record parents explicitly, we conservatively build a
    plausible lineage: each candidate's parent is its nearest *better* neighbor
    in variable space.
    """
    rows = []
    for i, a in enumerate(archive or []):
        inp = a.get("inputs") or {}
        x = [_sf(inp.get(k)) for k in var_keys]
        if not all(math.isfinite(v) for v in x):
            continue
        rows.append((i, a, x))

    # Define "better" by feasibility then score.
    def _rank(a: Dict[str, Any]) -> Tuple[int, float]:
        feas = 0 if bool(a.get("feasible", False)) else 1
        sc = _sf(a.get("_score", -1e30))
        return (feas, -sc)

    rows_sorted = sorted(rows, key=lambda t: _rank(t[1]))
    # Map from original index to position in sorted order
    pos = {idx: p for p, (idx, _, _) in enumerate(rows_sorted)}

    parents: Dict[int, Optional[int]] = {}
    children: Dict[int, List[int]] = {}

    for idx, a, x in rows_sorted:
        # Root candidates have no better predecessor
        best_parent = None
        best_d2 = float("inf")
        # Only search among candidates that are better (earlier in sorted)
        for jdx, b, y in rows_sorted[: pos[idx]]:
            d2 = 0.0
            for u, v in zip(x, y):
                d2 += (u - v) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best_parent = jdx
        parents[idx] = best_parent
        if best_parent is not None:
            children.setdefault(best_parent, []).append(idx)

    # Prune too-wide parents to keep UI readable
    pruned_children = {}
    for p, ch in children.items():
        if len(ch) <= max_children_per_parent:
            pruned_children[p] = ch
        else:
            pruned_children[p] = ch[:max_children_per_parent]

    roots = [idx for idx, _a, _x in rows_sorted if parents.get(idx) is None]
    return {
        "roots": roots,
        "parents": parents,
        "children": pruned_children,
        "var_keys": list(var_keys),
    }


# ---------------------------------------------------------------------------
# Counter-optimization (no interior optimum heuristics)
# ---------------------------------------------------------------------------

def counter_optimization_report(
    archive: List[Dict[str, Any]],
    key_obj: Optional[str] = None,
    min_margin_key: str = "min_signed_margin",
) -> Dict[str, Any]:
    """Heuristic report: whether improvements are boundary-limited.

    We do not claim global proofs. We claim *evidence*.

    Signals:
      - Best scores occur at very small margins.
      - Negative correlation between score and margin.
      - Objective increases toward bounds for at least one variable.
    """
    feas = [a for a in (archive or []) if bool(a.get("feasible", False))]
    if not feas:
        return {"status": "no_feasible", "message": "No feasible candidates in archive; cannot assess optimality structure."}

    # Choose objective key
    if key_obj is None:
        key_obj = "_score"

    scores = []
    margins = []
    for a in feas:
        s = _sf(a.get(key_obj)) if key_obj in a else _sf(a.get("_score"))
        m = _sf(a.get(min_margin_key))
        if math.isfinite(s) and math.isfinite(m):
            scores.append(s)
            margins.append(m)
    if len(scores) < 8:
        return {"status": "insufficient", "message": "Insufficient feasible samples to assess boundary limitation."}

    # correlation
    ms = sum(margins) / len(margins)
    ss = sum(scores) / len(scores)
    num = sum((m - ms) * (s - ss) for m, s in zip(margins, scores))
    dm = math.sqrt(sum((m - ms) ** 2 for m in margins))
    ds = math.sqrt(sum((s - ss) ** 2 for s in scores))
    corr = float(num / (dm * ds)) if dm > 0 and ds > 0 else float("nan")

    # boundary evidence: top-10 scores have low margin
    top = sorted(zip(scores, margins), key=lambda t: t[0], reverse=True)[: max(5, min(15, len(scores)//3))]
    top_m = [m for _s, m in top]
    frac_near = sum(1 for m in top_m if m < 0.03) / len(top_m)

    boundary_limited = (math.isfinite(corr) and corr < -0.25) or (frac_near >= 0.5)
    msg = "Boundary-limited evidence" if boundary_limited else "No strong boundary-limited evidence"
    rationale = []
    if math.isfinite(corr):
        rationale.append(f"corr(score, margin)={corr:.3g}")
    rationale.append(f"fraction of top candidates with margin < 0.03: {frac_near:.2f}")

    return {
        "status": "ok",
        "objective": str(key_obj),
        "corr_score_margin": corr,
        "top_margin_fraction_lt_0p03": float(frac_near),
        "boundary_limited": bool(boundary_limited),
        "message": msg,
        "rationale": "; ".join(rationale),
    }
