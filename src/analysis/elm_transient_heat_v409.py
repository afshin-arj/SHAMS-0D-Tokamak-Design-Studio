"""ELM / transient heat-load authority overlay (PHYS-004 / v409)."""
from __future__ import annotations

import math
from typing import Any, Dict


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else float("nan")
    except (TypeError, ValueError):
        return default


def evaluate_elm_transient_heat_v409(out: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    """Screening proxy for ELM/transient parallel heat-load peaking on exhaust."""
    patch: Dict[str, Any] = {
        "include_elm_transient_heat_v409": float(bool(getattr(inp, "include_elm_transient_heat_v409", False))),
        "elm_transient_q_parallel_max_MW_m2_v409": _f(getattr(inp, "elm_transient_q_parallel_max_MW_m2_v409", float("nan"))),
        "elm_heat_fraction_max_v409": _f(getattr(inp, "elm_heat_fraction_max_v409", float("nan"))),
    }
    if not bool(getattr(inp, "include_elm_transient_heat_v409", False)):
        patch["elm_transient_q_parallel_MW_m2_v409"] = float("nan")
        patch["elm_heat_fraction_v409"] = float("nan")
        return patch

    q_par = _f(out.get("q_parallel_MW_per_m2", out.get("q_parallel_MW_m2", float("nan"))))
    w_mj = _f(out.get("W_th_MJ", out.get("W_MJ", float("nan"))))
    tau_s = _f(out.get("tauE_s", out.get("tauE_eff_s", float("nan"))))
    # Transient peaking proxy: stored-energy dump fraction over ELM timescale vs steady parallel flux.
    elm_frac = _f(getattr(inp, "elm_energy_fraction_v409", 0.05))
    elm_frac = min(max(elm_frac, 0.0), 0.5)
    tau_elm_ms = _f(getattr(inp, "elm_duration_ms_v409", 0.5))
    tau_elm_s = max(tau_elm_ms, 0.05) * 1e-3
    p_sol = _f(out.get("P_SOL_MW", float("nan")))

    q_trans = float("nan")
    if w_mj == w_mj and tau_elm_s > 0.0:
        q_trans = (elm_frac * w_mj * 1000.0) / tau_elm_s  # MW/m^2 scale proxy (normalized)
        if p_sol == p_sol and p_sol > 0.0:
            q_trans = q_trans * (p_sol / max(p_sol, 1.0))
    if q_trans != q_trans and q_par == q_par:
        q_trans = q_par * (1.0 + 5.0 * elm_frac)

    patch["elm_transient_q_parallel_MW_m2_v409"] = float(q_trans)
    patch["elm_heat_fraction_v409"] = float(elm_frac)
    if q_par == q_par and q_par > 0.0 and q_trans == q_trans:
        patch["elm_transient_heat_multiplier_v409"] = float(q_trans / q_par)
    else:
        patch["elm_transient_heat_multiplier_v409"] = float("nan")

    # PHYS-009: ELM duty-cycle → availability ledger coupling proxy
    duty = _f(getattr(inp, "elm_duty_cycle_v409", 0.02))
    duty = min(max(duty, 0.0), 1.0)
    recovery = _f(getattr(inp, "elm_recovery_downtime_frac_v409", 0.5))
    recovery = min(max(recovery, 0.0), 1.0)
    patch["elm_duty_cycle_v409"] = float(duty)
    patch["elm_recovery_downtime_frac_v409"] = float(recovery)
    patch["elm_availability_downtime_frac_v409"] = float(duty * recovery)
    return patch
