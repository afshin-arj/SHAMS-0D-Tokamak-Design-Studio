from __future__ import annotations

"""Frontier family narratives (v246.0).

Generate a compact, publication-friendly narrative for a frontier-family run
(boundary_trace_multi) including:

- island list ordered by robustness envelope
- dominant mechanism composition per island
- mechanism switch-point statistics per island
- cross-island mechanism coverage

Inputs
------
- frontier_family_summary.json
- frontiers/frontier_island_<id>.csv

Outputs
-------
- dict (JSON-serializable) + markdown narrative string.

This is analysis-layer only. It does not modify physics truth.

© 2026 Afshin Arjhangmehr
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import math

def _as_str(x: Any, default: str = "—") -> str:
    try:
        s = str(x)
        return s if s.strip() else default
    except Exception:
        return default

def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")

def _finite(x: float) -> bool:
    return isinstance(x, float) and math.isfinite(x)

def build_frontier_family_narrative(
    run_dir: Path,
    *,
    max_islands: int = 12,
    mech_col_preference: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], str]:
    mech_col_preference = mech_col_preference or ["dominant_mechanism_group", "dominant_mechanism"]
    summary_path = run_dir / "frontier_family_summary.json"
    frontiers_dir = run_dir / "frontiers"
    if not summary_path.exists():
        return ({"ok": False, "reason": "missing_frontier_family_summary"}, "")

    try:
        fam = __import__("json").loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        fam = {}

    islands = fam.get("islands") if isinstance(fam, dict) else None
    if not isinstance(islands, list):
        islands = []

    # load csvs and compute envelope/switch stats
    try:
        import pandas as pd  # type: ignore
    except Exception:
        pd = None  # type: ignore

    rows: List[Dict[str, Any]] = []
    mech_global: Dict[str, int] = {}

    for isl in islands[:max_islands]:
        if not isinstance(isl, dict):
            continue
        iid = _as_str(isl.get("island_id"), "none")
        csv_path = frontiers_dir / f"frontier_island_{iid}.csv"
        if not csv_path.exists() or pd is None:
            continue
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            continue

        mech_col = None
        for c in mech_col_preference:
            if c in df.columns:
                mech_col = c
                break

        max_margin = float("nan")
        obj_at_max = float("nan")
        n = int(len(df))
        if n > 0 and "worst_hard_margin" in df.columns:
            try:
                max_margin = float(df["worst_hard_margin"].astype(float).max())
                if "objective" in df.columns:
                    j = int(df["worst_hard_margin"].astype(float).idxmax())
                    obj_at_max = float(df.loc[j, "objective"])
            except Exception:
                pass

        n_switch = 0
        top_mech = "—"
        if mech_col:
            try:
                seq = [_as_str(x) for x in df[mech_col].fillna("—").tolist()]
                # switches
                for a, b in zip(seq[:-1], seq[1:]):
                    if a != b:
                        n_switch += 1
                # counts
                counts: Dict[str, int] = {}
                for s in seq:
                    counts[s] = counts.get(s, 0) + 1
                    mech_global[s] = mech_global.get(s, 0) + 1
                top_mech = sorted(counts.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))[0][0] if counts else "—"
            except Exception:
                pass

        rows.append({
            "island_id": iid,
            "frontier_n": n,
            "max_worst_hard_margin": max_margin,
            "objective_at_max_margin": obj_at_max,
            "top_mechanism": top_mech,
            "mechanism_switches": int(n_switch),
        })

    # robustness envelope ranking
    def _rank_key(r: Dict[str, Any]):
        mm = _safe_float(r.get("max_worst_hard_margin"))
        obj = _safe_float(r.get("objective_at_max_margin"))
        return (-mm if _finite(mm) else 1e9, obj if _finite(obj) else 1e9)

    rows_sorted = sorted(rows, key=_rank_key)

    mech_cov = sorted(mech_global.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))[:20]

    narrative = []
    narrative.append("# Frontier Family Narrative")
    narrative.append("")
    narrative.append("This narrative is generated deterministically from the frozen evaluator outputs (feasible-only frontier points). It does not perform optimization inside truth.")
    narrative.append("")
    if rows_sorted:
        narrative.append("## Island ranking (robustness envelope)")
        narrative.append("Ranking rule: maximize max(worst_hard_margin) first; tie-break by objective_at_max_margin.")
        narrative.append("")
        narrative.append("| island | frontier_n | max worst hard margin | objective@max | top mechanism | mech switches |" )
        narrative.append("|---:|---:|---:|---:|---|---:|")
        for r in rows_sorted[:max_islands]:
            narrative.append(
                f"| {r['island_id']} | {r['frontier_n']} | {r['max_worst_hard_margin']:.4g} | {r['objective_at_max_margin']:.4g} | {r['top_mechanism']} | {r['mechanism_switches']} |"
            )
        narrative.append("")
    else:
        narrative.append("No island CSVs were available to build envelope/switch statistics.")
        narrative.append("")

    if mech_cov:
        narrative.append("## Mechanism coverage (across all rendered islands)")
        narrative.append("| mechanism | count |" )
        narrative.append("|---|---:|")
        for m, n in mech_cov:
            narrative.append(f"| {m} | {int(n)} |")
        narrative.append("")

    out = {
        "ok": True,
        "islands_ranked": rows_sorted,
        "mechanism_coverage": [{"mechanism": m, "count": int(n)} for m, n in mech_cov],
    }
    return out, "\n".join(narrative) + "\n"
