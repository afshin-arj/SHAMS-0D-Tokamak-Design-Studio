from __future__ import annotations
"""Robustness Certificate (v141)

A scientific authority object derived from:
- v139 Feasibility Certificate (truth object)
- v140 Sensitivity Report (fragility envelopes)

Goal:
Quantify how robust a feasible design is to perturbations of selected variables.
No optimization, no gradients — uses already computed sensitivity boundaries.

Inputs:
- feasibility_certificate: dict (kind=shams_feasibility_certificate, version=v139)
- sensitivity_report: dict (kind=shams_sensitivity_report, version=v140)

Outputs:
- robustness_certificate_v141.json (audit-ready)
"""

import time, uuid, json, hashlib
from typing import Any, Dict, List, Optional

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha(x: Any) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, default=str).encode("utf-8")).hexdigest()

def _safe_float(x):
    try:
        if x is None: return None
        if isinstance(x, bool): return None
        return float(x)
    except Exception:
        return None

def _extract_bounds(res: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Normalize v140 results into per-var +/- boundary rel (if bounded)."""
    out={}
    for r in (res.get("results") or []):
        if not isinstance(r, dict): 
            continue
        v=str(r.get("var"))
        m=r.get("minus", {}) if isinstance(r.get("minus"), dict) else {}
        p=r.get("plus", {}) if isinstance(r.get("plus"), dict) else {}
        out[v] = {
            "x0": _safe_float(r.get("x0")),
            "minus_status": m.get("status"),
            "minus_boundary_rel": _safe_float(m.get("boundary_rel")),
            "minus_boundary_x": _safe_float(m.get("boundary_x")),
            "plus_status": p.get("status"),
            "plus_boundary_rel": _safe_float(p.get("boundary_rel")),
            "plus_boundary_x": _safe_float(p.get("boundary_x")),
        }
    return out

def _robustness_index(bounds: Dict[str, Dict[str, Any]]) -> Optional[float]:
    vals=[]
    for v, b in bounds.items():
        if not isinstance(b, dict): 
            continue
        if b.get("minus_status") == "bounded" and b.get("plus_status") == "bounded":
            mn=abs(float(b.get("minus_boundary_rel") or 0.0))
            pl=abs(float(b.get("plus_boundary_rel") or 0.0))
            vals.append(min(mn, pl))
    if not vals:
        return None
    return float(min(vals))

def generate_robustness_certificate(
    feasibility_certificate: Dict[str, Any],
    sensitivity_report: Dict[str, Any],
    policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    # Minimal compatibility checks
    if not (isinstance(feasibility_certificate, dict) and feasibility_certificate.get("kind") == "shams_feasibility_certificate"):
        raise ValueError("feasibility_certificate kind mismatch")
    if not (isinstance(sensitivity_report, dict) and sensitivity_report.get("kind") == "shams_sensitivity_report"):
        raise ValueError("sensitivity_report kind mismatch")

    created = _utc()
    policy = dict(policy or {})
    bounds = _extract_bounds(sensitivity_report)

    # Determine a robustness index: min bounded +/- relative variation across vars
    idx = _robustness_index(bounds)

    # Rank fragility (smallest min(+,-) first), only where bounded both sides
    frag=[]
    for v,b in bounds.items():
        if b.get("minus_status") == "bounded" and b.get("plus_status") == "bounded":
            mn=abs(float(b.get("minus_boundary_rel") or 0.0))
            pl=abs(float(b.get("plus_boundary_rel") or 0.0))
            frag.append((min(mn,pl), v, mn, pl))
    frag_sorted=[{"var": v, "min_rel": m, "minus_rel": mn, "plus_rel": pl} for (m,v,mn,pl) in sorted(frag, key=lambda t: t[0])]

    cert = {
        "kind": "shams_robustness_certificate",
        "version": "v141",
        "certificate_id": str(uuid.uuid4()),
        "issued_utc": created,

        "references": {
            "feasibility_certificate_sha256": _sha(feasibility_certificate),
            "sensitivity_report_sha256": _sha(sensitivity_report),
        },

        "feasibility_summary": {
            "worst_hard": feasibility_certificate.get("worst_hard") if "worst_hard" in feasibility_certificate else feasibility_certificate.get("dominance", {}).get("worst_constraint"),
            "worst_hard_margin_frac": feasibility_certificate.get("worst_hard_margin_frac") if "worst_hard_margin_frac" in feasibility_certificate else feasibility_certificate.get("dominance", {}).get("worst_margin_frac"),
        },

        "baseline": {
            "sensitivity_baseline": sensitivity_report.get("baseline", {}),
        },

        "robustness": {
            "index_min_bounded_rel": idx,
            "per_variable_bounds": bounds,
            "fragility_ranking": frag_sorted[:50],
        },

        "policy": policy,

        "hashes": {
            "certificate_sha256": "",  # filled below
        }
    }
    cert["hashes"]["certificate_sha256"] = _sha(cert)
    return cert
