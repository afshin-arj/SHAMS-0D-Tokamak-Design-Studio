from __future__ import annotations
"""Plant power / net-electric closure.

PROCESS is a systems code; to move SHAMS in that direction, we add a simple plant closure:
- thermal power from fusion + blanket energy multiplication
- gross electric via efficiency
- recirculating power (cryo + balance-of-plant + pumps + aux)
- net electric and Qe

The intent is transparent bookkeeping, not a detailed power plant simulator.
"""
from dataclasses import dataclass


def electric_efficiency(coolant: str, T_outlet_K: float) -> float:
    """Very simple thermal-cycle efficiency proxy.

    This is an intentionally transparent mapping, not a detailed Brayton/Rankine cycle model.
    The goal is to avoid a *fixed* eta_elec when comparing coolant choices.

    - Water (Rankine-like): baseline ~0.33 around 550 K outlet
    - Helium / FLiBe (Brayton-like): can reach higher efficiencies with higher outlet temperature

    We cap to [0.25, 0.55] to avoid unrealistic values in early scoping.

    Parameters
    ----------
    coolant: "Helium" | "Water" | "FLiBe" | other
    T_outlet_K: representative outlet temperature in kelvin
    """
    c = (coolant or "").strip().lower()
    T = float(T_outlet_K)
    if c == "water":
        eta = 0.33 + 1.2e-4 * (T - 550.0)
    elif c in ("helium", "flibe"):
        eta = 0.40 + 1.6e-4 * (T - 900.0)
    else:
        eta = 0.35 + 1.3e-4 * (T - 700.0)
    return max(0.25, min(0.55, eta))


@dataclass(frozen=True)
class PlantPower:
    Pfus_MW: float
    Pth_MW: float
    Pe_gross_MW: float
    Precirc_MW: float
    Pe_net_MW: float
    Qe: float

def plant_power_closure(Pfus_MW: float,
                        Paux_MW: float,
                        Pcd_launch_MW: float,
                        eta_elec: float,
                        blanket_energy_mult: float,
                        eta_aux_wallplug: float,
                        eta_cd_wallplug: float,
                        P_balance_of_plant_MW: float,
                        P_pumps_MW: float,
                        P_cryo_20K_MW: float,
                        cryo_COP: float,
                        P_tf_ohmic_MW: float = 0.0,
                        eta_tf_wallplug: float = 0.95) -> PlantPower:
    """Simple net-electric closure.

    - Thermal power: Pth = blanket_mult * Pfus
    - Gross electric: eta_elec * Pth
    - Recirc: aux wallplug + CD wallplug + BOP + pumps + cryo electric
    - Cryo electric: Pcryo_el = P_cryo_20K / COP
    """
    Pth_MW = max(blanket_energy_mult, 0.0) * max(Pfus_MW, 0.0)
    Pe_gross = max(eta_elec, 0.0) * Pth_MW
    Paux_el = max(Paux_MW, 0.0) / max(eta_aux_wallplug, 1e-9)
    Pcd_el = max(Pcd_launch_MW, 0.0) / max(eta_cd_wallplug, 1e-9)
    Pcryo_el = max(P_cryo_20K_MW, 0.0) / max(cryo_COP, 1e-9)
    Ptf_el = max(P_tf_ohmic_MW, 0.0) / max(eta_tf_wallplug, 1e-9)
    Precirc = Paux_el + Pcd_el + Ptf_el + max(P_balance_of_plant_MW, 0.0) + max(P_pumps_MW, 0.0) + Pcryo_el
    Pe_net = Pe_gross - Precirc
    Qe = Pe_gross / max(Precirc, 1e-9)
    return PlantPower(Pfus_MW=Pfus_MW, Pth_MW=Pth_MW, Pe_gross_MW=Pe_gross, Precirc_MW=Precirc, Pe_net_MW=Pe_net, Qe=Qe)
