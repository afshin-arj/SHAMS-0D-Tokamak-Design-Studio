"""SHAMS Reactor Design Forge — Reality Gates

Declared, toggleable 'engineering reality' checks built from *existing* constraint
records and/or derived closure metrics.

These gates are explicit and auditable. They do not change frozen truth.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _gate(name: str, ok: bool, margin: Optional[float] = None, note: str = "") -> Dict[str, Any]:
    return {
        "name": str(name),
        "status": "PASS" if ok else "FAIL",
        "margin": float(margin) if margin is not None else None,
        "note": str(note) if note else "",
    }


def reality_gates(constraint_records: List[Dict[str, Any]], closure_bundle: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Compute a starter set of reality gates.

    This starter set intentionally reuses core constraints that experts consider
    'buildability gates'. Projects can extend this list later, but it is crucial
    these remain declared and visible.
    """
    recs = constraint_records or []
    by_name = {str(r.get("name")): r for r in recs if r.get("name")}

    out = {
        "schema": "shams.reactor_design_forge.reality_gates.v1",
        "gates": [],
        "notes": [
            "Gates are descriptive PASS/FAIL checks derived from frozen-truth constraints/closure.",
            "They do not change feasibility truth and are safe to disable for analysis.",
        ],
    }

    # Core: treat signed_margin>=0 as PASS where available.
    for key in ["q_div", "sigma_vm", "HTS margin", "TBR", "q95"]:
        r = by_name.get(key)
        if not r:
            continue
        sm = r.get("signed_margin")
        try:
            smf = float(sm)
        except Exception:
            smf = None
        out["gates"].append(_gate(key, ok=(smf is not None and smf >= 0.0), margin=smf))

    # Net-electric gate if closure bundle is present
    if isinstance(closure_bundle, dict):
        try:
            pnet = float(closure_bundle.get("net_electric_MW"))
            out["gates"].append(_gate("Net electric", ok=(pnet > 0.0), margin=pnet, note="MW"))
        except Exception:
            pass

    return out
