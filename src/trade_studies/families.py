from __future__ import annotations

"""Design family classification and summaries (v303.0).

This is a deterministic, rule-based family atlas. We avoid iterative clustering
to keep results audit-stable and easy to explain.

Families are intended to be helpful *narrative* buckets, not physics truth.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class FamilyDef:
    key: str
    title: str
    notes: str


FAMILIES: List[FamilyDef] = [
    FamilyDef("compact_hf", "Compact high-field (HTS-leaning)", "High B0 and smaller R0; often magnet/exhaust limited."),
    FamilyDef("conservative_lr", "Conservative large-R", "Larger R0 with moderate B0; tends to trade size for margins."),
    FamilyDef("high_current", "High-current", "Elevated Ip; often control/stability and q/β constraints tighten."),
    FamilyDef("balanced", "Balanced", "Neither extreme; useful baseline family."),
]


def classify_family(row: Dict[str, Any]) -> str:
    """Deterministic family classifier.

    Inputs:
      row: a trade study record containing some of: R0_m, Bt_T, Ip_MA

    Logic:
      - Compact high-field: B0 high and R0 small
      - Conservative large-R: R0 large and B0 moderate
      - High-current: Ip high
      - Otherwise: balanced
    """
    def _f(k: str) -> float:
        try:
            return float(row.get(k, float("nan")))
        except Exception:
            return float("nan")

    r0 = _f("R0_m")
    b0 = _f("Bt_T")
    ip = _f("Ip_MA")

    # Use fixed physical-ish thresholds; avoids dependence on sample distribution.
    if (b0 == b0) and (r0 == r0):
        if b0 >= 8.0 and r0 <= 4.5:
            return "compact_hf"
        if r0 >= 6.5 and b0 <= 7.0:
            return "conservative_lr"
    if ip == ip and ip >= 18.0:
        return "high_current"
    return "balanced"


def attach_families(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return new records with a 'family' field (stable)."""
    out: List[Dict[str, Any]] = []
    for r in records:
        rr = dict(r)
        rr["family"] = classify_family(rr)
        out.append(rr)
    return out


def family_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize counts and feasible yields per family."""
    counts: Dict[str, int] = {}
    feas: Dict[str, int] = {}
    for r in records:
        f = str(r.get("family", "")) or classify_family(r)
        counts[f] = counts.get(f, 0) + 1
        if bool(r.get("is_feasible", False)):
            feas[f] = feas.get(f, 0) + 1

    rows: List[Dict[str, Any]] = []
    for fd in FAMILIES:
        n = int(counts.get(fd.key, 0))
        nf = int(feas.get(fd.key, 0))
        frac = float(nf) / float(n) if n > 0 else 0.0
        rows.append({
            "family": fd.key,
            "title": fd.title,
            "n": n,
            "n_feasible": nf,
            "feasible_frac": frac,
            "notes": fd.notes,
        })
    return {
        "schema": "design_families.v1",
        "rows": rows,
    }
