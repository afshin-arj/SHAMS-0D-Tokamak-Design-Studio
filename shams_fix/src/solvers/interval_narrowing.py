"""Interval Narrowing & Repair Contracts (v343.0).

Explanatory-only: proposes interval narrowing and repair contracts from
evaluated candidate sets. All suggestions must be re-verified with frozen truth.

Design laws:
- Deterministic.
- No solvers/iteration inside truth.
- No hidden relaxation; narrowing is advisory only.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class NarrowingSuggestion:
    var: str
    current_interval: Tuple[float, float]
    suggested_interval: Tuple[float, float]
    pass_density: float
    dead_bins: int
    rationale: str


@dataclass(frozen=True)
class DeadBin:
    var: str
    bin_index: int
    lo: float
    hi: float
    n_total: int
    n_pass: int


def _as_float(x: Any) -> Optional[float]:
    try:
        v = float(x)
        if v != v:  # NaN
            return None
        return v
    except Exception:
        return None


def _quantile(xs: Sequence[float], q: float) -> float:
    """Deterministic nearest-rank quantile for small samples."""
    if not xs:
        return float("nan")
    y = sorted(float(v) for v in xs)
    q = float(max(0.0, min(1.0, q)))
    k = int(round(q * (len(y) - 1)))
    return float(y[max(0, min(len(y) - 1, k))])


def propose_interval_narrowing(
    variables: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    *,
    bins: int = 12,
    min_samples_per_bin: int = 2,
    pass_quantile_lo: float = 0.05,
    pass_quantile_hi: float = 0.95,
    max_suggestions: int = 8,
) -> Dict[str, Any]:
    """Propose interval narrowing suggestions from evaluated records.

    Args:
        variables: list of {name, lo, hi} (e.g., from certified search spec).
        records: list of {x: {var: value}, verdict: PASS/FAIL, evidence: {...}}.

    Returns:
        Evidence dict schema_version=interval_narrowing_evidence.v1.
    """

    vars_ = []
    for v in variables:
        name = str(v.get("name"))
        lo = _as_float(v.get("lo"))
        hi = _as_float(v.get("hi"))
        if not name or lo is None or hi is None or hi <= lo:
            continue
        vars_.append((name, float(lo), float(hi)))

    # Extract samples
    samples: List[Dict[str, Any]] = []
    for r in records:
        x = r.get("x") or {}
        if not isinstance(x, dict):
            continue
        verdict = str(r.get("verdict", "")).upper()
        is_pass = verdict == "PASS"
        row = {"is_pass": is_pass, "x": x, "evidence": (r.get("evidence") or {})}
        samples.append(row)

    n_total = len(samples)
    n_pass = sum(1 for s in samples if s["is_pass"])
    repairability = "REPAIRABLE" if n_pass > 0 else "STRUCTURALLY_INFEASIBLE"

    dead_bins: List[DeadBin] = []
    suggestions: List[NarrowingSuggestion] = []

    for (name, lo, hi) in vars_:
        width = float(hi - lo)
        if width <= 0:
            continue
        b = int(max(4, min(50, bins)))
        counts = [{"n": 0, "p": 0} for _ in range(b)]
        pass_vals: List[float] = []
        for s in samples:
            xv = _as_float((s["x"] or {}).get(name))
            if xv is None:
                continue
            # clamp to declared range
            xvc = float(min(max(xv, lo), hi))
            t = 0.0 if width == 0 else (xvc - lo) / width
            idx = int(min(b - 1, max(0, int(t * b))))
            counts[idx]["n"] += 1
            if s["is_pass"]:
                counts[idx]["p"] += 1
                pass_vals.append(xvc)

        # dead bins are those with enough samples but zero PASS
        n_dead = 0
        for i, c in enumerate(counts):
            if int(c["n"]) >= int(min_samples_per_bin) and int(c["p"]) == 0:
                n_dead += 1
                blo = lo + (i / b) * width
                bhi = lo + ((i + 1) / b) * width
                dead_bins.append(DeadBin(var=name, bin_index=i, lo=float(blo), hi=float(bhi), n_total=int(c["n"]), n_pass=0))

        # If we have PASS points, suggest interval spanning central quantiles.
        if pass_vals:
            qlo = _quantile(pass_vals, float(pass_quantile_lo))
            qhi = _quantile(pass_vals, float(pass_quantile_hi))
            # Expand slightly to avoid over-tightening.
            pad = 0.05 * width
            sug_lo = float(max(lo, qlo - pad))
            sug_hi = float(min(hi, qhi + pad))
            if sug_hi <= sug_lo:
                sug_lo, sug_hi = lo, hi
            # pass density proxy: PASS / total within suggested range
            in_rng = 0
            in_pass = 0
            for s in samples:
                xv = _as_float((s["x"] or {}).get(name))
                if xv is None:
                    continue
                if float(sug_lo) <= float(xv) <= float(sug_hi):
                    in_rng += 1
                    if s["is_pass"]:
                        in_pass += 1
            dens = float(in_pass) / float(max(1, in_rng))
            rationale = (
                f"PASS points concentrate in [{sug_lo:.4g}, {sug_hi:.4g}] (central quantiles) "
                f"with pass-density≈{dens:.2f}. Dead bins={n_dead}/{b}. "
                "Narrowing is advisory only; re-verify with frozen truth."
            )
            suggestions.append(
                NarrowingSuggestion(
                    var=name,
                    current_interval=(float(lo), float(hi)),
                    suggested_interval=(float(sug_lo), float(sug_hi)),
                    pass_density=float(dens),
                    dead_bins=int(n_dead),
                    rationale=rationale,
                )
            )
        else:
            # No PASS points: suggest nothing (do not invent feasible region)
            continue

    # Rank suggestions: lowest pass density first? Actually want best improvement: prioritize low density + many dead bins
    suggestions.sort(key=lambda s: (-s.dead_bins, s.pass_density, s.var))
    suggestions = suggestions[: max(0, int(max_suggestions))]

    evidence = {
        "schema_version": "interval_narrowing_evidence.v1",
        "n_total": int(n_total),
        "n_pass": int(n_pass),
        "repairability": str(repairability),
        "parameters": {
            "bins": int(bins),
            "min_samples_per_bin": int(min_samples_per_bin),
            "pass_quantile_lo": float(pass_quantile_lo),
            "pass_quantile_hi": float(pass_quantile_hi),
        },
        "variables": [{"name": n, "lo": float(lo), "hi": float(hi)} for (n, lo, hi) in vars_],
        "dead_bins": [
            {
                "var": db.var,
                "bin_index": int(db.bin_index),
                "lo": float(db.lo),
                "hi": float(db.hi),
                "n_total": int(db.n_total),
                "n_pass": int(db.n_pass),
            }
            for db in dead_bins
        ],
        "suggestions": [
            {
                "var": s.var,
                "current_interval": [float(s.current_interval[0]), float(s.current_interval[1])],
                "suggested_interval": [float(s.suggested_interval[0]), float(s.suggested_interval[1])],
                "pass_density": float(s.pass_density),
                "dead_bins": int(s.dead_bins),
                "rationale": str(s.rationale),
            }
            for s in suggestions
        ],
    }
    return evidence


def build_repair_contract(
    base_intervals: Mapping[str, Tuple[float, float]],
    *,
    allowed_knobs: Optional[Sequence[str]] = None,
    max_delta_frac: float = 0.10,
    forbid_relaxation: bool = True,
    notes: str = "",
) -> Dict[str, Any]:
    """Create a deterministic repair contract payload.

    The repair contract is a governance artifact describing *allowed* reformulations
    (knob moves and interval narrowing) without mutating truth.
    """
    ak = list(allowed_knobs) if allowed_knobs else sorted(list(base_intervals.keys()))
    return {
        "schema_version": "repair_contract.v1",
        "forbid_constraint_relaxation": bool(forbid_relaxation),
        "max_delta_frac": float(max_delta_frac),
        "allowed_knobs": list(ak),
        "base_intervals": {k: [float(v[0]), float(v[1])] for k, v in sorted(base_intervals.items())},
        "notes": str(notes or "").strip(),
    }
