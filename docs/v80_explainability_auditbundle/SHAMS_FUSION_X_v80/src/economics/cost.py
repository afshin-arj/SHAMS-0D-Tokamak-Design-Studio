from __future__ import annotations

"""Lightweight economics / cost proxies.

PROCESS-like systems studies often include an economic objective (e.g., COE).
SHAMS remains lightweight: these are transparent *proxies*, not a plant costing model.

All costs are dimensionless or approximate and intended for *relative* comparisons
in design-space exploration.
"""

from dataclasses import asdict
from typing import Dict, Any
import math
import json
from functools import lru_cache
from economics.lifecycle import discounted_cashflow_proxy, LifecycleAssumptions, ReplacementItem
from pathlib import Path

@lru_cache(maxsize=8)
def _load_cost_coeffs(name: str, path: str) -> Dict[str, float]:
    """Load cost calibration coefficients.

    Coefficients are used only for *relative* comparisons. Defaults are provided in
    `docs/cost_calibration_default.json`, and users may override by providing a JSON path.
    """
    # built-in default
    here = Path(__file__).resolve()
    default_path = here.parents[2] / "docs" / "cost_calibration_default.json"
    coeffs: Dict[str, float] = {}
    try:
        coeffs = json.loads(default_path.read_text(encoding="utf-8"))
    except Exception:
        coeffs = {}
    # optional override
    p = (path or "").strip()
    if p:
        try:
            coeffs.update(json.loads(Path(p).read_text(encoding="utf-8")))
        except Exception:
            pass
    # allow named presets later; currently only "default"
    return coeffs



def cost_proxies(inputs: Any, outputs: Dict[str, float]) -> Dict[str, float]:
    coeffs = _load_cost_coeffs(str(getattr(inputs, "cost_coeffs_name", "default")), str(getattr(inputs, "cost_coeffs_path", "")))
    kmag = float(coeffs.get("magnet_MUSD_per_Tm3", kmag))
    kblank = float(coeffs.get("blanket_MUSD_per_m3", 1.5))
    kbop = float(coeffs.get("bop_MUSD_per_MWe", 1.2))
    kcryo = float(coeffs.get("cryo_MUSD_per_MW_recirc", 0.8))
    fcr = float(coeffs.get("fixed_charge_rate", 0.10))
    opex_frac = float(coeffs.get("opex_fraction_of_capex", 0.04))
    avail = float(coeffs.get("availability", 0.70))
    capfac = float(coeffs.get("capacity_factor", 0.75))
    """Compute simple CAPEX/OPEX/COE proxies.

    Returns keys:
      - CAPEX_proxy_MUSD
      - OPEX_proxy_MUSD_per_y
      - COE_proxy_USD_per_MWh
      - cost_magnet_MUSD, cost_blanket_MUSD, cost_bop_MUSD, cost_cryo_MUSD (breakdown)
    """
    # Geometry / scale
    R0 = float(getattr(inputs, "R0_m", float("nan")))
    a  = float(getattr(inputs, "a_m", float("nan")))
    k  = float(getattr(inputs, "kappa", 1.0))
    Bt = float(getattr(inputs, "Bt_T", float("nan")))
    Bpk = float(outputs.get("B_peak_T", Bt))
    Pnet = float(outputs.get("P_e_net_MW", float("nan")))
    Pfus = float(outputs.get("Pfus_total_MW", outputs.get("Pfus_MW", float("nan"))))
    Precirc = float(outputs.get("P_recirc_MW", float("nan")))
    Ppump = float(outputs.get("P_pump_MW", 0.0))
    Precirc_total = Precirc + (Ppump if math.isfinite(Ppump) else 0.0)
    Pcryo = float(getattr(inputs, "P_cryo_20K_MW", 0.0))
    # Basic scale volumes / areas
    # - Vacuum vessel surface proxy ~ 4π^2 R a k  (torus area scaling)
    area = 4.0 * math.pi**2 * max(R0, 0.1) * max(a, 0.05) * max(k, 1.0)
    # - Plasma volume proxy ~ 2π^2 R a^2 k
    vol = 2.0 * math.pi**2 * max(R0, 0.1) * max(a, 0.05)**2 * max(k, 1.0)

    # Magnet cost proxy: scales strongly with peak field & coil volume.
    # Use B^2 * volume scaling.
    k_mag = float(getattr(inputs, "k_cost_magnet", 0.12))  # MUSD per (T^2*m^3) proxy
    # Coil volume proxy ~ torus area * t_coil; approximate t_coil ~ 0.5 m
    t_coil = float(getattr(inputs, "t_coil_proxy_m", 0.5))
    V_coil = area * max(t_coil, 0.1)
    cost_magnet = k_mag * (max(Bpk, 0.0)**2) * V_coil

    # Blanket/shield/structure cost proxy: scales with vessel area and thickness
    k_blank = float(getattr(inputs, "k_cost_blanket", 0.08))  # MUSD per (m^2*m)
    t_shield = float(getattr(inputs, "t_shield_m", 0.7))
    cost_blanket = k_blank * area * max(t_shield, 0.1)

    # Balance-of-plant cost proxy: scales with thermal power
    k_bop = float(getattr(inputs, "k_cost_bop", 0.35))  # MUSD per MW(th) proxy
    Pth = float(outputs.get("Pth_total_MW", float("nan")))
    cost_bop = k_bop * max(Pth if Pth==Pth else 0.0, 0.0)

    # Cryo plant CAPEX proxy: scales with cryo power
    k_cryo = float(getattr(inputs, "k_cost_cryo", 6.0))  # MUSD per MW@20K proxy
    cost_cryo = k_cryo * max(Pcryo, 0.0)

    CAPEX = cost_magnet + cost_blanket + cost_bop + cost_cryo

    # OPEX proxy: proportional to recirculating power and component replacement
    # Use electricity price and a simple availability.
    elec_price = float(getattr(inputs, "electricity_price_USD_per_MWh", 60.0))
    # Prefer model-derived availability if present in outputs; otherwise fall back to input.
    avail_out = outputs.get("availability_model", outputs.get("availability", float("nan")))
    try:
        avail_out = float(avail_out)
    except Exception:
        avail_out = float("nan")
    avail = float(getattr(inputs, "availability", 0.7)) if not (avail_out == avail_out) else max(min(avail_out, 1.0), 0.0)
    hours = 8760.0 * max(min(avail, 1.0), 0.0)
    duty = float(outputs.get("duty_factor", 1.0))
    if duty == duty:  # not NaN
        hours *= max(min(duty, 1.0), 0.0)
    # Annual electricity used for recirc (MWh)
    if Precirc_total == Precirc_total:
        E_recirc_MWh = max(Precirc_total, 0.0) * hours
    else:
        E_recirc_MWh = 0.0
    opex_elec = elec_price * E_recirc_MWh / 1e6  # MUSD/y

    # Replacement / maintenance proxy: scale with neutron wall load
    nwl = float(outputs.get("neutron_wall_load_MW_m2", 0.0))
    k_maint = float(getattr(inputs, "k_cost_maint", 15.0))  # MUSD/y per MW/m2 proxy
    opex_maint = k_maint * max(nwl, 0.0)

    OPEX = opex_elec + opex_maint

    # COE proxy: (FCR*CAPEX + OPEX) / (E_net)
    fcr = float(getattr(inputs, "fixed_charge_rate", 0.10))
    if Pnet == Pnet and Pnet > 1e-6:
        Pnet_energy = outputs.get("P_e_net_avg_MW", Pnet)
        try:
            Pnet_energy = float(Pnet_energy)
        except Exception:
            Pnet_energy = Pnet
        E_net_MWh = max(Pnet_energy, 0.0) * hours
        COE = (fcr * CAPEX + OPEX) * 1e6 / max(E_net_MWh, 1e-9)  # USD/MWh
    else:
        COE = float("inf")

    # --- lifecycle proxy (discounted cashflow) ---
    plant_life = float(coeffs.get("plant_life_y", 30.0))
    discount_rate = float(coeffs.get("discount_rate", 0.07))
    decom_frac = float(coeffs.get("decom_fraction_of_capex", 0.10))
    install_factor = float(coeffs.get("replacement_installation_factor", 1.15))
    blanket_life = float(coeffs.get("blanket_life_y", 5.0))
    divertor_life = float(coeffs.get("divertor_life_y", 2.0))

    # component replacement part-cost proxies (MUSD)
    blanket_part = float(max(cost_blanket, 0.0))
    divertor_part = float(max(0.30 * cost_blanket, 0.0))  # transparent proxy: scaled to blanket size

    assumptions = LifecycleAssumptions(
        plant_life_y=plant_life,
        discount_rate=discount_rate,
        fixed_charge_rate=fcr,
        availability=avail,
        capacity_factor=capfac,
        decom_fraction_of_capex=decom_frac,
    )
    replacements = []
    if blanket_life > 0:
        replacements.append(ReplacementItem("blanket", interval_y=blanket_life, part_cost_MUSD=blanket_part, install_factor=install_factor))
    if divertor_life > 0:
        replacements.append(ReplacementItem("divertor", interval_y=divertor_life, part_cost_MUSD=divertor_part, install_factor=install_factor))

    lifecycle = discounted_cashflow_proxy(
        capex_MUSD=CAPEX,
        opex_MUSD_per_y=OPEX,
        net_electric_MWe=Pnet,
        assumptions=assumptions,
        replacements=replacements,
    )

    return {
        "cost_magnet_MUSD": float(cost_magnet),
        "cost_blanket_MUSD": float(cost_blanket),
        "cost_bop_MUSD": float(cost_bop),
        "cost_cryo_MUSD": float(cost_cryo),
        "CAPEX_proxy_MUSD": float(CAPEX),
        "OPEX_proxy_MUSD_per_y": float(OPEX),
        "COE_proxy_USD_per_MWh": float(COE),
        # lifecycle additions (backward compatible)
        "LCOE_proxy_USD_per_MWh": float(lifecycle.get("LCOE_proxy_USD_per_MWh", float("nan"))),
        "NPV_cost_proxy_MUSD": float(lifecycle.get("npv_cost_MUSD", float("nan"))),
        # structured economics for artifact (optional consumer)
        "_economics": lifecycle,
    }