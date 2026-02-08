
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

import math

@dataclass
class DivertorProxyResult:
    Psep_MW: float
    q_par_MW_per_m2: float  # interpreted as peak target heat-flux proxy in MW/m^2
    q_limit_MW_per_m2: float
    margin: float
    mode: str

    # v287+ transparency fields (non-breaking; may be omitted by callers)
    lambda_q_used_m: float | None = None
    A_wet_m2: float | None = None
    validity: str | None = None

def divertor_proxy(out: Dict[str, float], inp: object) -> DivertorProxyResult:
    """Divertor / SOL heat exhaust proxy (deterministic).

    Models
    ------
    - wetted_area_proxy (legacy):
        q_par ≈ Psep / A_wet, with A_wet ~ (2πR0) * (2πaλq)
    - two_point (recommended bundle):
        q_par ≈ Psep / (2πR0 * λq * f_expansion)

      This is a lightweight two-point-style mapping that makes the *dependence*
      on λq and flux expansion explicit. It is still a proxy (no detachment physics),
      but it is more interpretable and closer to common SOL scaling usage.

    Notes
    -----
    - Psep is estimated from Pfus + Paux - Prad using f_Psep.
    - Technology modes tighten/relax the limit via an explicit multiplier.
    """
    Pfus = float(out.get("Pfus_MW", 0.0))
    Paux = float(out.get("Paux_MW", getattr(inp, "Paux_MW", 0.0)))
    Prad = float(out.get("Prad_MW", out.get("P_rad_MW", 0.0)))
    f_sep = float(getattr(inp, "f_Psep", 0.7))
    Psep = max(0.0, f_sep * (Pfus + Paux - Prad))

    R0 = float(out.get("R0_m", getattr(inp, "R0_m", 6.2)))
    a = float(out.get("a_m", getattr(inp, "a_m", 2.0)))

    # λq source hierarchy (deterministic):
    #  1) upstream Eich proxy (if enabled in hot_ion and finite)
    #  2) user-provided lambda_q_m
    # NOTE: hot_ion reports lambda_q_mm; we convert to meters here.
    lam_m_user = float(getattr(inp, "lambda_q_m", 0.005))
    lam_mm = float(out.get("lambda_q_mm", float("nan")))
    use_eich = bool(getattr(inp, "use_lambda_q", False)) and math.isfinite(lam_mm)
    lambda_q = max((lam_mm * 1e-3) if use_eich else lam_m_user, 1e-6)

    model = str(getattr(inp, "divertor_model", "wetted_area_proxy")).strip().lower()

    # v287 authority knobs (already exist in inputs in most builds; defaults preserve behavior)
    f_exp = float(getattr(inp, "flux_expansion", getattr(inp, "f_expansion", 10.0)))
    n_strikes = int(getattr(inp, "n_strike_points", 2) or 2)
    n_strikes = max(1, n_strikes)
    f_peaking = float(getattr(inp, "divertor_peaking_factor", 1.0) or 1.0)
    f_peaking = min(max(f_peaking, 0.7), 3.0)
    f_geom = float(getattr(inp, "divertor_geom_factor", 1.0) or 1.0)
    f_geom = min(max(f_geom, 0.2), 5.0)

    validity = "ok"
    A_wet = float("nan")
    if model in ("two_point", "twopoint", "two-point"):
        # Target wetted area proxy:
        #   A_wet ~ (2πR0) * (2π λq) * f_exp * N_strikes * f_geom
        # Interprets λq as midplane fall-off mapping to strike footprint.
        A_wet = (2.0 * math.pi * max(R0, 1e-6)) * (2.0 * math.pi * max(lambda_q, 1e-6))
        A_wet *= max(f_exp, 1e-6) * max(float(n_strikes), 1.0) * max(f_geom, 1e-6)
        q_par = f_peaking * Psep / max(1e-6, A_wet)
    else:
        # legacy wetted-area proxy (kept for back-compat)
        A_wet = (2.0 * math.pi * max(R0, 1e-6)) * (2.0 * math.pi * max(a, 1e-6) * max(lambda_q, 1e-6))
        q_par = f_peaking * Psep / max(1e-6, A_wet)
        validity = "legacy_model"

    # Prefer the explicit divertor target limit if present (v287+);
    # fall back to legacy q_parallel_limit_MW_per_m2.
    base_limit = float(getattr(inp, "q_div_max_MW_m2", getattr(inp, "q_parallel_limit_MW_per_m2", 10.0)))
    mode = str(getattr(inp, "divertor_tech_mode", "baseline")).lower()
    mult = {"conservative": 0.8, "baseline": 1.0, "aggressive": 1.3}.get(mode, 1.0)
    qlim = base_limit * mult

    return DivertorProxyResult(
        Psep_MW=Psep,
        q_par_MW_per_m2=q_par,
        q_limit_MW_per_m2=qlim,
        margin=qlim - q_par,
        mode=f"{mode}|{model}|{'eich' if use_eich else 'user'}",
        lambda_q_used_m=float(lambda_q),
        A_wet_m2=float(A_wet) if math.isfinite(A_wet) else None,
        validity=str(validity),
    )
