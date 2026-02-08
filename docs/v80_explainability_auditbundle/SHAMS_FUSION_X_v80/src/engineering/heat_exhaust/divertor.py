
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

@dataclass
class DivertorProxyResult:
    Psep_MW: float
    q_par_MW_per_m2: float
    q_limit_MW_per_m2: float
    margin: float
    mode: str

def divertor_proxy(out: Dict[str, float], inp: object) -> DivertorProxyResult:
    """PROCESS-inspired but transparent divertor proxy.

    We estimate parallel heat flux proxy from Psep and wetted area.
    Technology modes tighten/relax the limit with an explicit multiplier.
    """
    Pfus = float(out.get("Pfus_MW", 0.0))
    Paux = float(out.get("Paux_MW", getattr(inp, "Paux_MW", 0.0)))
    Prad = float(out.get("Prad_MW", out.get("P_rad_MW", 0.0)))
    # assume fraction to SOL
    f_sep = float(getattr(inp, "f_Psep", 0.7))
    Psep = max(0.0, f_sep*(Pfus + Paux - Prad))

    R0 = float(out.get("R0_m", getattr(inp, "R0_m", 6.2)))
    a = float(out.get("a_m", getattr(inp, "a_m", 2.0)))
    # wetted area proxy ~ 2*pi*R * (2*pi*a*lambda_q) ??? keep simple:
    lambda_q = float(getattr(inp, "lambda_q_m", 0.005))
    A_wet = 2.0*3.14159*R0 * (2.0*3.14159*a*lambda_q)  # m^2 proxy

    q_par = Psep / max(1e-6, A_wet)  # MW/m^2 proxy

    base_limit = float(getattr(inp, "q_parallel_limit_MW_per_m2", 10.0))
    mode = str(getattr(inp, "divertor_tech_mode", "baseline")).lower()
    mult = {"conservative": 0.8, "baseline": 1.0, "aggressive": 1.3}.get(mode, 1.0)
    qlim = base_limit * mult

    return DivertorProxyResult(Psep_MW=Psep, q_par_MW_per_m2=q_par, q_limit_MW_per_m2=qlim, margin=qlim-q_par, mode=mode)
