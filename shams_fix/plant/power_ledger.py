"""Plant power ledger overlay (non-authoritative).

Deterministic algebraic bookkeeping computed from existing point outputs.

SHAMS law:
- No iteration, no solvers.
- Overlay only; must not change upstream physics.

Emits:
- f_recirc: recirculating fraction (P_recirc / P_e_gross)
- P_pf_avg_MW: PF average electric draw proxy (pf_E_pulse_MJ / t_cycle_s)
- P_e_net_avg_MW: average net electric (P_e_net_MW * duty_factor)

All computations are NaN-safe.
"""

from __future__ import annotations

from typing import Any, Dict
import math


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def compute_power_ledger(out: Dict[str, Any]) -> Dict[str, float]:
    """Compute plant-level bookkeeping metrics to merge into outputs."""
    Pe_gross = _f(out.get("P_e_gross_MW", float("nan")))
    Precirc = _f(out.get("P_recirc_MW", float("nan")))
    f_recirc = float("nan")
    if math.isfinite(Pe_gross) and Pe_gross > 1e-9 and math.isfinite(Precirc) and Precirc >= 0.0:
        f_recirc = Precirc / Pe_gross

    E_pulse_MJ = _f(out.get("pf_E_pulse_MJ", float("nan")))
    t_burn_s = _f(out.get("t_burn_s", out.get("t_flat_s", float("nan"))))
    t_dwell_s = _f(out.get("t_dwell_s", float("nan")))
    t_cycle_s = float("nan")
    if math.isfinite(t_burn_s) and math.isfinite(t_dwell_s) and (t_burn_s + t_dwell_s) > 1e-9:
        t_cycle_s = t_burn_s + t_dwell_s

    P_pf_avg_MW = float("nan")
    if math.isfinite(E_pulse_MJ) and E_pulse_MJ >= 0.0 and math.isfinite(t_cycle_s) and t_cycle_s > 0.0:
        P_pf_avg_MW = E_pulse_MJ / t_cycle_s  # MJ/s == MW

    duty = _f(out.get("duty_factor", float("nan")))
    Pe_net = _f(out.get("P_e_net_MW", float("nan")))
    P_e_net_avg_MW = float("nan")
    if math.isfinite(Pe_net) and math.isfinite(duty):
        P_e_net_avg_MW = Pe_net * max(min(duty, 1.0), 0.0)

    return {
        "f_recirc": float(f_recirc),
        "P_pf_avg_MW": float(P_pf_avg_MW),
        "P_e_net_avg_MW": float(P_e_net_avg_MW),
        "pf_t_cycle_s": float(t_cycle_s),
    }
