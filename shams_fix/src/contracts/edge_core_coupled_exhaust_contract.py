from __future__ import annotations

"""v348.0 — Edge–Core Coupled Exhaust Authority (contract wrapper)

Frozen, deterministic one-pass coupling between:
- core radiation budget (Prad_core)
- required SOL+div radiation for detachment (Prad_sol_div_required)
- effective SOL power to divertor proxies (P_SOL_eff)

This module MUST:
- be algebraic (no iteration)
- be replayable (contract sha256 stamped)
- surface validity flags for caps/clamps

Author: © 2026 Afshin Arjhangmehr
"""

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

_CONTRACT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "edge_core_coupled_exhaust_contract.json"


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load_contract() -> Dict[str, Any]:
    return json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))


CONTRACT: Dict[str, Any] = _load_contract()
CONTRACT_SHA256: str = _sha256_file(_CONTRACT_PATH)


@dataclass(frozen=True)
class EdgeCoreCouplingResult:
    """Deterministic results + validity ledger."""

    P_SOL_eff_MW: float
    delta_Prad_core_MW: float
    f_rad_core_edge_core: float
    validity: Dict[str, str]


def apply_edge_core_coupling(
    *,
    Pin_MW: float,
    Prad_core_MW: float,
    Ploss_MW: float,
    P_SOL_MW: float,
    Prad_sol_div_required_MW: float,
    chi_core: float,
    f_rad_core_edge_core_max: float = float("nan"),
) -> EdgeCoreCouplingResult:
    """Apply one-pass edge–core coupling.

    Model:
      ΔPrad_core = chi_core * Prad_sol_div_required
      P_SOL_eff  = max(P_SOL - ΔPrad_core, eps)
      f_rad_ec   = (Prad_core + ΔPrad_core) / Ploss

    Caps:
      - chi_core clamped to [chi_min, chi_max]
      - ΔPrad_core capped to cap_frac * Pin
      - optional: f_rad_ec capped by reducing ΔPrad_core so that f_rad_ec <= f_rad_core_edge_core_max

    All caps are algebraic; no back-substitution.
    """

    params = CONTRACT.get("params") or {}
    chi_min = float(params.get("chi_core_min", 0.0))
    chi_max = float(params.get("chi_core_max", 1.0))
    eps = float(params.get("eps_P_SOL_MW", 1e-9))
    cap_frac = float(params.get("delta_prad_core_max_frac_of_Pin", 0.30))

    validity: Dict[str, str] = {}

    Pin = max(float(Pin_MW), 0.0)
    Prad_core = max(float(Prad_core_MW), 0.0)
    Ploss = max(float(Ploss_MW), 0.0)
    P_SOL = max(float(P_SOL_MW), 0.0)
    Prad_req = max(float(Prad_sol_div_required_MW), 0.0)

    chi = float(chi_core)
    if not math.isfinite(chi):
        chi = 0.0
        validity["chi_core"] = "invalid->0"
    chi2 = min(max(chi, chi_min), chi_max)
    if chi2 != chi:
        validity["chi_core"] = "clamped"
    chi = chi2

    dprad = chi * Prad_req

    # cap ΔPrad_core relative to Pin
    dcap_pin = cap_frac * Pin
    if Pin > 0.0 and math.isfinite(dcap_pin) and dprad > dcap_pin:
        dprad = dcap_pin
        validity["delta_Prad_core"] = "capped_Pin"

    # optional cap by f_rad limit: reduce ΔPrad_core so that (Prad_core + ΔPrad_core)/Ploss <= fmax
    fmax = float(f_rad_core_edge_core_max)
    if math.isfinite(fmax) and fmax >= 0.0 and Ploss > 0.0:
        dcap_f = max(fmax * Ploss - Prad_core, 0.0)
        if dprad > dcap_f:
            dprad = dcap_f
            validity["delta_Prad_core"] = "capped_f_rad"

    P_SOL_eff = max(P_SOL - dprad, eps)
    if P_SOL_eff != (P_SOL - dprad):
        validity["P_SOL_eff"] = "capped_eps"

    f_rad_ec = float("nan")
    if Ploss > 0.0 and math.isfinite(Ploss):
        f_rad_ec = (Prad_core + dprad) / max(Ploss, eps)

    return EdgeCoreCouplingResult(
        P_SOL_eff_MW=float(P_SOL_eff),
        delta_Prad_core_MW=float(dprad),
        f_rad_core_edge_core=float(f_rad_ec),
        validity=validity,
    )
