from __future__ import annotations
"""Failure Mode Taxonomy (v106)

Classifies infeasible SHAMS run artifacts into failure modes by identifying the
dominant failing constraint(s). Produces aggregated statistics and region tags.

Additive only: reads artifacts, outputs a report.
"""

from typing import Any, Dict, List, Optional, Tuple
import time
import math

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

def _dominant_failure(constraints: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    failing = [c for c in constraints if isinstance(c, dict) and c.get("passed") is False]
    if not failing:
        return None
    # prefer explicit severity if present, else smallest margin_frac, else smallest margin
    def key(c: Dict[str, Any]):
        sev = c.get("severity")
        mf = c.get("margin_frac")
        m = c.get("margin")
        sev_key = -float(sev) if _is_num(sev) else 0.0
        mf_key = float(mf) if _is_num(mf) else float("inf")
        m_key = float(m) if _is_num(m) else float("inf")
        return (sev_key, mf_key, m_key)
    failing.sort(key=key)
    return failing[0]

def _map_mode(name: str, group: Optional[str]) -> Dict[str, str]:
    n = (name or "").lower()
    g = (group or "").lower()
    # Default buckets; can be refined over time without changing physics
    if "greenwald" in n or "density" in n or "ng" in n:
        return {"mode": "plasma_density_limit", "pillar": "plasma"}
    if "q95" in n or "safety factor" in n or "q_" in n:
        return {"mode": "plasma_stability_q", "pillar": "plasma"}
    if "beta" in n:
        return {"mode": "plasma_beta_limit", "pillar": "plasma"}
    if "bootstrap" in n or "bs" in n:
        return {"mode": "transport_bootstrap", "pillar": "plasma"}
    if "stress" in n or "strain" in n or "hoop" in n:
        return {"mode": "magnet_stress", "pillar": "engineering"}
    if "rebc" in n or "j_sc" in n or "current density" in n or "coil" in n:
        return {"mode": "superconductor_limit", "pillar": "engineering"}
    if "wall" in n or "heat" in n or "p_" in n or "power density" in n:
        return {"mode": "thermal_wall_loading", "pillar": "engineering"}
    if "recirc" in n or "power balance" in n or "net" in n:
        return {"mode": "systems_power_balance", "pillar": "systems"}
    if g:
        if "plasma" in g:
            return {"mode": "plasma_other", "pillar": "plasma"}
        if "eng" in g or "magnet" in g or "coil" in g:
            return {"mode": "engineering_other", "pillar": "engineering"}
        if "system" in g:
            return {"mode": "systems_other", "pillar": "systems"}
    return {"mode": "other", "pillar": "other"}

def extract_failure_record(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict) or payload.get("kind") != "shams_run_artifact":
        return None
    cons = payload.get("constraints")
    if not isinstance(cons, list):
        return None
    dom = _dominant_failure(cons)
    if dom is None:
        return None
    inputs = payload.get("inputs") if isinstance(payload.get("inputs"), dict) else {}
    name = str(dom.get("name") or "")
    group = dom.get("group")
    mapped = _map_mode(name, group if isinstance(group, str) else None)
    return {
        "run_id": payload.get("id"),
        "constraint_name": name,
        "constraint_group": group,
        "mode": mapped["mode"],
        "pillar": mapped["pillar"],
        "margin_frac": dom.get("margin_frac"),
        "margin": dom.get("margin"),
        "severity": dom.get("severity"),
        "inputs": inputs,
    }

def build_failure_taxonomy_report(
    payloads: List[Dict[str, Any]],
    *,
    lever_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    recs: List[Dict[str, Any]] = []
    for p in payloads or []:
        r = extract_failure_record(p)
        if r is not None:
            recs.append(r)

    # infer lever keys from inputs numeric intersection
    if lever_keys is None:
        keys = None
        for r in recs:
            inp = r.get("inputs")
            if not isinstance(inp, dict):
                continue
            ks=set()
            for k,v in inp.items():
                if _is_num(v):
                    ks.add(k)
            keys = ks if keys is None else (keys & ks)
        lever_keys = sorted(list(keys or []))

    # aggregate counts
    by_mode: Dict[str, int] = {}
    by_pillar: Dict[str, int] = {}
    for r in recs:
        by_mode[r["mode"]] = by_mode.get(r["mode"], 0) + 1
        by_pillar[r["pillar"]] = by_pillar.get(r["pillar"], 0) + 1

    # simple region tags: bin by each lever quartiles for top modes
    region_stats: Dict[str, Any] = {}
    # precompute lever distributions
    lever_vals: Dict[str, List[float]] = {k: [] for k in lever_keys}
    for r in recs:
        inp = r.get("inputs", {})
        for k in lever_keys:
            if isinstance(inp, dict) and k in inp and _is_num(inp[k]):
                lever_vals[k].append(float(inp[k]))
    lever_bins: Dict[str, List[float]] = {}
    for k, vals in lever_vals.items():
        if len(vals) >= 8:
            s = sorted(vals)
            lever_bins[k] = [s[int(0.25*(len(s)-1))], s[int(0.50*(len(s)-1))], s[int(0.75*(len(s)-1))]]

    def bin_label(k: str, x: float) -> Optional[str]:
        b = lever_bins.get(k)
        if not b:
            return None
        if x <= b[0]:
            return "low"
        if x <= b[1]:
            return "mid"
        if x <= b[2]:
            return "high"
        return "vhigh"

    # region signatures for each mode
    mode_regions: Dict[str, Dict[str, Dict[str,int]]] = {}
    for r in recs:
        mode = r["mode"]
        inp = r.get("inputs", {})
        if not isinstance(inp, dict):
            continue
        for k in lever_keys:
            if k in lever_bins and k in inp and _is_num(inp[k]):
                lab = bin_label(k, float(inp[k]))
                if lab is None:
                    continue
                mode_regions.setdefault(mode, {}).setdefault(k, {}).setdefault(lab, 0)
                mode_regions[mode][k][lab] += 1

    report = {
        "kind": "shams_failure_taxonomy_report",
        "created_utc": _created_utc(),
        "n_payloads": len(payloads or []),
        "n_failures": len(recs),
        "lever_keys": lever_keys,
        "counts_by_mode": dict(sorted(by_mode.items(), key=lambda kv: kv[1], reverse=True)),
        "counts_by_pillar": dict(sorted(by_pillar.items(), key=lambda kv: kv[1], reverse=True)),
        "mode_region_bins": lever_bins,
        "mode_region_counts": mode_regions,
        "records": recs[:500],  # cap for portability
    }
    return report
