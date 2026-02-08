from __future__ import annotations

"""Optimizer Family Gallery utilities.

A *family* is a deterministic grouping of feasible designs, intended for reviewer-safe
summaries and UI browsing. Grouping uses scan-derived seed provenance when available.

This module is UI/client-side only. It must never affect the frozen evaluator.

© 2026 Afshin Arjhangmehr
"""

from typing import Any, Dict, List
import math


def _is_candidate(rec: Dict[str, Any]) -> bool:
    return bool(rec.get("candidate"))


def _island_id_from_inputs(inp: Any) -> int:
    if not isinstance(inp, dict):
        return -1
    meta = inp.get("_seed_meta")
    if isinstance(meta, dict):
        try:
            return int(meta.get("island_id", -1))
        except Exception:
            return -1
    return -1


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _quantiles(xs: List[float], qs: List[float]) -> Dict[str, float]:
    v = [x for x in xs if math.isfinite(x)]
    if not v:
        return {f"q{int(100*q)}": float("nan") for q in qs}
    v.sort()
    n = len(v)
    out: Dict[str, float] = {}
    for q in qs:
        if n == 1:
            out[f"q{int(100*q)}"] = float(v[0])
            continue
        pos = q * (n - 1)
        i0 = int(math.floor(pos))
        i1 = min(n - 1, i0 + 1)
        t = pos - i0
        out[f"q{int(100*q)}"] = float(v[i0] * (1 - t) + v[i1] * t)
    return out


def build_family_gallery(
    records: List[Dict[str, Any]],
    *,
    objective_key: str,
    objective_direction: str,
) -> Dict[str, Any]:
    """Build a deterministic family gallery.

    Families are keyed by island_id when available; otherwise island_id=-1.
    Returns a JSON-serializable dict.
    """
    feas = [r for r in records if isinstance(r, dict) and _is_candidate(r)]
    fams: Dict[int, List[Dict[str, Any]]] = {}
    for r in feas:
        isl = _island_id_from_inputs(r.get("inputs"))
        fams.setdefault(isl, []).append(r)

    families_out: List[Dict[str, Any]] = []
    for isl in sorted(fams.keys()):
        rs = fams[isl]
        worst = [_safe_float(r.get("worst_hard_margin")) for r in rs]
        obj = [_safe_float(r.get("objective")) for r in rs]

        robust_best = max(
            rs,
            key=lambda r: (_safe_float(r.get("worst_hard_margin")), _safe_float(r.get("objective"))),
        )
        obj_best = max(rs, key=lambda r: _safe_float(r.get("objective")))

        def _idx(r: Dict[str, Any]) -> int:
            try:
                return int(records.index(r))
            except Exception:
                return -1

        families_out.append(
            {
                "family_id": int(isl),
                "n_feasible": int(len(rs)),
                "objective_key": str(objective_key),
                "objective_direction": str(objective_direction),
                "worst_hard_margin": {
                    "min": float(min([w for w in worst if math.isfinite(w)], default=float("nan"))),
                    **_quantiles(worst, [0.1, 0.5, 0.9]),
                },
                "objective": {
                    "min": float(min([o for o in obj if math.isfinite(o)], default=float("nan"))),
                    **_quantiles(obj, [0.1, 0.5, 0.9]),
                },
                "representatives": {
                    "robust_best": {
                        "record_index": _idx(robust_best),
                        "worst_hard_margin": _safe_float(robust_best.get("worst_hard_margin")),
                        "objective": _safe_float(robust_best.get("objective")),
                    },
                    "objective_best": {
                        "record_index": _idx(obj_best),
                        "worst_hard_margin": _safe_float(obj_best.get("worst_hard_margin")),
                        "objective": _safe_float(obj_best.get("objective")),
                    },
                },
            }
        )

    return {
        "schema": "optimizer_family_gallery.v1",
        "objective_key": str(objective_key),
        "objective_direction": str(objective_direction),
        "families": families_out,
    }


def render_family_gallery_md(gallery: Dict[str, Any]) -> str:
    fams = gallery.get("families") if isinstance(gallery, dict) else None
    if not isinstance(fams, list) or not fams:
        return "# Optimization Family Gallery\n\nNo feasible families found.\n"
    lines: List[str] = []
    lines.append("# Optimization Family Gallery")
    lines.append("")
    lines.append(f"Objective: `{gallery.get('objective_key')}` ({gallery.get('objective_direction')})")
    lines.append("")
    for f in fams:
        if not isinstance(f, dict):
            continue
        fid = f.get("family_id")
        lines.append(f"## Family {fid}")
        lines.append(f"- Feasible count: {f.get('n_feasible')}")
        wm = f.get("worst_hard_margin", {})
        ob = f.get("objective", {})
        if isinstance(wm, dict):
            lines.append(
                f"- Worst hard margin: min={wm.get('min')}, q10={wm.get('q10')}, q50={wm.get('q50')}, q90={wm.get('q90')}"
            )
        if isinstance(ob, dict):
            lines.append(
                f"- Objective: min={ob.get('min')}, q10={ob.get('q10')}, q50={ob.get('q50')}, q90={ob.get('q90')}"
            )
        reps = f.get("representatives", {})
        if isinstance(reps, dict):
            rb = reps.get("robust_best", {})
            obb = reps.get("objective_best", {})
            if isinstance(rb, dict):
                lines.append(
                    f"- Robust representative: record_index={rb.get('record_index')} (wm={rb.get('worst_hard_margin')}, obj={rb.get('objective')})"
                )
            if isinstance(obb, dict):
                lines.append(
                    f"- Objective representative: record_index={obb.get('record_index')} (wm={obb.get('worst_hard_margin')}, obj={obb.get('objective')})"
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
