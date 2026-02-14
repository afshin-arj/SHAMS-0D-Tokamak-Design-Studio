from __future__ import annotations

"""v351.0 Multi-Objective Feasible Frontier Atlas.

Deterministic, feasibility-first summarization utilities.
Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import math

from models.inputs import PointInputs


def _is_finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def pareto_dominates(a: Dict[str, float], b: Dict[str, float], senses: Dict[str, str]) -> bool:
    """Return True if a dominates b under senses {'obj': 'min'|'max'}."""
    better_or_equal = True
    strictly_better = False
    for k, s in senses.items():
        va = float(a.get(k, float('nan')))
        vb = float(b.get(k, float('nan')))
        if not (_is_finite(va) and _is_finite(vb)):
            return False
        if s == 'min':
            if va > vb:
                better_or_equal = False
            elif va < vb:
                strictly_better = True
        else:
            if va < vb:
                better_or_equal = False
            elif va > vb:
                strictly_better = True
    return bool(better_or_equal and strictly_better)


def pareto_front(records: List[Dict[str, Any]], objectives: List[str], senses: Dict[str, str]) -> List[Dict[str, Any]]:
    """Extract nondominated records based on objective columns."""
    pts = []
    for r in records:
        ok = True
        p: Dict[str, float] = {}
        for o in objectives:
            v = r.get(o, float('nan'))
            try:
                p[o] = float(v)
            except Exception:
                ok = False
                break
            if not _is_finite(p[o]):
                ok = False
                break
        if ok:
            pts.append((r, p))

    front: List[Dict[str, Any]] = []
    for i, (ri, pi) in enumerate(pts):
        dominated = False
        for j, (rj, pj) in enumerate(pts):
            if i == j:
                continue
            if pareto_dominates(pj, pi, senses):
                dominated = True
                break
        if not dominated:
            front.append(ri)
    return front


@dataclass(frozen=True)
class LaneSummary:
    optimistic_verdict: str
    robust_verdict: str
    optimistic_worst_margin_frac: float
    robust_worst_margin_frac: float


def reconstruct_pointinputs(base_inputs: Dict[str, Any], row: Dict[str, Any]) -> PointInputs:
    """Reconstruct PointInputs from base + overriding any matching keys in row."""
    dd = dict(base_inputs)
    for k, v in row.items():
        if k in dd:
            try:
                dd[k] = float(v)
            except Exception:
                pass
    return PointInputs(**dd)


def classify_lanes_for_points(
    *,
    evaluator: Any,
    base_inputs: Dict[str, Any],
    rows: List[Dict[str, Any]],
    optimistic_contract_fn: Any,
    robust_contract_fn: Any,
    run_uq_fn: Any,
    label_prefix: str = "v351",
    max_points: int = 200,
) -> List[Dict[str, Any]]:
    """Deterministically classify a set of rows under optimistic and robust lanes.

    This function is intentionally budgeted; it annotates at most max_points rows.
    Rows beyond the budget are returned unchanged.
    """
    out_rows: List[Dict[str, Any]] = []
    n = min(len(rows), int(max_points))
    for i, r in enumerate(rows):
        if i >= n:
            out_rows.append(dict(r))
            continue

        inp = reconstruct_pointinputs(base_inputs, r)

        # Nominal feasibility already in r (expected). Lane classification uses UQ contracts.
        try:
            opt_spec = optimistic_contract_fn(inp)
            opt = run_uq_fn(inp, opt_spec, label_prefix=f"{label_prefix}_O")
            opt_s = dict(opt.get('summary', {}) or {})
        except Exception:
            opt_s = {}

        try:
            rob_spec = robust_contract_fn(inp)
            rob = run_uq_fn(inp, rob_spec, label_prefix=f"{label_prefix}_R")
            rob_s = dict(rob.get('summary', {}) or {})
        except Exception:
            rob_s = {}

        def _wm(d: Dict[str, Any]) -> float:
            x = d.get('worst_hard_margin_frac', None)
            try:
                return float(x) if x is not None else float('nan')
            except Exception:
                return float('nan')

        rr = dict(r)
        rr['lane_optimistic_verdict'] = str(opt_s.get('verdict', ''))
        rr['lane_robust_verdict'] = str(rob_s.get('verdict', ''))
        rr['lane_optimistic_worst_margin_frac'] = float(_wm(opt_s))
        rr['lane_robust_worst_margin_frac'] = float(_wm(rob_s))
        rr['is_mirage'] = bool(rr['lane_optimistic_verdict'] == 'ROBUST_PASS' and rr['lane_robust_verdict'] != 'ROBUST_PASS')
        rr['is_robust'] = bool(rr['lane_robust_verdict'] == 'ROBUST_PASS')
        out_rows.append(rr)

    return out_rows


def bin_counts(
    rows: Iterable[Dict[str, Any]],
    x_key: str,
    y_key: str,
    *,
    x_bins: int = 12,
    y_bins: int = 12,
    x_range: Optional[Tuple[float, float]] = None,
    y_range: Optional[Tuple[float, float]] = None,
    predicate: Optional[Any] = None,
) -> Dict[str, Any]:
    """2D binning count map (deterministic) for empty-region detection."""
    pts: List[Tuple[float, float]] = []
    for r in rows:
        if predicate is not None and not bool(predicate(r)):
            continue
        try:
            x = float(r.get(x_key, float('nan')))
            y = float(r.get(y_key, float('nan')))
        except Exception:
            continue
        if not (_is_finite(x) and _is_finite(y)):
            continue
        pts.append((x, y))

    if len(pts) == 0:
        return {
            'x_key': x_key,
            'y_key': y_key,
            'x_bins': int(x_bins),
            'y_bins': int(y_bins),
            'counts': [[0 for _ in range(int(x_bins))] for __ in range(int(y_bins))],
            'empty_cells': int(x_bins) * int(y_bins),
            'total_points': 0,
        }

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    xlo, xhi = (min(xs), max(xs)) if x_range is None else (float(x_range[0]), float(x_range[1]))
    ylo, yhi = (min(ys), max(ys)) if y_range is None else (float(y_range[0]), float(y_range[1]))

    # guard degenerate ranges
    if not _is_finite(xlo) or not _is_finite(xhi) or xhi <= xlo:
        xhi = xlo + 1.0
    if not _is_finite(ylo) or not _is_finite(yhi) or yhi <= ylo:
        yhi = ylo + 1.0

    xb = max(2, int(x_bins))
    yb = max(2, int(y_bins))
    counts = [[0 for _ in range(xb)] for __ in range(yb)]

    for x, y in pts:
        ix = int(math.floor((x - xlo) / (xhi - xlo) * xb))
        iy = int(math.floor((y - ylo) / (yhi - ylo) * yb))
        ix = min(max(ix, 0), xb - 1)
        iy = min(max(iy, 0), yb - 1)
        counts[iy][ix] += 1

    empty = sum(1 for iy in range(yb) for ix in range(xb) if counts[iy][ix] == 0)

    return {
        'x_key': x_key,
        'y_key': y_key,
        'x_bins': xb,
        'y_bins': yb,
        'x_range': [float(xlo), float(xhi)],
        'y_range': [float(ylo), float(yhi)],
        'counts': counts,
        'empty_cells': int(empty),
        'total_points': int(len(pts)),
    }
