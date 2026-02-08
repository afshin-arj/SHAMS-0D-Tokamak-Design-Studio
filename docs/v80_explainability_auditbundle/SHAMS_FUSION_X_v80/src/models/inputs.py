from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PointInputs:
    # --- Core machine knobs (Phase-1) ---
    R0_m: float
    a_m: float
    kappa: float
    Bt_T: float
    Ip_MA: float
    Ti_keV: float
    fG: float
    Paux_MW: float
    t_shield_m: float = 0.70
    Ti_over_Te: float = 2.0

    # Model switches (PROCESS-like scaffolding; defaults preserve current behavior)
    confinement_model: str = 'ipb98y2'  # 'ipb98y2' (default) or 'iter89p'
    profile_model: str = 'none'  # 'none' (0-D) or 'parabolic' or 'pedestal'
    profile_peaking_ne: float = 1.0
    profile_peaking_T: float = 1.5
    bootstrap_model: str = 'proxy'  # 'proxy' (default) or 'improved'

    # Multiplicative uncertainty / calibration factors (default 1.0)
    confinement_mult: float = 1.0   # scales effective energy confinement time (tauE)
    lambda_q_mult: float = 1.0      # scales SOL width proxy (lambda_q)
    hts_Jc_mult: float = 1.0        # scales HTS critical current density Jc

    # Optional cap on required confinement performance
    H98_allow: float = 9.99e9       # set to e.g. 1.5 to enforce H98 <= 1.5


    # Profile shape knobs (used when profile_model is 'pedestal' or 'eped')
    pedestal_rho_ped: float = 0.9
    pedestal_edge_frac: float = 0.2
    eped_surrogate: bool = False  # if True and profile_model=='pedestal', auto-set pedestal params from proxies

    # Plasma shaping (transparent geometry proxy)
    # Triangularity δ is used only in the radial-build clearance proxy (inboard stack closure).
    # Default 0.0 preserves legacy behavior.
    delta: float = 0.0

    # --- Core plasma/physics knobs (Phase-1 extended) ---
    zeff: float = 1.8
    dilution_fuel: float = 0.85

    # If set to 'from_impurity', Zeff is estimated from (impurity_species, impurity_frac)
    # using a simple two-ion mixture model. Default 'fixed' preserves legacy behavior.
    zeff_mode: str = 'fixed'  # 'fixed' or 'from_impurity'


    # --- Optional physics toggles ---
    include_radiation: bool = True       # if False, skip core radiation model terms
    include_alpha_loss: bool = True      # if False, ignore alpha_loss_frac in alpha heating
    include_hmode_physics: bool = True   # if False, skip P_LH computation and H-mode access screening
    # --- Fuel / reaction mode ---
    fuel_mode: str = "DT"                 # "DT" or "DD"
    include_secondary_DT: bool = True     # in DD mode: include DT burn from DD-produced tritium
    tritium_retention: float = 0.5        # 0..1 fraction of produced T that remains available to burn
    tau_T_loss_s: float = 5.0             # effective tritium particle loss / exhaust timescale [s]
    alpha_loss_frac: float = 0.05

    # --- Alpha deposition / prompt-loss closure (optional; defaults preserve legacy behavior) ---
    # Legacy behavior: if include_alpha_loss, Palpha is reduced by alpha_loss_frac.
    # Opt-in models expose PROCESS-style transparency for fast-particle / prompt-loss effects
    # without changing defaults.
    alpha_loss_model: str = 'fixed'   # 'fixed' (default) or 'rho_star'
    alpha_prompt_loss_k: float = 0.0  # used when alpha_loss_model=='rho_star': alpha_loss_frac_eff = alpha_loss_frac + k*rho_star

    # Alpha ion/electron partition model (bookkeeping only; totals unchanged)
    alpha_partition_model: str = 'fixed'  # 'fixed' (default) or 'Te_ratio'
    alpha_partition_k: float = 0.0        # used when alpha_partition_model=='Te_ratio'

    # --- Helium ash / dilution closure (optional; defaults preserve legacy behavior) ---
    # Treated as an additional multiplicative penalty on DT-equivalent fusion power used for Q.
    # If enabled: Pfus_for_Q *= (1 - f_He_ash)^2.
    ash_dilution_mode: str = 'off'  # 'off' (default) or 'fixed_fraction'
    f_He_ash: float = 0.0

    # --- Power partition (transparent 2-T channel bookkeeping; totals unchanged) ---
    # These fractions only affect reporting of ion/electron channel powers and the optional
    # P_ie equilibration term; the total Pin_MW remains Paux + Palpha (backward compatible).
    f_alpha_to_ion: float = 0.85
    f_aux_to_ion: float = 0.50
    # Toggle to include explicit ion↔electron equilibration power P_ie (diagnostic ledger term).
    include_P_ie: bool = True

    # --- Particle sustainability closure (0-D proxy; optional) ---
    # tau_p is modeled as tau_p_over_tauE * tauE_eff. Required fueling source is then:
    #   S_fuel_required ≈ N_particles / tau_p   (particles/s), with N ≈ <n_e>*V.
    # This is a transparency / feasibility diagnostic; it does not change the operating point unless
    # you explicitly add it as a constraint.
    include_particle_balance: bool = False
    tau_p_over_tauE: float = 3.0
    S_fuel_max_1e22_per_s: float = float('nan')  # if set, enforce required fueling ≤ max (as constraint)

    # --- Optional feasibility caps (off by default when NaN) ---
    # Power/confinement self-consistency residual cap (MW)
    power_balance_tol_MW: float = float('nan')
    # Optional stability caps using screening proxies
    betaN_max: float = float('nan')
    q95_min: float = float('nan')

    # Radiation handling:
    # In Phase-1 you used "extra_rad_factor" * brems. That was a placeholder.
    # For a cleaner point design, we expose explicit radiated fractions:
    f_rad_core: float = 0.20   # fraction of Pin radiated in the core (0..1)
    f_rad_div: float = 0.30    # fraction of P_SOL radiated in divertor (detachment proxy, 0..1)

    # Radiation model selection (PROCESS-like optional path)
    radiation_model: str = 'fractional'  # 'fractional' (default) or 'physics'
    impurity_species: str = 'C'
    impurity_frac: float = 0.0  # number fraction (rough knob) used by line radiation model
    impurity_mix: str = ""  # optional JSON-like string: e.g. '{"C":0.01,"Ne":0.002}' (number fractions)
    include_synchrotron: bool = True

    # Screening proxy knob
    C_bs: float = 0.15

    # H-mode access
    require_Hmode: bool = False
    PLH_margin: float = 0.0   # if >0, require Paux >= (1+PLH_margin)*PLH
    A_eff: float = 2.0

    # Optional SOL metric from Eich λq (risk metric; also used for divertor constraint below)
    use_lambda_q: bool = True
    lambda_q_factor: float = 1.0

    # --- (1) Radial build + magnet constraints ---
    # Radial-build layer thicknesses (inboard) [m]
    t_fw_m: float = 0.02
    t_blanket_m: float = 0.50
    t_vv_m: float = 0.05
    t_gap_m: float = 0.03
    t_tf_wind_m: float = 0.20
    t_tf_struct_m: float = 0.15

    # TF peak field mapping + stress limits
    Bpeak_factor: float = 1.05
    B_peak_allow_T: float = 25.0  # allowable TF peak field at coil [T] (design-dependent)

    # Divertor / SOL power handling proxy limits
    P_SOL_over_R_max_MW_m: float = 25.0  # proxy: P_SOL / R0 limit [MW/m] for power exhaust
    sigma_allow_MPa: float = 800.0  # allowable hoop stress (material/design dependent)

    # --- (2) HTS margin + quench/dump voltage proxy ---
    Tcoil_K: float = 20.0
    hts_margin_min: float = 1.2


    # Enable the explicit HTS critical-surface margin Jc(B,T,ε)/Jop (off by default to preserve legacy behavior)
    include_hts_critical_surface: bool = False

    # Optional HTS strain proxy (dimensionless). 0 means ignore strain.
    hts_strain: float = 0.0
    hts_strain_crit: float = 0.004  # ~0.4% characteristic strain scale

    # Dump / protection knobs (proxy)
    N_tf_turns: int = 1
    tau_dump_s: float = 10.0
    Vmax_kV: float = 20.0

    # Magnetic-energy volume proxy for TF system
    # (effective field volume used for E ~ B^2/(2mu0)*V)
    tf_energy_volume_factor: float = 1.0  # multiplier on an internal geometric volume proxy

    # --- (3) Divertor heat flux surrogate ---
    flux_expansion: float = 5.0
    q_div_max_MW_m2: float = 10.0
    # Optional additional exhaust feasibility caps (NaN disables)
    q_midplane_max_MW_m2: float = float('nan')
    P_SOL_over_R_limit_MW_m: float = float('nan')

    f_Lpar: float = 1.0

    # --- (4) Neutronics lifetime/TBR feasibility ---
    blanket_coverage: float = 0.80
    TBR_min: float = 1.05
    TBR_lambda_m: float = 0.30
    TBR_multiplier: float = 1.10

    # HTS fast-neutron lifetime proxy
    hts_fluence_limit_n_m2: float = 3.0e22   # placeholder; set to your preferred limit
    atten_len_m: float = 0.25               # attenuation length in shield/blanket
    f_geom_to_tf: float = 0.05              # geometry factor from FW to TF (very approximate)
    lifetime_min_yr: float = 3.0            # minimum acceptable lifetime (screen)
    neutron_wall_load_max_MW_m2: float = 2.5   # neutron wall load limit [MW/m^2] (proxy)            # minimum acceptable lifetime (screen)

    # --- (5) Recirculating power closure (net electric) ---
    eta_elec: float = 0.40                  # gross electric efficiency from fusion thermal
    eta_aux_wallplug: float = 0.40          # wall-plug efficiency for auxiliary heating
    eta_cd_wallplug: float = 0.33
    blanket_energy_mult: float = 1.00        # blanket energy multiplication for fusion thermal (>=1)
    P_balance_of_plant_MW: float = 20.0      # fixed balance-of-plant electric load [MW]
    cryo_COP: float = 0.02                   # coefficient of performance (electric/thermal) for cryo at ~20K
    P_cryo_20K_MW: float = 0.0               # thermal load at 20K requiring cryogenic power [MW]
    P_pumps_MW: float = 5.0                  # coolant/pumping parasitic power [MW]
           # wall-plug efficiency for current drive
    eta_cd_MA_per_MW: float = 0.05          # CD efficiency proxy: MA / MW of launched power
    steady_state: bool = True               # if True, compute CD requirement from bootstrap fraction

    # Pulsed operation / flux consumption proxy (used when steady_state=False)
    flux_swing_Wb: float = 60.0      # available transformer flux swing [Wb]
    li_internal: float = 0.8         # internal inductance (proxy)
    V_loop_max_V: float = 2.0        # max loop voltage during flat-top [V]
    pulse_min_s: float = 10.0        # minimum acceptable flat-top duration [s]

    # Cryo loads (proxy)
    R_joint_ohm: float = 1e-9               # joint resistance per joint
    N_joints: int = 0                       # set >0 if demountable joints assumed
    static_cold_W: float = 2.0e4            # static cold load [W] (total TF system proxy)
    W_elec_per_Wcold: float = 300.0         # cryoplant multiplier (20 K-ish)

    # Balance-of-plant pumps & auxiliaries (proxy)
    pump_frac_of_gross: float = 0.03        # fraction of gross electric used for pumps, etc.

    # Optional net-power requirement (screen); if <= -1e8 treated as "off"
    P_net_min_MW: float = -1e9

    # --- (New) TF winding-pack geometry + J limits (PROCESS-like) ---
    tf_wp_width_m: float = 0.25          # winding pack radial width [m]
    tf_wp_height_factor: float = 2.4     # winding pack height ≈ factor * (a*kappa) [–]
    tf_Jop_from_wp_geometry: bool = False  # if True, compute TF Jop from required ampere-turns and winding-pack area
    
    # Optional winding-pack fill factor (0<ff<=1). Used only when tf_Jop_from_wp_geometry is True.
    tf_wp_fill_factor: float = 1.0
    J_eng_max_A_mm2: float = 250.0       # max engineering current density [A/mm^2]

    # --- (New) Simple current drive model ---
    eta_CD_A_W: float = 0.04e-6          # A/W (≈ 40 kA per MW) engineering proxy
    P_CD_MW: float = 0.0                 # current-drive power (subset of Paux) [MW]

    # --- (New) Heat exhaust / SOL proxy knobs ---
    flux_expansion: float = 8.0          # divertor flux expansion proxy
    n_strike_points: int = 2             # 2=single-null, 4=double-null proxy

    # --- (New) Confinement scaling options ---
    # confinement_scaling selects the *reference scaling* used for H-factor reporting.
    # Default remains IPB98(y,2) for continuity. Additional PROCESS-inspired scalings
    # are available as optional comparators (see src/phase1_models.py).
    confinement_scaling: str = "IPB98y2"    # "IPB98y2" | "ITER89P" | "KG" | "NEOALC" | "SHIMOMURA" | "MIRNOV"
    transport_stiffness_c: float = 0.0      # 0 disables; tauE_eff = tauE/(1+c*max(0,Ploss/Ploss_ref-1))
    Ploss_ref_MW: float = 100.0

    # --- (New) Optional analytic profiles (diagnostics + bootstrap hooks) ---
    profile_mode: bool = False              # keep legacy 0-D if False
    profile_alpha_T: float = 1.5            # parabolic exponent for T(r)
    profile_alpha_n: float = 1.0            # parabolic exponent for n(r)
    pedestal_enabled: bool = False
    pedestal_width_a: float = 0.05          # pedestal width as fraction of a
    pedestal_top_T_frac: float = 0.6        # T_ped / T0
    pedestal_top_n_frac: float = 0.8        # n_ped / n0

    # --- (New) Divertor model realism knobs ---
    advanced_divertor_factor: float = 1.0   # <1 reduces q_div via advanced geometry

    # --- (New) Economics / cost proxies ---
    include_economics: bool = False
    electricity_price_USD_per_MWh: float = 60.0
    availability: float = 0.70
    fixed_charge_rate: float = 0.10
    COE_max_USD_per_MWh: float = float('nan')
    k_cost_magnet: float = 0.12
    t_coil_proxy_m: float = 0.5
    k_cost_blanket: float = 0.08
    k_cost_bop: float = 0.35
    k_cost_cryo: float = 6.0
    k_cost_maint: float = 15.0

    # --- (New) Current drive / heating system realism ---
    include_current_drive: bool = False
    f_noninductive_target: float = 1.0
    gamma_cd_A_per_W: float = 0.05
    Pcd_max_MW: float = 200.0
    eta_cd_wallplug: float = 0.35

    # --- (New) q-profile plausibility constraints ---
    q95_min: float = float('nan')
    q95_max: float = float('nan')
    q0_min: float = float('nan')

    # --- (New) Pulsed operation / fatigue proxies ---
    t_burn_s: float = 7200.0  # nominal burn duration for pulsed metrics
    t_dwell_s: float = 600.0
    cycles_max: float = float('nan')


    # --- (New) Thermal-hydraulic proxies ---
    coolant: str = "Helium"  # Helium | Water | FLiBe
    coolant_flow_m3_s: float = 0.05  # representative flow for ΔT proxy

    # --- (New) PF/CS (central solenoid) flux swing proxy ---
    include_pf_cs: bool = True
    cs_Bmax_T: float = 12.0              # Peak CS field (proxy)
    cs_fill_factor: float = 0.6          # Fraction of CS area that contributes to useful flux
    cs_radius_factor: float = 0.30       # CS effective radius ~ cs_radius_factor * R0
    cs_flux_mult: float = 1.0            # Global multiplier for CS available flux (calibration knob)
    pulse_ramp_s: float = 300.0          # Ramp time used in required-flux proxy
    cs_flux_margin_min: float = float("nan")  # optional minimum margin requirement (fraction)

    # --- (New) Plant efficiency model knobs ---
    eta_elec_model: str = "auto"         # "auto" uses coolant/outlet temperature proxy; otherwise uses eta_elec
    T_outlet_K: float = 900.0            # Representative coolant outlet temperature for efficiency proxy

    # --- (New) TF coil thermal margin proxies ---
    coil_cooling_capacity_MW: float = 5.0
    coil_nuclear_heat_coeff_MW_per_MW_m2: float = 0.2  # maps neutron wall load (MW/m^2) -> TF nuclear heating (MW)
    coil_heat_max_MW: float = float("nan")

    # --- (New) Economics calibration ---
    cost_coeffs_name: str = "default"
    cost_coeffs_path: str = ""  # optional JSON file path to override coefficients
    # --- (New) Performance / caching ---
    enable_point_cache: bool = True

    # --- Reactor-grade risk / lifetime / availability ---
    mhd_risk_max: float = float('nan')  # optional hard cap on disruption/MHD risk proxy
    vs_margin_min: float = float('nan')  # optional minimum vertical stability margin proxy
    fw_dpa_max_per_year: float = float('nan')  # optional max dpa/year proxy for first wall
    fw_heatflux_max_MW_m2: float = float('nan')  # optional max first-wall heat flux (proxy)
    div_erosion_max_mm_per_y: float = float('nan')  # optional divertor erosion cap
    availability_min: float = float('nan')  # optional minimum availability fraction
    tritium_inventory_max_g: float = float('nan')  # optional cap on tritium inventory proxy

    # --- PF system proxy knobs ---
    pf_current_max_MA: float = float('nan')  # optional cap on PF coil current proxy
    pf_stress_max: float = float('nan')  # optional cap on PF coil stress proxy (dimensionless)

    # --- Maintenance / replacement assumptions ---
    fw_replace_time_days: float = 30.0
    div_replace_time_days: float = 30.0
    blanket_replace_time_days: float = 90.0
    trips_per_year: float = 5.0  # unscheduled trips per year proxy
    trip_duration_days: float = 2.0


    # --- Reference calibration knobs (transparent, optional) ---
    # Multiplicative factors; defaults keep behavior unchanged.
    calib_confinement: float = 1.0
    calib_divertor: float = 1.0
    calib_bootstrap: float = 1.0

    # Optional 1-sigma uncertainties (used by UQ if specified)
    calib_confinement_sigma: float = 0.0
    calib_divertor_sigma: float = 0.0
    calib_bootstrap_sigma: float = 0.0


    def to_dict(self) -> dict:
        """Return JSON-serializable dict of inputs."""
        from dataclasses import asdict
        return asdict(self)


    # --- Engineering proxies (Phase-2 / PROCESS-inspired) ---
    tf_Jop_MA_per_mm2: float = 0.055  # operating current density (MA/mm^2)
    tf_Jop_limit_MA_per_mm2: float = 0.075
    tf_stress_allow_MPa: float = 900.0
    tf_E_GPa: float = 200.0  # effective structural modulus for strain proxy
    tf_strain_allow: float = float('nan')  # optional cap on TF strain proxy (NaN disables)
    tf_struct_factor: float = 1.0
    cryo_W_per_W: float = 250.0

    # NOTE: do not re-define radial-build thicknesses here; the canonical values
    # live in the "Radial build + magnet constraints" section above.
    gap_m: float = 0.05
    blanket_coverage: float = 0.85
    li6_enrichment: float = 0.30
    TBR_required: float = 1.10

    divertor_tech_mode: str = "baseline"  # conservative|baseline|aggressive
    lambda_q_m: float = 0.005
    f_Psep: float = 0.70
    q_parallel_limit_MW_per_m2: float = 10.0

    blanket_replace_interval_y: float = 4.0
    blanket_replace_duration_mo: float = 4.0
    forced_outage_base: float = 0.10

    enable_envelope: bool = False
    envelope_n_points: int = 3

    # Economics coefficients (override via scenarios/presets)
    cost_k_tf: float = 120.0
    cost_k_pf: float = 60.0
    cost_k_blanket: float = 90.0
    cost_k_cryo: float = 30.0
    cost_k_bop: float = 55.0
    cost_k_buildings: float = 80.0

    @staticmethod
    def from_dict(d: dict) -> "PointInputs":
        """Construct PointInputs from a dict (ignores unknown keys)."""
        fields = {f.name for f in PointInputs.__dataclass_fields__.values()}  # type: ignore
        clean = {k: v for k, v in (d or {}).items() if k in fields}
        return PointInputs(**clean)
