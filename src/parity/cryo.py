from __future__ import annotations

"""PROCESS Parity Layer v1: cryogenics block.

SHAMS models coil/structural nuclear + AC heat loads and provides coil heat proxies.
This parity block turns cold power into electric power using an explicit COP model
and reports a PROCESS-like summary.

This is intentionally simple and auditable.
"""

from typing import Any, Dict


def parity_cryo(inputs: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
    # Inputs may supply direct cold load at 20 K; otherwise use coil heat proxy.
    P20 = float(getattr(inputs, "P_cryo_20K_MW", outputs.get("P_cryo_20K_MW", 0.0)) or 0.0)
    # If not provided, use coil heat as a conservative stand-in (many studies do this).
    if P20 <= 0.0:
        P20 = float(outputs.get("coil_heat_MW", 0.0) or 0.0)

    COP = float(getattr(inputs, "cryo_COP", outputs.get("cryo_COP", 0.02)) or 0.02)
    COP = max(COP, 1e-6)
    Pel = P20 / COP

    derived = {
        "P_cold_20K_MW": float(P20),
        "cryo_COP": float(COP),
        "P_cryo_e_MW": float(Pel),
        "coil_heat_MW": float(outputs.get("coil_heat_MW", 0.0) or 0.0),
        "coil_thermal_margin": float(outputs.get("coil_thermal_margin", float("nan")) or float("nan")),
    }
    assumptions = {
        "note": "If P_cryo_20K_MW is not specified, uses coil_heat_MW as cold-load proxy.",
        "P_cryo_e_MW": "P_cold_20K_MW / cryo_COP",
    }
    return {"derived": derived, "assumptions": assumptions}
