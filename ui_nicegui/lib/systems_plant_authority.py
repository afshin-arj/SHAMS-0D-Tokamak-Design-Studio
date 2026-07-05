"""Post-solve plant & exhaust authority bundles — derived from solver outputs only."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_exhaust_authority_bundle(out: dict) -> dict:
    """Divertor / exhaust screening bundle (algebraic, no re-solve)."""
    o = out or {}
    return {
        "lambda_q_mm_raw": float(o.get("lambda_q_mm_raw", float("nan"))),
        "lambda_q_mm_used": float(o.get("lambda_q_mm", float("nan"))),
        "flux_expansion_raw": float(o.get("flux_expansion_raw", float("nan"))),
        "flux_expansion_used": float(o.get("flux_expansion", float("nan"))),
        "n_strike_points_raw": int(o.get("n_strike_points_raw", o.get("n_strike_points", 2)) or 2),
        "n_strike_points_used": int(o.get("n_strike_points", 2) or 2),
        "f_wet_raw": float(o.get("f_wet_raw", float("nan"))),
        "f_wet_used": float(o.get("f_wet_divertor", float("nan"))),
        "A_wet_m2": float(o.get("A_wet_m2", float("nan"))),
        "q_div_MW_m2": float(o.get("q_div_MW_m2", float("nan"))),
        "q_div_max_MW_m2": float(o.get("q_div_max_MW_m2", float("nan"))),
        "q_div_unit_suspect": float(o.get("q_div_unit_suspect", 0.0)),
        "contract_sha256": str(o.get("exhaust_authority_contract_sha256", "")),
    }


def exhaust_table_row(bundle: dict) -> dict:
    b = bundle or {}
    return {
        "λ_q used [mm]": b.get("lambda_q_mm_used"),
        "Flux expansion": b.get("flux_expansion_used"),
        "Strike points": b.get("n_strike_points_used"),
        "f_wet": b.get("f_wet_used"),
        "A_wet [m²]": b.get("A_wet_m2"),
        "q_div [MW/m²]": b.get("q_div_MW_m2"),
        "q_div max [MW/m²]": b.get("q_div_max_MW_m2"),
    }


def exhaust_unit_suspect(bundle: dict) -> bool:
    try:
        return float((bundle or {}).get("q_div_unit_suspect", 0.0)) >= 0.5
    except (TypeError, ValueError):
        return False


def warm_post_solve_cert_cache(session: Any, outs: dict, ins: dict, *, keys: Optional[List[str]] = None) -> None:
    """Compute missing certification entries into session cache (deterministic)."""
    from ui_nicegui.lib.systems_cert_registry import CERT_REGISTRY, run_certify

    cache = dict(getattr(session, "systems_cert_cache", None) or {})
    want = set(keys) if keys else {spec[1] for spec in CERT_REGISTRY}
    for spec in CERT_REGISTRY:
        key = spec[1]
        if key not in want or key in cache:
            continue
        try:
            cache[key] = run_certify(spec, outs, ins)
        except Exception:
            pass
    session.systems_cert_cache = cache
    bundle = build_exhaust_authority_bundle(outs)
    session.systems_exhaust_authority = bundle
