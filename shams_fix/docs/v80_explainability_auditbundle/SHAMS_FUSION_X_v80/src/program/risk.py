from __future__ import annotations

from typing import Any, Dict, Optional
import math

def schedule_proxy(inputs: Dict[str, Any], outputs: Dict[str, Any]) -> Dict[str, Any]:
    """Transparent schedule proxy.

    Returns a small set of program planning scalars. These are *not* intended
    to be high-fidelity schedule models; they are decision-grade proxies with
    explicit assumptions.

    Heuristic assumptions (editable):
    - Base build time grows with major radius and magnet complexity.
    - Outage time per year grows with blanket/divertor heat flux and maintenance complexity.
    """
    R = float(outputs.get("R0_m", outputs.get("R_m", inputs.get("R0_m", 3.0))))
    B = float(outputs.get("B0_T", outputs.get("B_T", inputs.get("B0_T", 8.0))))
    Pth = float(outputs.get("P_th_MW", outputs.get("P_fusion_MW", 500.0)))
    qdiv = float(outputs.get("q_div_MWm2", outputs.get("q_divertor_MWm2", 10.0)))

    # Build time: baseline 6 years at R=3m, B=8T; grows mildly with size/field.
    build_years = 6.0 * (R/3.0)**0.35 * (B/8.0)**0.15

    # Commissioning: 1.5 years baseline, grows with thermal power
    commission_years = 1.5 * (Pth/500.0)**0.20

    # Planned outage days per year: baseline 60 days, increases with divertor load proxy
    outage_days_per_year = 60.0 * (1.0 + max(0.0, (qdiv-10.0))/20.0)

    # Simple delivery risk proxy (0-1): higher for longer build and higher outage.
    risk = 1.0 - math.exp(-(build_years + 0.2*commission_years)/8.0)  # saturating
    risk = float(max(0.0, min(1.0, risk + 0.003*(outage_days_per_year-60.0))))

    return {
        "build_years": float(build_years),
        "commission_years": float(commission_years),
        "outage_days_per_year": float(outage_days_per_year),
        "delivery_risk_proxy": float(risk),
        "assumptions": {
            "build_years_baseline_at_R3m_B8T": 6.0,
            "commission_baseline_years": 1.5,
            "outage_baseline_days_per_year": 60.0,
        }
    }

def robustness_from_uq(outputs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract robustness summary if UQ block exists."""
    uq = outputs.get("uq", None)
    if not isinstance(uq, dict):
        return None
    p = uq.get("p_feasible", uq.get("prob_feasible", None))
    if p is None:
        return None
    try:
        p = float(p)
    except Exception:
        return None
    return {"p_feasible": float(p)}
