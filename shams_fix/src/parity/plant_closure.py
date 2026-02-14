from __future__ import annotations

"""PROCESS Parity Layer v1: plant (net-electric) closure.

SHAMS already computes several plant-like quantities in the frozen evaluator.
This parity block re-computes a transparent net-electric closure using
`src.physics.plant.plant_power_closure`, returning:

* a derived breakdown (gross / recirc / net)
* explicit assumptions used by the closure
* a small comparison against evaluator-provided keys when available

The goal is **auditable bookkeeping**, not a detailed power-plant simulator.
"""

from typing import Any, Dict

from physics.plant import plant_power_closure, electric_efficiency


def parity_plant_closure(inputs: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
    # Pull required values with safe fallbacks
    Pfus = float(outputs.get("Pfus_total_MW", outputs.get("Pfus_MW", 0.0)) or 0.0)
    Paux = float(getattr(inputs, "Paux_MW", outputs.get("Paux_MW", 0.0)) or 0.0)
    Pcd_launch = float(outputs.get("P_cd_launch_MW", outputs.get("P_cd_launch_MW", 0.0)) or 0.0)

    coolant = str(getattr(inputs, "coolant", outputs.get("coolant", "")) or "")
    T_out = float(getattr(inputs, "T_outlet_K", outputs.get("T_outlet_K", 900.0)) or 900.0)
    eta_elec = float(getattr(inputs, "eta_elec", 0.0) or 0.0)
    if eta_elec <= 0.0:
        eta_elec = electric_efficiency(coolant=coolant, T_outlet_K=T_out)

    blanket_mult = float(getattr(inputs, "blanket_energy_mult", outputs.get("blanket_energy_mult", 1.2)) or 1.2)
    eta_aux = float(getattr(inputs, "eta_aux_wallplug", outputs.get("eta_aux_wallplug", 0.4)) or 0.4)
    eta_cd = float(getattr(inputs, "eta_cd_wallplug", outputs.get("eta_cd_wallplug", 0.25)) or 0.25)
    P_bop = float(getattr(inputs, "P_balance_of_plant_MW", outputs.get("P_balance_of_plant_MW", 0.0)) or 0.0)
    P_pumps = float(outputs.get("P_pump_MW", outputs.get("P_pumps_MW", 0.0)) or 0.0)
    P_cryo_20K = float(getattr(inputs, "P_cryo_20K_MW", outputs.get("P_cryo_20K_MW", 0.0)) or 0.0)
    cryo_COP = float(getattr(inputs, "cryo_COP", outputs.get("cryo_COP", 0.02)) or 0.02)

    pp = plant_power_closure(
        Pfus_MW=Pfus,
        Paux_MW=Paux,
        Pcd_launch_MW=Pcd_launch,
        eta_elec=eta_elec,
        blanket_energy_mult=blanket_mult,
        eta_aux_wallplug=eta_aux,
        eta_cd_wallplug=eta_cd,
        P_balance_of_plant_MW=P_bop,
        P_pumps_MW=P_pumps,
        P_cryo_20K_MW=P_cryo_20K,
        cryo_COP=cryo_COP,
    )

    # Compare to evaluator-provided values when they exist
    def _cmp(key: str, v: float) -> Dict[str, Any]:
        ref = outputs.get(key)
        try:
            ref_f = float(ref)
        except Exception:
            ref_f = None
        if ref_f is None:
            return {"ref": None, "delta": None, "rel": None}
        delta = v - ref_f
        rel = delta / max(abs(ref_f), 1e-9)
        return {"ref": ref_f, "delta": delta, "rel": rel}

    derived = {
        "Pfus_MW": float(pp.Pfus_MW),
        "Pth_MW": float(pp.Pth_MW),
        "P_e_gross_MW": float(pp.Pe_gross_MW),
        "P_recirc_MW": float(pp.Precirc_MW),
        "P_e_net_MW": float(pp.Pe_net_MW),
        "Qe": float(pp.Qe),
    }
    compare = {
        "Pth_total_MW": _cmp("Pth_total_MW", derived["Pth_MW"]),
        "P_e_gross_MW": _cmp("P_e_gross_MW", derived["P_e_gross_MW"]),
        "P_recirc_MW": _cmp("P_recirc_MW", derived["P_recirc_MW"]),
        "P_e_net_MW": _cmp("P_e_net_MW", derived["P_e_net_MW"]),
    }

    assumptions = {
        "coolant": coolant or "(unspecified)",
        "T_outlet_K": float(T_out),
        "eta_elec": float(eta_elec),
        "blanket_energy_mult": float(blanket_mult),
        "eta_aux_wallplug": float(eta_aux),
        "eta_cd_wallplug": float(eta_cd),
        "P_balance_of_plant_MW": float(P_bop),
        "P_pumps_MW": float(P_pumps),
        "P_cryo_20K_MW": float(P_cryo_20K),
        "cryo_COP": float(cryo_COP),
    }

    return {
        "derived": derived,
        "assumptions": assumptions,
        "compare": compare,
    }
