from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import math

@dataclass(frozen=True)
class TritiumResult:
    T_burn_g_per_day: float
    T_burn_g_per_year: float
    T_inventory_proxy_g: float
    T_processing_proxy_g_per_day: float

def compute_tritium_cycle(out: Dict[str, Any], inp: Any) -> TritiumResult:
    """Very lightweight tritium fuel-cycle proxies.

    Assumptions:
    - DT fusion releases 17.6 MeV per reaction.
    - One T atom consumed per fusion reaction.
    - Converts fusion power to burn rate; inventory proxy based on processing + reserve time.

    This is a transparent feasibility/risk indicator, not a detailed fuel-cycle model.
    """
    try:
        Pfus_MW = float(out.get("Pfus_total_MW", out.get("Pfus_MW", 0.0)))
    except Exception:
        Pfus_MW = 0.0

    # reactions per second = Pfus / (17.6 MeV) ; 1 eV = 1.602e-19 J
    E_J = 17.6e6 * 1.602e-19
    reactions_s = max(Pfus_MW, 0.0) * 1e6 / E_J if E_J > 0 else 0.0

    # grams per second: reactions_s * (atomic mass of T ~ 3 g/mol) / Avogadro
    NA = 6.02214076e23
    g_per_s = reactions_s * (3.0 / NA)

    g_per_day = g_per_s * 86400.0
    g_per_year = g_per_day * 365.0

    reserve_days = float(getattr(inp, "tritium_reserve_days", 7.0))
    processing_eff = float(getattr(inp, "tritium_processing_eff", 0.9))
    processing_g_per_day = g_per_day / max(processing_eff, 1e-6)
    inventory_proxy = processing_g_per_day * reserve_days

    return TritiumResult(
        T_burn_g_per_day=float(g_per_day),
        T_burn_g_per_year=float(g_per_year),
        T_inventory_proxy_g=float(inventory_proxy),
        T_processing_proxy_g_per_day=float(processing_g_per_day),
    )
