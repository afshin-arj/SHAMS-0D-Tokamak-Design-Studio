from __future__ import annotations
"""Constraint evaluation for SHAMS (systems-code style).

PROCESS-style workflows are constraint-driven: iteration variables are adjusted until a target set is met
and all constraints are satisfied. SHAMS promotes its former UI-only "checks" into reusable constraints.

This module:
- Defines a ``Constraint`` record (value, limits, residual, ok flag)
- Builds a consistent constraint list from a model output dict
- Provides small helpers to summarize / filter constraints for UI and solvers

Constraints are intentionally simple and interpretable; they can be expanded as new submodels are added.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Constraint:
    name: str
    value: float
    lo: Optional[float] = None
    hi: Optional[float] = None
    units: str = "-"
    description: str = ""

    @property
    def ok(self) -> bool:
        if self.lo is not None and self.value < self.lo:
            return False
        if self.hi is not None and self.value > self.hi:
            return False
        return True

    def residual(self) -> float:
        """Normalized violation (0 if satisfied)."""
        if self.lo is not None and self.value < self.lo:
            denom = abs(self.lo) if abs(self.lo) > 1e-9 else 1.0
            return (self.lo - self.value) / denom
        if self.hi is not None and self.value > self.hi:
            denom = abs(self.hi) if abs(self.hi) > 1e-9 else 1.0
            return (self.value - self.hi) / denom
        return 0.0


def _safe(out: Dict[str, float], k: str) -> float:
    try:
        return float(out.get(k, float("nan")))
    except Exception:
        return float("nan")


def build_constraints_from_outputs(out: Dict[str, float], design_intent: Optional[str] = None, **_ignored: object) -> List[Constraint]:
    """Build a PROCESS-like constraint list from hot_ion_point outputs.

    Philosophy: constraints with missing/NaN values are omitted (not failed),
    so legacy runs remain robust.
    """
    cs: List[Constraint] = []

    def add(name: str, value_key: str, lo_key: Optional[str] = None, hi_key: Optional[str] = None,
            units: str = "-", description: str = ""):
        v = _safe(out, value_key)
        if v != v:  # NaN
            return
        lo = _safe(out, lo_key) if lo_key else None
        hi = _safe(out, hi_key) if hi_key else None
        if lo_key and (lo != lo):
            lo = None
        if hi_key and (hi != hi):
            hi = None
        cs.append(Constraint(name=name, value=v, lo=lo, hi=hi, units=units, description=description))

    def add_bool(name: str, value_key: str, description: str = ""):
        v = _safe(out, value_key)
        if v != v:
            return
        cs.append(Constraint(name=name, value=v, lo=1.0, hi=None, units="bool", description=description))

    # Geometry / build
    add_bool("Radial build closes", "radial_build_ok", description="Inboard radial build feasibility (1=ok).")
    add("Inboard stack closes", "stack_ok", units="bool", description="Inboard stack including TF coil fits inside R0-a (1=ok).")

    # Shaping (optional screening bounds; NaN disables)
    add("Elongation (kappa)", "kappa", hi_key="kappa_max", units="-", description="Optional cap on elongation proxy.")
    add("Triangularity (delta)", "delta", lo_key="delta_min", hi_key="delta_max", units="-", description="Optional bounds on triangularity proxy.")

    # Minimum thickness constraints from explicit radial stack (if present)
    if isinstance(out.get('radial_stack'), list):
        for r in out['radial_stack']:
            try:
                name = str(r.get('name','region'))
                t = float(r.get('thickness_m', float('nan')))
                tmin = float(r.get('min_thickness_m', 0.0) or 0.0)
                if t == t and tmin > 0.0:
                    cs.append(Constraint(name=f"{name} thickness", value=t, lo=tmin, hi=None, units='m', description='Minimum thickness requirement (radial stack)'))
            except Exception:
                continue

# Operations
    add_bool("L-H access", "LH_ok", description="H-mode access proxy (1=ok).")
    add("H-mode power margin", "Paux_MW", lo_key="P_LH_required_MW", units="MW", description="If H-mode required, enforces Paux ≥ (1+margin)*P_LH.")

    # Particle sustainability (optional)
    add("Fueling source required", "S_fuel_required_1e22_per_s", hi_key="S_fuel_max_1e22_per_s", units="1e22/s",
        description="0-D particle sustainability proxy: required fueling source must be ≤ max, if enabled.")
    add_bool("Fueling sustainability", "fueling_ok", description="Fueling sustainability flag (1=ok) when particle balance closure is enabled.")

    # Confinement requirement (output constraint; optional cap via H98_allow)
    add("Required confinement (H_required)", "H_required", hi_key="H98_allow", units="-",
        description="Derived required H-factor (relative to IPB98(y,2)) for the computed point. Optional cap via H98_allow.")

    # Power/confinement self-consistency (optional)
    try:
        res = _safe(out, "power_balance_residual_MW")
        tol = _safe(out, "power_balance_tol_MW")
        if res == res and tol == tol and tol > 0.0:
            cs.append(Constraint(
                name="Power/confinement residual",
                value=abs(float(res)),
                lo=None,
                hi=float(tol),
                units="MW",
                description="|Ploss - W/tauE_model|. Optional cap when power_balance_tol_MW is set.",
            ))
    except Exception:
        pass

    # Optional stability screening caps
    add("Normalized beta (betaN)", "betaN_proxy", hi_key="betaN_max", units="-",
        description="Screening proxy: betaN must be below cap when betaN_max is set.")
    add("Troyon beta_N", "beta_N", hi_key="betaN_troyon_max", units="-",
        description="Optional Troyon-like cap on beta_N (uses evaluator beta_N output).")
    add("Safety factor (q95)", "q95_proxy", lo_key="q95_min", units="-",
        description="Screening proxy: q95 must exceed minimum when q95_min is set.")

    # TF / structures
    add("TF peak field", "B_peak_T", hi_key="B_peak_allow_T", units="T", description="Peak TF field at inner leg.")
    add("Hoop stress", "sigma_hoop_MPa", hi_key="sigma_allow_MPa", units="MPa", description="Hoop stress proxy at inner leg.")
    add("Von Mises stress", "sigma_vm_MPa", hi_key="sigma_allow_MPa", units="MPa", description="Von Mises stress proxy (thin-shell).")
    add("TF engineering current density", "J_eng_A_mm2", hi_key="J_eng_max_A_mm2", units="A/mm^2",
        description="Engineering current density in TF winding pack (proxy).")
    add("HTS margin (critical surface)", "hts_margin_cs", lo_key="hts_margin_min", units="-",
        description="HTS margin computed from Jc(B,T,ε)/Jeng (fit proxy).")
    add("HTS margin (legacy)", "hts_margin", lo_key="hts_margin_min", units="-",
        description="Legacy HTS margin proxy (kept for continuity).")

    # Power exhaust
    add("SOL power exhaust (P_SOL/R)", "P_SOL_over_R_MW_m", hi_key="P_SOL_over_R_max_MW_m", units="MW/m",
        description="Power crossing separatrix per major radius.")
    add("Divertor heat flux (target)", "q_div_MW_m2", hi_key="q_div_max_MW_m2", units="MW/m^2",
        description="Divertor target heat-flux proxy using λq and flux expansion.")
    # Exhaust authority (v285.0)
    add("Detachment index", "detachment_index", hi_key="detachment_index_max", units="MW/(1e40 m^-6·m)",
        description="Detachment access proxy: P_SOL/(n_e^2 R). Optional cap detachment_index_max.")
    add("Radiated fraction total", "f_rad_total", hi_key="f_rad_total_max", units="-",
        description="Total radiative fraction proxy (core + divertor). Optional cap f_rad_total_max.")
    add("Fuel ion fraction", "fuel_ion_fraction", lo_key="fuel_ion_fraction_min", units="-",
        description="Fuel ion fraction (dilution proxy). Optional minimum fuel_ion_fraction_min.")
    add("Effective Q (dilution-adjusted)", "Q_effective", lo_key="Q_effective_min", units="-",
        description="Q degraded by fuel ion fraction squared: Q_eff=Q*fuel^2. Optional minimum Q_effective_min.")

    # Magnet quench authority (v285.0)
    add("Magnet quench risk proxy", "magnet_quench_risk_proxy", hi_key="magnet_quench_risk_max", units="-",
        description="Proxy ratio of stored magnetic energy to allowable (from quench_energy_density_max_MJ_m3). Optional cap magnet_quench_risk_max.")


    # Pulse / flux
    add("Flat-top duration", "t_flat_s", lo_key="pulse_min_s", units="s",
        description="Flat-top duration in pulsed mode (if computed).")
    add("CS flux swing (required ≤ available)", "cs_flux_required_Wb", hi_key="cs_flux_available_Wb", units="Wb",
        description="Central-solenoid flux swing proxy: required inductive flux must be below available CS flux.")
    add("CS loop voltage (ramp)", "cs_V_loop_ramp_V", hi_key="cs_V_loop_max_V", units="V",
        description="Optional cap on loop voltage proxy during ramp (derived from flux swing / ramp time).")
    add("CS flux margin", "cs_flux_margin", lo_key="cs_flux_margin_min", units="-",
        description="Flux margin (avail-req)/req; optional minimum requirement.")

    # Control & stability authority (v298.0): optional caps on deterministic envelopes
    add("VS control bandwidth (required)", "vs_bandwidth_req_Hz", hi_key="vs_bandwidth_max_Hz", units="Hz",
        description="Vertical stability control bandwidth requirement (proxy) must be below cap when set.")
    add("VS control power (required)", "vs_control_power_req_MW", hi_key="vs_control_power_max_MW", units="MW",
        description="Vertical stability control power requirement (proxy) must be below cap when set.")
    add("PF envelope peak current", "pf_I_peak_MA", hi_key="pf_I_peak_max_MA", units="MA",
        description="PF peak current requirement (contract) must be below cap when set.")
    add("PF envelope peak dI/dt", "pf_dIdt_peak_MA_s", hi_key="pf_dIdt_max_MA_s", units="MA/s",
        description="PF peak ramp rate requirement (contract) must be below cap when set.")
    add("PF envelope peak voltage", "pf_V_peak_V", hi_key="pf_V_peak_max_V", units="V",
        description="PF peak voltage requirement (contract) must be below cap when set.")
    add("PF envelope peak power", "pf_P_peak_MW", hi_key="pf_P_peak_max_MW", units="MW",
        description="PF peak electrical power requirement (contract) must be below cap when set.")
    add("PF pulse energy", "pf_E_pulse_MJ", hi_key="pf_E_pulse_max_MJ", units="MJ",
        description="PF pulse energy proxy (contract) must be below cap when set.")
    add("RWM control bandwidth (required)", "rwm_bandwidth_req_Hz", hi_key="rwm_bandwidth_max_Hz", units="Hz",
        description="RWM bandwidth requirement must be below cap when set (active regime only).")
    add("RWM control power (required)", "rwm_control_power_req_MW", hi_key="rwm_control_power_max_MW", units="MW",
        description="RWM control power requirement must be below cap when set (active regime only).")

    # TF coil thermal (optional)
    add("TF coil thermal load", "coil_heat_MW", hi_key="coil_cooling_capacity_MW", units="MW",
        description="TF coil heating proxy (nuclear + AC) must not exceed cooling capacity proxy.")
    add("TF coil heat (hard cap)", "coil_heat_MW", hi_key="coil_heat_max_MW", units="MW",
        description="Optional hard cap on TF coil heating proxy.")

    # Net electric (optional)
    add("Net electric power", "P_net_MW", lo_key="P_net_min_MW", units="MW",
        description="Net electric power must exceed minimum, if enabled.")

    # Plant power ledger caps (optional; NaN disables)
    add("Recirculating fraction", "f_recirc", hi_key="f_recirc_max", units="-",
        description="Recirculating fraction Precirc/Pe_gross must be below cap when enabled.")
    add("PF average electric draw", "P_pf_avg_MW", hi_key="P_pf_avg_max_MW", units="MW",
        description="Average PF electric draw proxy (pf_E_pulse/t_cycle) must be below cap when enabled.")
    add("Cryo electric draw", "P_cryo_MW", hi_key="P_cryo_max_MW", units="MW",
        description="Cryogenic electric draw proxy must be below cap when enabled.")
    add("Aux + CD electric draw", "P_aux_total_el_MW", hi_key="P_aux_max_MW", units="MW",
        description="Auxiliary+CD wallplug electric draw proxy must be below cap when enabled.")

    # Economics overlay (v356.0) — optional hard cap on component CAPEX proxy (NaN disables)
    add("Component CAPEX proxy", "CAPEX_component_proxy_MUSD", hi_key="CAPEX_max_proxy_MUSD", units="MUSD",
        description="Optional cap on PROCESS-style component CAPEX proxy total. Diagnostic only; no hidden weighting.")

    # Fuel-cycle / tritium (optional; NaN disables)
    add("Fuel-cycle TBR requirement", "TBR", lo_key="TBR_required_fuelcycle", units="-",
        description="TBR must exceed the fuel-cycle-required proxy (contract).")
    add("Tritium inventory (required)", "T_inventory_required_kg", lo_key="T_inventory_min_kg", units="kg",
        description="Required on-site tritium inventory proxy must exceed minimum inventory contract when enabled.")
    add("Tritium processing capacity", "T_processing_capacity_min_g_per_day", lo_key="T_processing_required_g_per_day", units="g/day",
        description="Processing capacity contract must exceed the required throughput proxy (conservative).")

    # v350.0 tight closure caps (optional; NaN disables)
    add("In-vessel tritium inventory (proxy)", "T_in_vessel_required_kg", hi_key="T_in_vessel_max_kg", units="kg",
        description="In-vessel tritium inventory proxy from processing delay must be below max when enabled.")
    add("Total tritium inventory (proxy)", "T_total_inventory_required_kg", hi_key="T_total_inventory_max_kg", units="kg",
        description="Total tritium inventory proxy (reserve+in-vessel+startup) must be below max when enabled.")
    add("Fuel-cycle self-sufficiency (effective TBR)", "TBR_eff_fuelcycle", lo_key="TBR_self_sufficiency_required", units="-",
        description="Effective TBR after declared losses must exceed 1+margin when TBR_self_sufficiency_required is finite.")

    # Burn / ignition screening (optional; NaN disables)
    add("Ignition margin (Pα/Ploss)", "M_ign", lo_key="ignition_margin_min", units="-",
        description="Ignition-like margin proxy: requires Palpha/Ploss ≥ threshold when ignition_margin_min is set.")

    # Neutronics screening (optional; NaN disables)
    add("Neutron wall load", "neutron_wall_load_MW_m2", hi_key="neutron_wall_load_max_MW_m2", units="MW/m^2",
        description="Optional cap on neutron wall loading proxy when neutron_wall_load_max_MW_m2 is set.")

    # v372.0: Neutronics–Materials Coupling Authority 2.0 (governance-only)
    # These constraints are active only when the corresponding caps are explicitly set (NaN disables).
    add("Eff. DPA rate (v372)", "dpa_rate_eff_per_fpy_v372", hi_key="dpa_rate_eff_max_v372", units="DPA/FPY",
        description="Material+ spectrum-conditioned effective DPA rate proxy (screening).")
    add("Damage margin (v372)", "damage_margin_v372", lo_key="damage_margin_min_v372", units="-",
        description="Normalized margin against the explicit DPA cap (>=0 is feasible).")
    add_bool("Materials temp window (v372)", "nm_temp_window_ok_v372",
        description="If operating temperature is provided, 1 indicates within material window; outside triggers conservative penalty.")

    # Nuclear heating / materials replacement (optional; NaN disables)
    add("Total nuclear heating", "P_nuc_total_MW", hi_key="P_nuc_total_max_MW", units="MW",
        description="Optional cap on total nuclear heating proxy from stack region shares.")
    add("TF nuclear heating", "P_nuc_TF_MW", hi_key="P_nuc_tf_max_MW", units="MW",
        description="Optional cap on TF nuclear heating proxy (winding pack + structure).")
    add("First-wall lifetime", "fw_lifetime_yr", lo_key="fw_lifetime_min_yr", units="yr",
        description="Optional minimum first-wall lifetime proxy derived from dpa/y and a material dpa limit.")
    add("Blanket lifetime", "blanket_lifetime_yr", lo_key="blanket_lifetime_min_yr", units="yr",
        description="Optional minimum blanket lifetime proxy derived from blanket dpa/y and a material dpa limit.")

    # (v367.0) Materials lifetime closure: cadence + plant-life policy
    add("FW replacement cadence", "fw_replace_interval_y", lo_key="fw_replace_interval_min_yr", units="yr",
        description="Optional minimum first-wall replacement cadence (years) applied to fw_replace_interval_y.")
    add("Blanket replacement cadence", "blanket_replace_interval_y", lo_key="blanket_replace_interval_min_yr", units="yr",
        description="Optional minimum blanket replacement cadence (years) applied to blanket_replace_interval_y.")


# Risk / lifetime / availability / PF / Tritium
    # --- (v264.0) Non-inductive and disruption/radiative risk screens ---
    add("Non-inductive fraction", "f_NI", lo_key="f_NI_min", units="-",
    description="Requires (I_bootstrap + I_cd)/Ip ≥ min when enabled.")
    # v357.0 CD channel engineering caps (optional; NaN disables)
    add("LHCD n_parallel", "lhcd_n_parallel", lo_key="lhcd_n_parallel_min", hi_key="lhcd_n_parallel_max", units="-",
    description="LHCD parallel refractive index (n||) must lie within optional bounds when set.")
    add("ECCD launcher power density", "eccd_launcher_power_density_MW_m2", hi_key="eccd_launcher_power_density_max_MW_m2", units="MW/m^2",
    description="ECCD launcher power density proxy P_cd/A_launcher must be below cap when set.")
    add("NBI shine-through fraction", "nbi_shinethrough_frac", hi_key="nbi_shinethrough_frac_max", units="-",
    description="NBI shine-through fraction proxy must be below cap when set.")

    add("Disruption risk proxy", "disruption_risk_proxy", hi_key="disruption_risk_max", units="-",
    description="Conservative disruption risk screening proxy (lower is better). Optional cap.")
    add("Core radiative fraction", "f_rad_core", hi_key="f_rad_core_max", units="-",
    description="Core radiative fraction proxy Prad_core/Ploss. Optional cap.")
    add("Edge-core coupled radiative fraction", "f_rad_core_edge_core", hi_key="f_rad_core_edge_core_max", units="-",
    description="Proxy: (Prad_core + chi_core·Prad_req(SOL+div))/Ploss. Optional cap when edge-core coupling is enabled.")

    add("Bootstrap–pressure self-consistency |Δf_bs|", "bsp_abs_delta_f_bootstrap", hi_key="f_bootstrap_consistency_abs_max", units="-",
    description="If enabled, requires |f_bs(reported) - f_bs(expected)| <= cap. Optional cap.")

    add("MHD risk proxy", "mhd_risk_proxy", hi_key="mhd_risk_max", units="-",
    description="Lightweight operational risk proxy (smaller is better). Optional hard cap.")
    add("Vertical stability margin", "vs_margin", lo_key="vs_margin_min", units="-",
    description="Vertical stability margin proxy (larger is better). Optional minimum requirement.")
    add("First-wall dpa per year", "fw_dpa_per_year", hi_key="fw_dpa_max_per_year", units="dpa/y",
    description="First-wall damage proxy from neutron wall load (order-of-magnitude).")
    add("Divertor erosion", "div_erosion_mm_per_year", hi_key="div_erosion_max_mm_per_y", units="mm/y",
    description="Divertor erosion proxy from heat flux and duty factor.")
    add("Availability (model)", "availability_model", lo_key="availability_min", units="-",
    description="Availability proxy from scheduled replacements and trips.")

    # --- (v359.0) Availability & replacement ledger authority (optional) ---
    add("Availability (v359)", "availability_v359", lo_key="availability_v359_min", units="-",
        description="Availability including planned/forced baselines and replacement downtime (v359).")
    add("LCOE proxy (v359)", "LCOE_proxy_v359_USD_per_MWh", hi_key="LCOE_max_USD_per_MWh", units="USD/MWh",
        description="Lifecycle-style LCOE proxy using CAPEX/OPEX proxies and v359 replacement cost rate.")

    # --- (v368.0) Maintenance Scheduling Authority 1.0 (optional) ---
    add("Availability (v368)", "availability_v368", lo_key="availability_v368_min", units="-",
        description="Maintenance-schedule-dominated availability including bundled replacements and trip model (v368).")
    add("Total outage fraction (v368)", "outage_total_frac_v368", hi_key="outage_fraction_v368_max", units="-",
        description="Optional cap on planned+forced+replacement outage fraction from v368 schedule closure.")
    # --- (v360.0) Plant Economics Authority 1.0 (optional) ---
    add("OPEX (v360)", "OPEX_v360_total_MUSD_per_y", hi_key="OPEX_max_MUSD_per_y", units="MUSD/y",
        description="Total OPEX decomposition including recirc+cryo+CD electricity, tritium processing, maintenance, and fixed OPEX (v360).")
    add("LCOE proxy (v360)", "LCOE_proxy_v360_USD_per_MWh", hi_key="LCOE_max_USD_per_MWh", units="USD/MWh",
        description="Availability-coupled LCOE proxy using CAPEX component proxy (v356), replacement cost rate (v359), and OPEX decomposition (v360).")
    add("Tritium inventory proxy", "T_inventory_proxy_g", hi_key="tritium_inventory_max_g", units="g",
    description="Tritium inventory proxy derived from burn rate and processing reserve.")
    add("PF coil current proxy", "pf_I_pf_MA", hi_key="pf_current_max_MA", units="MA",
    description="PF coil current demand proxy (screening).")
    add("PF stress proxy", "pf_stress_proxy", hi_key="pf_stress_max", units="-",
    description="PF coil stress proxy (screening).")

    # --- (v226.0) Envelope-based control contracts (optional) ---
    add("VS control bandwidth required", "vs_bandwidth_req_Hz", hi_key="vs_bandwidth_max_Hz", units="Hz",
    description="Vertical stability control bandwidth requirement (proxy) must be below max if set.")
    add("VS control power required", "vs_control_power_req_MW", hi_key="vs_control_power_max_MW", units="MW",
    description="Vertical stability control power requirement (proxy) must be below max if set.")
    add("PF waveform peak current", "pf_I_peak_MA", hi_key="pf_I_peak_max_MA", units="MA",
    description="Canonical PF waveform peak current must be below max if set.")
    add("PF waveform peak voltage", "pf_V_peak_V", hi_key="pf_V_peak_max_V", units="V",
    description="Canonical PF waveform peak voltage must be below max if set.")
    add("PF waveform peak power", "pf_P_peak_MW", hi_key="pf_P_peak_max_MW", units="MW",
    description="Canonical PF waveform peak electrical power must be below max if set.")
    add("PF waveform dI/dt", "pf_dIdt_peak_MA_s", hi_key="pf_dIdt_max_MA_s", units="MA/s",
    description="Canonical PF waveform peak current slew rate must be below max if set.")
    add("SOL radiation fraction required", "f_rad_SOL_required", hi_key="f_rad_SOL_max", units="-",
    description="If SOL radiation control is enabled, required SOL radiation fraction must be <= max if set.")

    # --- (v229.0) RWM screening (optional, PROCESS-class depth) ---
    # Enforces: beta_N <= beta_N_ideal-wall (screen) and required control authority within caps.
    add("RWM ideal-wall beta_N limit", "beta_N", hi_key="rwm_betaN_ideal_wall", units="-",
    description="If RWM screening is enabled, beta_N must remain below ideal-wall proxy limit; exceeding implies non-operable." )
    add("RWM control bandwidth required", "rwm_bandwidth_req_Hz", hi_key="rwm_bandwidth_max_Hz", units="Hz",
    description="RWM closed-loop bandwidth requirement (proxy) must be <= cap if set (defaults to VS cap if not provided).")
    add("RWM control power required", "rwm_control_power_req_MW", hi_key="rwm_control_power_max_MW", units="MW",
    description="RWM control power requirement (proxy) must be <= cap if set (defaults to VS power cap if not provided).")
    
    # --- Phase-2 engineering closures (PROCESS-inspired) ---
    add("TF current density", "tf_Jop_MA_per_mm2", hi_key="tf_Jop_limit_MA_per_mm2", units="MA/mm^2",
    description="Operating current density must be below limit (proxy).")
    add("TF stress", "tf_stress_MPa", hi_key="tf_stress_allow_MPa", units="MPa",
    description="TF coil stress proxy must be below allowable.")
    add("TF strain", "tf_strain", hi_key="tf_strain_allow", units="-",
    description="TF coil strain proxy must be below allowable (screening). Optional cap.")

    # --- (v288.0) Magnet authority 2.0 ---
    add("TF peak field", "tf_Bpeak_T", hi_key="B_peak_allow_T", units="T",
    description="TF peak field at winding pack (proxy) must be below allowable.")
    add("HTS margin", "tf_hts_margin", lo_key="hts_margin_min", units="-",
    description="HTS critical-surface margin Jc(B,T,ε)/Jop must exceed minimum if enabled.")
    add("Magnet quench risk proxy", "magnet_quench_risk_proxy", hi_key="magnet_quench_risk_max", units="-",
    description="Quench/protection risk proxy must be below cap if set (energy density relative to allowable).")
    add("Divertor heat flux", "q_parallel_MW_per_m2", hi_key="q_parallel_limit_MW_per_m2", units="MW/m^2",
    description="Parallel heat flux proxy must be below technology-mode limit.")

    # --- (v287.0) Exhaust authority 2.0 ---
    add("Detachment access index", "detachment_index", hi_key="detachment_index_max", lo_key="detachment_index_min", units="-",
    description="Detachment access proxy must lie within optional [min,max] window if provided.")
    add("Total radiation fraction", "f_rad_total", hi_key="f_rad_total_max", units="-",
    description="Total radiated power fraction (core+div) must be below cap if set.")
    add("Fuel ion fraction", "fuel_ion_fraction", lo_key="fuel_ion_fraction_min", units="-",
    description="Fuel ion fraction (dilution/ash proxy) must exceed min if set.")
    add("Effective Q", "Q_effective", lo_key="Q_effective_min", units="-",
    description="Q degraded by fuel-ion fraction must exceed min if set.")
    add("Tritium breeding ratio", "TBR", lo_key="TBR_required", units="-",
    description="TBR proxy must meet required threshold.")
    add("Availability", "availability", lo_key="availability_min", units="-",
    description="Plant availability proxy must exceed minimum.")

    return cs


def summarize_constraints(constraints: List[Constraint]) -> Dict[str, float]:
    return {
        "n": float(len(constraints)),
        "n_ok": float(sum(1 for c in constraints if c.ok)),
        "max_violation": float(max((c.residual() for c in constraints), default=0.0)),
    }
