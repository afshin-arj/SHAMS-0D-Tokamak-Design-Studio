from __future__ import annotations

"""Unified SOL/divertor exhaust evaluation.

Single deterministic API for exhaust quantities used by the frozen evaluator,
constraint ledger, and UI.

Includes:
- optional Eich-like SOL width proxy (lambda_q)
- divertor target heat-flux proxy using wetted area (lambda_q * flux expansion)
- two-regime attached/detached-like proxy based on P_SOL/R overload

These are lightweight proxies intended for systems studies. They are not
high-fidelity divertor simulations and should be treated as screening/closure
models with explicit validity domains.
"""

import math
from dataclasses import dataclass, asdict
from typing import Any, Dict

from phase1_systems import (
    divertor_q_MW_m2,
    connection_length_m,
    divertor_wetted_area_m2,
)
from physics.divertor import divertor_two_regime, DivertorResult

from engineering.heat_exhaust.exhaust_authority_v375 import (
    apply_exhaust_authority,
    ExhaustAuthorityBundle,
    CONTRACT_SHA256 as EXHAUST_AUTHORITY_CONTRACT_SHA256,
)


@dataclass(frozen=True)
class ExhaustResult:
    P_SOL_MW: float
    R0_m: float
    q95: float

    use_lambda_q: bool
    Bpol_out_mid_T: float
    lambda_q_mm: float

    flux_expansion: float
    n_strike_points: int
    f_wet: float
    f_rad_div: float

    A_wet_m2: float
    q_div_proxy_MW_m2: float

    div_regime: str
    f_rad_div_eff: float
    P_div_MW: float
    q_div_MW_m2: float
    q_midplane_MW_m2: float

    Lpar_m: float

    # v375 authority transparency (non-breaking; used by UI/governance)
    lambda_q_mm_raw: float
    flux_expansion_raw: float
    n_strike_points_raw: int
    f_wet_raw: float
    q_div_unit_suspect: float
    exhaust_authority_contract_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["schema_version"] = "exhaust_result.v1"
        return d


def evaluate_exhaust_with_known_lambda_q(
    *,
    P_SOL_MW: float,
    R0_m: float,
    q95: float,
    A_fw_m2: float,
    Bpol_out_mid_T: float,
    lambda_q_mm: float,
    flux_expansion: float,
    n_strike_points: int,
    f_rad_div: float,
    P_SOL_over_R_max_MW_m: float,
    f_Lpar: float = 1.0,
    advanced_divertor_factor: float = 1.0,
    f_wet: float = 1.0,
) -> ExhaustResult:
    """Evaluate exhaust proxies when Bpol and lambda_q are already computed upstream."""
    P_SOL = max(float(P_SOL_MW), 0.0)
    R0 = max(float(R0_m), 1e-9)
    q95_f = float(q95)

    lam_mm_raw = float(lambda_q_mm)
    Bpol_out = float(Bpol_out_mid_T)

    f_div = min(max(float(f_rad_div), 0.0), 0.99)
    nsp_raw = int(n_strike_points)
    flux_exp_raw = float(flux_expansion)
    f_wet_raw = float(f_wet)

    # Apply explicit v375 authority bounds BEFORE computing wetted area / q_div.
    tmp: ExhaustAuthorityBundle = apply_exhaust_authority(
        lambda_q_mm_raw=lam_mm_raw,
        flux_expansion_raw=flux_exp_raw,
        n_strike_points_raw=nsp_raw,
        f_wet_raw=f_wet_raw,
        q_div_MW_m2=float("nan"),
        A_wet_m2=float("nan"),
    )

    lam_mm = float(tmp.lambda_q_mm_used)
    nsp = int(tmp.n_strike_points_used)
    flux_exp = float(tmp.flux_expansion_used)
    f_wet_used = float(tmp.f_wet_used)

    qdiv_proxy = divertor_q_MW_m2(
        P_SOL_MW=P_SOL,
        R0_m=R0,
        lambda_q_mm=lam_mm,
        flux_expansion=float(flux_exp),
        f_rad_div=float(f_div),
        n_strikes=nsp,
    )
    lam_m = max(lam_mm * 1e-3, 1e-9)
    A_wet = divertor_wetted_area_m2(R0, lam_m, flux_expansion=float(flux_exp), n_strikes=nsp) * max(f_wet_used, 1e-9)

    div: DivertorResult = divertor_two_regime(
        P_SOL_MW=float(P_SOL),
        R0_m=R0,
        A_fw_m2=float(A_fw_m2),
        q_div_proxy_MW_m2=float(qdiv_proxy),
        P_SOL_over_R_max_MW_m=float(P_SOL_over_R_max_MW_m),
        f_rad_div=float(f_div),
        advanced_divertor_factor=float(advanced_divertor_factor),
    )

    # Final authority bundle with computed q_div and wetted area. We do not enforce q_div_max here;
    # constraints handle feasibility. We only add a unit/scale sanity flag.
    bundle: ExhaustAuthorityBundle = apply_exhaust_authority(
        lambda_q_mm_raw=lam_mm_raw,
        flux_expansion_raw=flux_exp_raw,
        n_strike_points_raw=nsp_raw,
        f_wet_raw=f_wet_raw,
        q_div_MW_m2=float(div.q_div_MW_m2),
        A_wet_m2=float(A_wet),
    )

    Lpar = connection_length_m(q95_f, R0, f_Lpar=float(f_Lpar))

    return ExhaustResult(
        P_SOL_MW=P_SOL,
        R0_m=R0,
        q95=q95_f,
        use_lambda_q=True,
        Bpol_out_mid_T=Bpol_out,
        lambda_q_mm=lam_mm,
        flux_expansion=float(flux_exp),
        n_strike_points=nsp,
        f_wet=float(f_wet_used),
        f_rad_div=f_div,
        A_wet_m2=float(A_wet),
        q_div_proxy_MW_m2=float(qdiv_proxy),
        div_regime=str(div.regime),
        f_rad_div_eff=float(div.f_rad_div_eff),
        P_div_MW=float(div.P_div_MW),
        q_div_MW_m2=float(div.q_div_MW_m2),
        q_midplane_MW_m2=float(div.q_mid_MW_m2),
        Lpar_m=float(Lpar),

        lambda_q_mm_raw=float(lam_mm_raw),
        flux_expansion_raw=float(flux_exp_raw),
        n_strike_points_raw=int(nsp_raw),
        f_wet_raw=float(f_wet_raw),
        q_div_unit_suspect=float(bundle.q_div_unit_suspect),
        exhaust_authority_contract_sha256=str(EXHAUST_AUTHORITY_CONTRACT_SHA256),
    )


def q_midplane_from_lambda_q(
    *, P_SOL_MW: float, R0_m: float, lambda_q_mm: float
) -> float:
    """Midplane/SOL proxy heat flux density.

    q_mp ~ P_SOL / (2πR0 * λq)

    Returns MW/m^2.
    """
    P_SOL = max(float(P_SOL_MW), 0.0)
    R0 = max(float(R0_m), 1e-9)
    lam_m = max(float(lambda_q_mm) * 1e-3, 1e-9)
    return P_SOL / (2.0 * math.pi * R0 * lam_m)
