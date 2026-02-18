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
import hashlib
from functools import lru_cache
from .lifecycle import discounted_cashflow_proxy, LifecycleAssumptions, ReplacementItem
from .components.stack_v356 import component_cost_proxy_v356
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
def cost_proxies(*args: Any, **kwargs: Any) -> Dict[str, float]:
    """Compute transparent CAPEX/OPEX/COE proxies.

    Backward compatibility
    ----------------------
    Earlier SHAMS UI prototypes sometimes called `cost_proxies(outputs)`.
    The authoritative signature is `cost_proxies(inputs, outputs)`.
    This function accepts both forms.
    """

    # Parse args
    if len(args) == 1 and isinstance(args[0], dict):
        inputs = kwargs.get("inputs", None)
        outputs = args[0]
    elif len(args) >= 2:
        inputs, outputs = args[0], args[1]
    else:
        inputs = kwargs.get("inputs", None)
        outputs = kwargs.get("outputs", {})

    coeffs = _load_cost_coeffs(
        str(getattr(inputs, "cost_coeffs_name", "default")) if inputs is not None else "default",
        str(getattr(inputs, "cost_coeffs_path", "")) if inputs is not None else "",
    )
    # optional global coeffs used later
    fcr_default = float(coeffs.get("fixed_charge_rate", 0.10))
    capfac_default = float(coeffs.get("capacity_factor", 0.75))
    # Geometry / scale
    R0 = float(getattr(inputs, "R0_m", float("nan"))) if inputs is not None else float(outputs.get("R0_m", float("nan")))
    a  = float(getattr(inputs, "a_m", float("nan"))) if inputs is not None else float(outputs.get("a_m", float("nan")))
    k  = float(getattr(inputs, "kappa", 1.0)) if inputs is not None else float(outputs.get("kappa", 1.0))
    Bt = float(getattr(inputs, "Bt_T", float("nan"))) if inputs is not None else float(outputs.get("Bt_T", float("nan")))
    Bpk = float(outputs.get("B_peak_T", Bt))
    Pnet = float(outputs.get("P_e_net_MW", float("nan")))
    Pfus = float(outputs.get("Pfus_total_MW", outputs.get("Pfus_MW", float("nan"))))
    Precirc = float(outputs.get("P_recirc_MW", float("nan")))
    Ppump = float(outputs.get("P_pump_MW", 0.0))
    Precirc_total = Precirc + (Ppump if math.isfinite(Ppump) else 0.0)
    Pcryo = float(getattr(inputs, "P_cryo_20K_MW", 0.0)) if inputs is not None else float(outputs.get("P_cryo_20K_MW", 0.0))
    # Basic scale volumes / areas
    # - Vacuum vessel surface proxy ~ 4π^2 R a k  (torus area scaling)
    area = 4.0 * math.pi**2 * max(R0, 0.1) * max(a, 0.05) * max(k, 1.0)
    # - Plasma volume proxy ~ 2π^2 R a^2 k
    # (kept for future proxy extensions)
    _vol = 2.0 * math.pi**2 * max(R0, 0.1) * max(a, 0.05)**2 * max(k, 1.0)

    # Magnet cost proxy: scales strongly with peak field & coil volume.
    # Use B^2 * volume scaling.
    k_mag = float(getattr(inputs, "k_cost_magnet", 0.12)) if inputs is not None else 0.12  # MUSD per (T^2*m^3) proxy
    # Coil volume proxy ~ torus area * t_coil; approximate t_coil ~ 0.5 m
    t_coil = float(getattr(inputs, "t_coil_proxy_m", 0.5)) if inputs is not None else 0.5
    V_coil = area * max(t_coil, 0.1)
    cost_magnet = k_mag * (max(Bpk, 0.0)**2) * V_coil

    # Blanket/shield/structure cost proxy: scales with vessel area and thickness
    k_blank = float(getattr(inputs, "k_cost_blanket", 0.08)) if inputs is not None else 0.08  # MUSD per (m^2*m)
    t_shield = float(getattr(inputs, "t_shield_m", 0.7)) if inputs is not None else float(outputs.get("t_shield_m", 0.7))
    cost_blanket = k_blank * area * max(t_shield, 0.1)

    # Balance-of-plant cost proxy: scales with thermal power
    k_bop = float(getattr(inputs, "k_cost_bop", 0.35)) if inputs is not None else 0.35  # MUSD per MW(th) proxy
    Pth = float(outputs.get("Pth_total_MW", float("nan")))
    cost_bop = k_bop * max(Pth if Pth==Pth else 0.0, 0.0)

    # Cryo plant CAPEX proxy: scales with cryo power
    k_cryo = float(getattr(inputs, "k_cost_cryo", 6.0)) if inputs is not None else 6.0  # MUSD per MW@20K proxy
    cost_cryo = k_cryo * max(Pcryo, 0.0)

    CAPEX = cost_magnet + cost_blanket + cost_bop + cost_cryo

    # --- Authority / provenance for economics (reviewer-visible) ---
    cost_coeffs_path = str(getattr(inputs, 'cost_coeffs_path', '')).strip() if inputs is not None else ''
    cost_authority_tier = 'proxy'
    cost_coeffs_sha256 = ''
    if cost_coeffs_path:
        # User override exists -> treat as external parametric (hashed).
        cost_authority_tier = 'external'
        try:
            p = Path(cost_coeffs_path)
            if p.exists() and p.is_file():
                cost_coeffs_sha256 = hashlib.sha256(p.read_bytes()).hexdigest()
        except Exception:
            pass
    else:
        # Default coeffs live in-repo: parametric proxy
        cost_authority_tier = 'parametric'

    cost_validity_domain = str(coeffs.get('validity_domain', 'Relative proxy; not a bankable plant cost.'))

    # --- Uncertainty bands (1-sigma, transparent) ---
    # Defaults are conservative; users may override via cost calibration JSON.
    sigma_mag = float(coeffs.get('sigma_cost_magnet_frac', 0.25))
    sigma_blank = float(coeffs.get('sigma_cost_blanket_frac', 0.25))
    sigma_bop = float(coeffs.get('sigma_cost_bop_frac', 0.20))
    sigma_cryo = float(coeffs.get('sigma_cost_cryo_frac', 0.30))
    def _band(x: float, s: float) -> tuple[float, float]:
        try:
            x = float(x)
            s = max(float(s), 0.0)
            return (x * (1.0 - s), x * (1.0 + s))
        except Exception:
            return (float('nan'), float('nan'))
    cost_magnet_low, cost_magnet_high = _band(cost_magnet, sigma_mag)
    cost_blanket_low, cost_blanket_high = _band(cost_blanket, sigma_blank)
    cost_bop_low, cost_bop_high = _band(cost_bop, sigma_bop)
    cost_cryo_low, cost_cryo_high = _band(cost_cryo, sigma_cryo)
    CAPEX_low = cost_magnet_low + cost_blanket_low + cost_bop_low + cost_cryo_low
    CAPEX_high = cost_magnet_high + cost_blanket_high + cost_bop_high + cost_cryo_high

    # Dominant driver + fragility index (max component fraction)
    comps = {
        'magnet': float(cost_magnet),
        'blanket_shield': float(cost_blanket),
        'bop': float(cost_bop),
        'cryo': float(cost_cryo),
    }
    dominant_cost_driver = max(comps, key=lambda k: comps.get(k, 0.0)) if comps else ''
    dominant_cost_frac = (comps.get(dominant_cost_driver, 0.0) / CAPEX) if (CAPEX and CAPEX > 0) else float('nan')
    cost_fragility_index = float(dominant_cost_frac) if dominant_cost_frac == dominant_cost_frac else float('nan')

    # OPEX proxy: proportional to recirculating power and component replacement
    # Use electricity price and a simple availability.
    elec_price = float(getattr(inputs, "electricity_price_USD_per_MWh", 60.0)) if inputs is not None else 60.0
    # Prefer model-derived availability if present in outputs; otherwise fall back to input.
    avail_out = outputs.get("availability_model", outputs.get("availability", float("nan")))
    try:
        avail_out = float(avail_out)
    except Exception:
        avail_out = float("nan")
    avail_in = float(getattr(inputs, "availability", 0.7)) if inputs is not None else 0.7
    avail = avail_in if not (avail_out == avail_out) else max(min(avail_out, 1.0), 0.0)
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
    k_maint = float(getattr(inputs, "k_cost_maint", 15.0)) if inputs is not None else 15.0  # MUSD/y per MW/m2 proxy
    opex_maint = k_maint * max(nwl, 0.0)

    OPEX = opex_elec + opex_maint

    # COE proxy: (FCR*CAPEX + OPEX) / (E_net)
    fcr = fcr_default
    if inputs is not None:
        fcr = float(getattr(inputs, "fixed_charge_rate", fcr_default))
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

    capfac = capfac_default
    if inputs is not None:
        capfac = float(getattr(inputs, "capacity_factor", capfac_default))

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

    # --- v356.0 PROCESS-like component CAPEX overlay (diagnostic) ---
    # This provides a richer CAPEX breakdown without changing legacy outputs.
    legacy_costs = {
        "cost_magnet_MUSD": float(cost_magnet),
        "cost_blanket_MUSD": float(cost_blanket),
        "cost_bop_MUSD": float(cost_bop),
        "cost_cryo_MUSD": float(cost_cryo),
    }
    comp = {}
    try:
        if inputs is not None:
            comp = component_cost_proxy_v356(inputs=inputs, outputs=outputs, legacy_costs=legacy_costs)
    except Exception:
        comp = {}

    # Contract fingerprint (in-repo)
    contract_sha = ""
    try:
        here = Path(__file__).resolve()
        contract_path = here.parents[2] / "contracts" / "cost_overlay_v356_contract.json"
        if contract_path.exists():
            contract_sha = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    except Exception:
        contract_sha = ""

    # --- (v360.0) Plant Economics Authority 1.0 (optional) ---
    econ_v360 = {}
    try:
        if inputs is not None and bool(getattr(inputs, 'include_economics_v360', False)):
            # Contract fingerprint
            econ_contract_sha = ''
            try:
                econ_contract_path = (Path(__file__).resolve().parents[2] / 'contracts' / 'economics_v360_contract.json')
                if econ_contract_path.exists():
                    econ_contract_sha = hashlib.sha256(econ_contract_path.read_bytes()).hexdigest()
            except Exception:
                econ_contract_sha = ''

            # Prefer v368 maintenance-aware net electric MWh/y if present, else v359
            net_mwh = float(outputs.get('net_electric_MWh_per_year_v368', float('nan')))
            if not (net_mwh == net_mwh):
                net_mwh = float(outputs.get('net_electric_MWh_per_year_v359', float('nan')))
            if not (net_mwh == net_mwh):
                # fall back to previously computed E_net_MWh (based on Pnet and hours)
                try:
                    net_mwh = float(E_net_MWh)
                except Exception:
                    net_mwh = float('nan')
            net_mwh = max(net_mwh, 0.0) if (net_mwh == net_mwh) else float('nan')

            # Replacement annual cost rate (prefer v368 maintenance/material-authoritative, else v359)
            repl_MUSD_per_y = float(outputs.get('replacement_cost_MUSD_per_year_v368', float('nan')))
            if not (repl_MUSD_per_y == repl_MUSD_per_y):
                repl_MUSD_per_y = float(outputs.get('replacement_cost_MUSD_per_year_v359', float('nan')))
            if not (repl_MUSD_per_y == repl_MUSD_per_y):
                repl_MUSD_per_y = 0.0

            # Electricity price
            elec_price = float(getattr(inputs, 'electricity_price_USD_per_MWh', 60.0))

            # Recirculating electricity already computed as opex_elec
            opex_elec_recirc = float(opex_elec)

            # Cryo wall-plug electricity
            cryo_mult = float(getattr(inputs, 'cryo_wallplug_multiplier', 250.0))
            Pcryo_wp_MW = max(float(Pcryo), 0.0) * max(cryo_mult, 0.0)
            opex_elec_cryo = (elec_price * Pcryo_wp_MW * hours) / 1e6

            # Heating/CD wall-plug electricity
            P_cd = float(outputs.get('P_cd_MW', outputs.get('Pcd_MW', outputs.get('P_CD_MW', 0.0))))
            eta_wp = float(outputs.get('eta_cd_wallplug', getattr(inputs, 'eta_cd_wallplug', 0.35)))
            eta_wp = max(min(eta_wp, 1.0), 1e-6)
            P_cd_wp = max(P_cd, 0.0) / eta_wp
            opex_elec_cd = (elec_price * P_cd_wp * hours) / 1e6

            # Tritium processing OPEX (throughput-based)
            T_proc_g_per_day = float(outputs.get('T_processing_required_g_per_day', float('nan')))
            if not (T_proc_g_per_day == T_proc_g_per_day):
                # fall back to burn rate (kg/day -> g/day)
                T_burn_kg_per_day = float(outputs.get('T_burn_kg_per_day', float('nan')))
                T_proc_g_per_day = (T_burn_kg_per_day * 1000.0) if (T_burn_kg_per_day == T_burn_kg_per_day) else 0.0
            T_cost = float(getattr(inputs, 'tritium_processing_cost_USD_per_g', 0.05))
            opex_trit = (max(T_proc_g_per_day, 0.0) * 365.0 * max(T_cost, 0.0)) / 1e6

            # Maintenance proxy (reuse)
            opex_maint = float(opex_maint)

            # Fixed OPEX
            opex_fixed = float(getattr(inputs, 'opex_fixed_MUSD_per_y', 0.0))

            opex_total = opex_fixed + opex_elec_recirc + opex_elec_cryo + opex_elec_cd + opex_trit + opex_maint

            # LCOE decomposition
            capex_for_lcoe = float(comp.get('CAPEX_component_proxy_MUSD', CAPEX)) if isinstance(comp, dict) else float(CAPEX)
            annual_cost_MUSD = fcr * capex_for_lcoe + repl_MUSD_per_y + opex_total
            if (net_mwh == net_mwh) and net_mwh > 1e-9:
                lcoe = (annual_cost_MUSD * 1e6) / net_mwh
                lcoe_capex = (fcr * capex_for_lcoe * 1e6) / net_mwh
                lcoe_repl = (repl_MUSD_per_y * 1e6) / net_mwh
                lcoe_opex = (opex_total * 1e6) / net_mwh
            else:
                lcoe = float('inf')
                lcoe_capex = float('nan')
                lcoe_repl = float('nan')
                lcoe_opex = float('nan')

            econ_v360 = {
                'economics_v360_contract_sha256': str(econ_contract_sha),
                'OPEX_v360_total_MUSD_per_y': float(opex_total),
                'OPEX_v360_fixed_MUSD_per_y': float(opex_fixed),
                'OPEX_v360_electric_recirc_MUSD_per_y': float(opex_elec_recirc),
                'OPEX_v360_electric_cryo_MUSD_per_y': float(opex_elec_cryo),
                'OPEX_v360_electric_cd_MUSD_per_y': float(opex_elec_cd),
                'OPEX_v360_tritium_processing_MUSD_per_y': float(opex_trit),
                'OPEX_v360_maint_MUSD_per_y': float(opex_maint),
                'LCOE_proxy_v360_USD_per_MWh': float(lcoe),
                'LCOE_v360_capex_USD_per_MWh': float(lcoe_capex),
                'LCOE_v360_replacement_USD_per_MWh': float(lcoe_repl),
                'LCOE_v360_opex_USD_per_MWh': float(lcoe_opex),
            }
    except Exception:
        econ_v360 = {}

    # --- (v383.0) Plant Economics & Cost Authority 2.0 (optional; OFF by default) ---
    # Deterministic structured CAPEX + availability-tiered CF + LCOE-lite.
    econ_v383: Dict[str, Any] = {}
    try:
        if inputs is not None and bool(getattr(inputs, 'include_economics_v383', False)):
            econ_contract_sha = ''
            try:
                econ_contract_path = (Path(__file__).resolve().parents[2] / 'contracts' / 'economics_v383_contract.json')
                if econ_contract_path.exists():
                    econ_contract_sha = hashlib.sha256(econ_contract_path.read_bytes()).hexdigest()
            except Exception:
                econ_contract_sha = ''

            # Prefer structured component CAPEX if available (v356 overlay), else legacy CAPEX proxy.
            capex_struct = float('nan')
            if isinstance(comp, dict):
                capex_struct = float(comp.get('CAPEX_component_proxy_MUSD', float('nan')))
            if not (capex_struct == capex_struct):
                capex_struct = float(CAPEX)

            prox = float(outputs.get('disruption_proximity_index', float('nan')))
            ctrl = float(outputs.get('control_power_margin_cert_v378', outputs.get('control_power_margin', float('nan'))))
            vs = float(outputs.get('volt_second_headroom_frac', outputs.get('volt_second_headroom', float('nan'))))
            tq = float(outputs.get('thermal_quench_severity_W_per_m2', outputs.get('thermal_quench_proxy', float('nan'))))

            tier = 'B'
            if (prox == prox) and math.isfinite(prox):
                if prox >= float(coeffs.get('v383_disruption_proximity_high', 0.75)):
                    tier = 'C'
                elif prox <= float(coeffs.get('v383_disruption_proximity_low', 0.35)):
                    tier = 'A'
            if (ctrl == ctrl) and math.isfinite(ctrl) and ctrl < float(coeffs.get('v383_control_margin_min', 0.10)):
                tier = 'C'
            if (vs == vs) and math.isfinite(vs) and vs < float(coeffs.get('v383_vs_headroom_min', 0.05)):
                tier = 'C'
            if (tq == tq) and math.isfinite(tq) and tq >= float(coeffs.get('v383_quench_severity_high', 1.0e7)):
                tier = 'C'

            cf_map = {
                'A': float(coeffs.get('v383_capacity_factor_A', 0.85)),
                'B': float(coeffs.get('v383_capacity_factor_B', 0.70)),
                'C': float(coeffs.get('v383_capacity_factor_C', 0.50)),
            }
            cf = float(cf_map.get(tier, 0.70))
            cf = max(0.0, min(0.95, cf))

            net_mwh = float(outputs.get('net_electric_MWh_per_year_v368', float('nan')))
            if not (net_mwh == net_mwh):
                net_mwh = float(outputs.get('net_electric_MWh_per_year_v359', float('nan')))
            if not (net_mwh == net_mwh):
                duty = float(outputs.get('duty_factor', 1.0))
                duty = max(0.0, min(1.0, duty)) if (duty == duty) else 1.0
                Pnet_eff = float(Pnet) if (Pnet == Pnet) else float('nan')
                if (Pnet_eff == Pnet_eff) and math.isfinite(Pnet_eff):
                    net_mwh = max(Pnet_eff, 0.0) * 8760.0 * cf * duty
                else:
                    net_mwh = float('nan')

            elec_price = float(getattr(inputs, 'electricity_price_USD_per_MWh', 60.0))
            hours_cf = 8760.0 * cf
            opex_elec_recirc = (elec_price * max(Precirc_total, 0.0) * hours_cf) / 1e6 if (Precirc_total == Precirc_total) else 0.0
            cryo_mult = float(getattr(inputs, 'cryo_wallplug_multiplier', 250.0))
            Pcryo_wp_MW = max(float(Pcryo), 0.0) * max(cryo_mult, 0.0)
            opex_elec_cryo = (elec_price * Pcryo_wp_MW * hours_cf) / 1e6

            P_cd = float(outputs.get('P_cd_MW', outputs.get('Pcd_MW', outputs.get('P_CD_MW', 0.0))))
            eta_wp = float(outputs.get('eta_cd_wallplug', getattr(inputs, 'eta_cd_wallplug', 0.35)))
            eta_wp = max(min(eta_wp, 1.0), 1e-6)
            P_cd_wp = max(P_cd, 0.0) / eta_wp
            opex_elec_cd = (elec_price * P_cd_wp * hours_cf) / 1e6

            T_proc_g_per_day = float(outputs.get('T_processing_required_g_per_day', float('nan')))
            if not (T_proc_g_per_day == T_proc_g_per_day):
                T_burn_kg_per_day = float(outputs.get('T_burn_kg_per_day', float('nan')))
                T_proc_g_per_day = (T_burn_kg_per_day * 1000.0) if (T_burn_kg_per_day == T_burn_kg_per_day) else 0.0
            T_cost = float(getattr(inputs, 'tritium_processing_cost_USD_per_g', 0.05))
            opex_trit = (max(T_proc_g_per_day, 0.0) * 365.0 * max(T_cost, 0.0)) / 1e6

            opex_maint_struct = float(opex_maint)
            repl_MUSD_per_y = float(outputs.get('replacement_cost_MUSD_per_year_v368', float('nan')))
            if not (repl_MUSD_per_y == repl_MUSD_per_y):
                repl_MUSD_per_y = float(outputs.get('replacement_cost_MUSD_per_year_v359', float('nan')))
            if not (repl_MUSD_per_y == repl_MUSD_per_y):
                repl_MUSD_per_y = 0.0

            opex_fixed = float(getattr(inputs, 'opex_fixed_MUSD_per_y', 0.0))
            opex_struct = float(opex_fixed + opex_elec_recirc + opex_elec_cryo + opex_elec_cd + opex_trit + opex_maint_struct + max(repl_MUSD_per_y, 0.0))

            fcr = float(getattr(inputs, 'fixed_charge_rate', fcr_default))
            fcr = max(0.0, min(0.30, fcr))

            if (net_mwh == net_mwh) and net_mwh > 1e-9 and math.isfinite(net_mwh):
                lcoe_lite = ((fcr * capex_struct) + opex_struct) * 1e6 / net_mwh
            else:
                lcoe_lite = float('inf')

            econ_v383 = {
                'economics_v383_contract_sha256': str(econ_contract_sha),
                'CAPEX_structured_v383_MUSD': float(capex_struct),
                'OPEX_structured_v383_MUSD_per_y': float(opex_struct),
                'availability_tier_v383': str(tier),
                'capacity_factor_used_v383': float(cf),
                'net_electric_MWh_per_year_used_v383': float(net_mwh) if (net_mwh == net_mwh) else float('nan'),
                'LCOE_lite_v383_USD_per_MWh': float(lcoe_lite),
                'dominant_cost_driver_v383': str(dominant_cost_driver),
                'dominant_cost_frac_v383': float(dominant_cost_frac),
                'CAPEX_structured_max_MUSD': float(getattr(inputs, 'CAPEX_structured_max_MUSD', float('nan'))),
                'OPEX_structured_max_MUSD_per_y': float(getattr(inputs, 'OPEX_structured_max_MUSD_per_y', float('nan'))),
                'LCOE_lite_max_USD_per_MWh': float(getattr(inputs, 'LCOE_lite_max_USD_per_MWh', float('nan'))),
            }
    except Exception:
        econ_v383 = {}

    return {
        "cost_magnet_MUSD": float(cost_magnet),
        "cost_blanket_MUSD": float(cost_blanket),
        "cost_bop_MUSD": float(cost_bop),
        "cost_cryo_MUSD": float(cost_cryo),
        "cost_magnet_MUSD_low": float(cost_magnet_low),
        "cost_magnet_MUSD_high": float(cost_magnet_high),
        "cost_blanket_MUSD_low": float(cost_blanket_low),
        "cost_blanket_MUSD_high": float(cost_blanket_high),
        "cost_bop_MUSD_low": float(cost_bop_low),
        "cost_bop_MUSD_high": float(cost_bop_high),
        "cost_cryo_MUSD_low": float(cost_cryo_low),
        "cost_cryo_MUSD_high": float(cost_cryo_high),
        "CAPEX_proxy_MUSD_low": float(CAPEX_low),
        "CAPEX_proxy_MUSD_high": float(CAPEX_high),
        "cost_authority_tier": str(cost_authority_tier),
        "cost_coeffs_sha256": str(cost_coeffs_sha256),
        "cost_validity_domain": str(cost_validity_domain),
        "dominant_cost_driver": str(dominant_cost_driver),
        "dominant_cost_frac": float(dominant_cost_frac),
        "cost_fragility_index": float(cost_fragility_index),
        "CAPEX_proxy_MUSD": float(CAPEX),
        "OPEX_proxy_MUSD_per_y": float(OPEX),
        "COE_proxy_USD_per_MWh": float(COE),
        # lifecycle additions (backward compatible)
        "LCOE_proxy_USD_per_MWh": float(lifecycle.get("LCOE_proxy_USD_per_MWh", float("nan"))),
        "NPV_cost_proxy_MUSD": float(lifecycle.get("npv_cost_MUSD", float("nan"))),
        # v356 overlay
        "cost_overlay_contract_sha256": str(contract_sha),
        "CAPEX_max_proxy_MUSD": float(getattr(inputs, "CAPEX_max_proxy_MUSD", float("nan"))) if inputs is not None else float("nan"),
        **(comp if isinstance(comp, dict) else {}),
        **(econ_v360 if isinstance(econ_v360, dict) else {}),
        **(econ_v383 if isinstance(econ_v383, dict) else {}),
        # structured economics for artifact (optional consumer)
        "_economics": lifecycle,
    }