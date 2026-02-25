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
    # --- Policy contracts (feasibility semantics; reviewer-visible) ---
    # These do NOT change physics evaluation; they only change enforcement tier in the constraint ledger.
    # Allowed: 'hard' (blocking) | 'diagnostic' (soft, non-blocking)
    q95_enforcement: str = "hard"
    greenwald_enforcement: str = "hard"

    # --- Technology readiness / maturity contract tier (governance; does not re-solve truth) ---
    # Used to label assumptions and drive optional contract defaults in UI/exploration layers.
    tech_tier: str = "TRL7"  # TRL3 | TRL5 | TRL7 | TRL9

    t_shield_m: float = 0.70
    Ti_over_Te: float = 2.0
    # Model switches (PROCESS-inspired scaffolding; defaults preserve current behavior)
    # confinement_scaling controls the *reference scaling* used for H_scaling reporting
    # (H98 is always reported vs IPB98(y,2)).
    confinement_scaling: str = 'IPB98y2'  # 'IPB98y2' (default), 'ITER89P', 'KAYE_GOLDSTON', 'NEO_ALCATOR', 'MIRNOV', 'SHIMOMURA'
    # Back-compat alias (legacy UI); if set, hot_ion falls back to it when confinement_scaling is missing.
    confinement_model: str = 'ipb98y2'
    profile_model: str = 'none'  # 'none' (0-D) or 'parabolic' or 'pedestal'
    profile_peaking_ne: float = 1.0
    profile_peaking_T: float = 1.5

    # ------------------------------------------------------------------
    # v318.0: 1.5D profile proxy bundle knobs (deterministic, non-iterative)
    # ------------------------------------------------------------------
    # profile_mode enables analytic profile diagnostics that may inform bootstrap
    # sensitivity *only* through explicit bounded multipliers. Defaults preserve
    # legacy 0-D behavior.
    profile_mode: bool = False
    # Analytic core parabolic exponents used for diagnostic profiles (when
    # profile_mode is enabled). These are NOT transport solves.
    profile_alpha_T: float = 1.5
    profile_alpha_n: float = 1.0
    # Current-profile shear shape knob for the algebraic 1.5D profile bundle.
    # 0..1 increases qmin_proxy (stabilizing) when higher.
    profile_shear_shape: float = 0.5
    # --- (v358.0) Profile Family Library Authority (transport proxy, deterministic) ---
    include_profile_family_v358: bool = False
    profile_family_v358: str = "CORE_FLAT"
    profile_family_pedestal_frac: float = 0.0
    profile_family_peaking_p: float = 1.0
    profile_family_peaking_j: float = 1.0
    profile_family_shear_shape: float = 0.5
    profile_family_confinement_mult: float = 1.0
    profile_family_bootstrap_mult: float = 1.0

    # Optional explicit pedestal enable independent of profile_model string.
    pedestal_enabled: bool = False
    pedestal_width_a: float = 0.05
    # Pedestal/profile scaffold variant (used when profile_model=='pedestal')
    # 'tanh'     : smooth edge transition (legacy)
    # 'two_zone' : explicit core+pedestal piecewise (recommended for H-mode scoping)
    profile_pedestal_model: str = 'tanh'
    # Pedestal top fractions relative to core central values (used by 'two_zone' and 'tanh' variants)
    pedestal_top_T_frac: float = 0.6
    pedestal_top_n_frac: float = 0.8
    # Bootstrap closure:
    #   - 'proxy'    : legacy simple proxy
    #   - 'improved' : more responsive proxy (still 0-D)
    #   - 'sauter'   : Sauter-style bootstrap with analytic profile scaffold (requires profile_model != 'none')
    bootstrap_model: str = 'proxy'

    # --- Magnet technology axis (minimal, audit-visible) ---
    # Canonical values:
    #   - 'HTS_REBCO'  (default; legacy behavior)
    #   - 'LTS_NB3SN'
    #   - 'LTS_NBTI'
    #   - 'COPPER'
    # This selects the TF coil critical-surface proxy (or disables it for copper)
    # and drives intent policy gating (reactor blocks copper TF by default).
    magnet_technology: str = 'HTS_REBCO'

    # TF wallplug efficiency for resistive-coil power (COPPER tech only)
    # Used as: P_tf_el = P_tf_ohmic / eta_tf_wallplug
    eta_tf_wallplug: float = 0.95

    # Multiplicative uncertainty / calibration factors (default 1.0)
    confinement_mult: float = 1.0   # scales effective energy confinement time (tauE)
    lambda_q_mult: float = 1.0      # scales SOL width proxy (lambda_q)
    hts_Jc_mult: float = 1.0        # scales HTS critical current density Jc

    # Optional cap on required confinement performance
    H98_allow: float = 9.99e9       # set to e.g. 1.5 to enforce H98 <= 1.5

    # ------------------------------------------------------------------
    # v371.0: Transport Contract Library Authority (governance only)
    # ------------------------------------------------------------------
    include_transport_contracts_v371: bool = False
    transport_contract_profile: str = "default"
    # Optional caps on required confinement relative to IPB98(y,2).
    # NaN disables (default). If set, these become explicit feasibility constraints.
    H_required_max_optimistic: float = float("nan")
    H_required_max_robust: float = float("nan")

    # ------------------------------------------------------------------
    # v396.0: Transport Envelope 2.0 Authority (governance only)
    # ------------------------------------------------------------------
    # Computes τE envelope over multiple scalings (min/max), spread ratio, and a
    # deterministic credibility tier. Does NOT modify truth.
    include_transport_envelope_v396: bool = True

    # Optional feasibility cap on transport scaling spread ratio:
    #   spread = tauE_max / tauE_min
    # NaN disables (default). If set (>0), becomes an explicit feasibility constraint.
    transport_spread_max_v396: float = float("nan")

    # Optional user scaling vector (generic power-law). Disabled by default.
    include_tauE_user_scaling_v396: bool = False
    tauE_user_C_v396: float = float("nan")
    tauE_user_exp_Ip_v396: float = float("nan")
    tauE_user_exp_Bt_v396: float = float("nan")
    tauE_user_exp_ne_v396: float = float("nan")
    tauE_user_exp_Ploss_v396: float = float("nan")
    tauE_user_exp_R_v396: float = float("nan")
    tauE_user_exp_eps_v396: float = float("nan")
    tauE_user_exp_kappa_v396: float = float("nan")
    tauE_user_exp_M_v396: float = float("nan")

    # ------------------------------------------------------------------
    # v372.0: Neutronics–Materials Coupling Authority 2.0 (governance only)
    # ------------------------------------------------------------------
    include_neutronics_materials_coupling_v372: bool = False
    # Governance labels (explicit, reviewer-visible): RAFM | W | SiC | ODS
    nm_material_class_v372: str = "RAFM"
    # Spectrum hardness class: soft | nominal | hard
    nm_spectrum_class_v372: str = "nominal"
    # Optional operating temperature used for window checks (°C). NaN disables window check.
    nm_T_oper_C_v372: float = float("nan")
    # Optional explicit caps / margins (NaN disables). When set, become explicit constraints.
    dpa_rate_eff_max_v372: float = float("nan")
    damage_margin_min_v372: float = float("nan")


    # Profile shape knobs (used when profile_model is 'pedestal' or 'eped')
    pedestal_rho_ped: float = 0.9
    pedestal_edge_frac: float = 0.2
    pedestal_edge_T_frac: float = 0.2
    pedestal_edge_n_frac: float = 0.2
    eped_surrogate: bool = False  # if True and profile_model=='pedestal', auto-set pedestal params from proxies

    # Plasma shaping (transparent geometry proxy)
    # Triangularity δ is used only in the radial-build clearance proxy (inboard stack closure).
    # Default 0.0 preserves legacy behavior.
    delta: float = 0.0

    # Optional shaping bounds (screening constraints when set; NaN disables)
    kappa_max: float = float('nan')
    delta_min: float = float('nan')
    delta_max: float = float('nan')

    # --- Core plasma/physics knobs (Phase-1 extended) ---
    zeff: float = 1.8
    dilution_fuel: float = 0.85

    # If set to 'from_impurity', Zeff is estimated from (impurity_species, impurity_frac)
    # using a simple two-ion mixture model. Default 'fixed' preserves legacy behavior.
    zeff_mode: str = 'fixed'  # 'fixed' or 'from_impurity'


    # --- Optional physics toggles ---
    # Radiation is available but defaults OFF for conservative scoping.
    # Users may enable it explicitly (recommended: diagnostic-only for research intent).
    include_radiation: bool = False      # if False, skip core radiation model terms
    include_alpha_loss: bool = True      # if False, ignore alpha_loss_frac in alpha heating
    include_hmode_physics: bool = True   # if False, skip P_LH computation and H-mode access screening

    # --- Regime coupling (diagnostic; defaults preserve legacy behavior) ---
    # If True, compute a confinement-regime label (L/H) from the P_LH proxy and report
    # a regime-referenced H-factor (H_regime) using ITER89P in L-mode and IPB98(y,2) in H-mode.
    couple_regime_to_confinement: bool = False
    # Access criterion: require P_heat >= f_LH_access * P_LH (1.0 means Martin08 threshold).
    f_LH_access: float = 1.0

    # --- Burn / ignition screening (optional; NaN disables) ---
    ignition_margin_min: float = float('nan')  # enforce M_ign >= min if set

    # --- Neutronics screening (optional; NaN disables) ---
    neutron_wall_load_max_MW_m2: float = float('nan')

    # --- Edge / divertor radiative control (optional; defaults preserve legacy behavior) ---
    # If enabled, compute a required SOL radiative fraction to hit a requested q_div target.
    include_sol_radiation_control: bool = False
    q_div_target_MW_m2: float = float('nan')  # requested target heat flux (tech goal), NaN disables
    # This does not change the operating point; it is a transparency / reviewer feature.

    # --- Fuel / reaction mode ---
    fuel_mode: str = "DT"                 # "DT" or "DD"
    include_secondary_DT: bool = True     # in DD mode: include DT burn from DD-produced tritium
    tritium_retention: float = 0.5        # 0..1 fraction of produced T that remains available to burn
    tau_T_loss_s: float = 5.0             # effective tritium particle loss / exhaust timescale [s]
    alpha_loss_frac: float = 0.05

    # --- Burn / ignition screening (optional; NaN disables) ---
    # Defines a simple ignition-like margin M_ign = Palpha / Ploss (Ploss = P_SOL = Pin - Prad_core).
    ignition_margin_min: float = float('nan')

    # --- Neutronics-lite screening (optional; NaN disables) ---
    neutron_wall_load_max_MW_m2: float = float('nan')

    # --- Radiative divertor coupling (optional; defaults preserve legacy behavior) ---
    # If enabled, compute the required SOL radiated fraction to meet a target divertor heat flux.
    # This only re-partitions P_SOL used by the divertor proxy; it does not change core power balance.
    include_sol_radiation_control: bool = False
    q_div_target_MW_m2: float = float('nan')

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
    betaN_troyon_max: float = float('nan')  # explicit Troyon-style betaN cap
    q95_min: float = float('nan')

    # --- (v264.0) Heating/CD closure (proxy; optional) ---
    cd_enable: bool = False
    cd_method: str = "NBI"  # NBI|EC|LH (proxy)
    cd_fraction_of_Paux: float = 0.5  # portion of Paux allocated to current drive
    f_NI_min: float = float("nan")  # require non-inductive fraction >= min if set

    # --- (v264.0) Disruption / radiative-limit risk screens (optional caps; NaN disables) ---
    disruption_risk_max: float = float("nan")
    f_rad_core_max: float = float("nan")

    # --- (v285.0) Exhaust authority (optional caps; NaN disables) ---
    # Detachment access index window (proxy): enforce I_detach >= min and/or <= max when set.
    detachment_index_min: float = float("nan")
    detachment_index_max: float = float("nan")
    f_rad_total_max: float = float("nan")
    fuel_ion_fraction_min: float = float("nan")
    Q_effective_min: float = float("nan")

    # --- (v285.0) Magnet quench / protection authority (optional caps; NaN disables) ---
    magnet_quench_risk_max: float = float("nan")
    quench_energy_density_max_MJ_m3: float = float("nan")


    # Radiation handling:
    # In Phase-1 you used "extra_rad_factor" * brems. That was a placeholder.
    # For a cleaner point design, we expose explicit radiated fractions:
    f_rad_core: float = 0.20   # fraction of Pin radiated in the core (0..1)
    f_rad_div: float = 0.30    # fraction of P_SOL radiated in divertor (detachment proxy, 0..1)

    # Radiation model selection (PROCESS-like optional path)
    radiation_model: str = 'fractional'  # 'fractional' (default) or 'impurity_mix'/'lz_table'
    radiation_db: str = 'proxy_v1'       # Lz(Te) table database id when using impurity/line models
    impurity_species: str = 'C'
    impurity_frac: float = 0.0  # number fraction (rough knob) used by line radiation model
    impurity_mix: str = ""  # optional JSON-like string: e.g. '{"C":0.01,"Ne":0.002}' (number fractions)
    include_synchrotron: bool = True

    # --- (v320.0) Impurity radiation & detachment authority contract (algebraic) ---
    # These do not change the core operating point unless you add explicit constraints.
    impurity_contract_species: str = 'Ne'     # C|N|Ne|Ar|W
    impurity_contract_f_z: float = 3e-4       # seeding fraction nZ/ne
    impurity_partition_core: float = 0.50
    impurity_partition_edge: float = 0.20
    impurity_partition_sol: float = 0.20
    impurity_partition_div: float = 0.10
    # Detachment inversion knobs (used when include_sol_radiation_control is enabled)
    T_sol_keV: float = 0.08
    f_V_sol_div: float = 0.12
    # Optional feasibility cap: require implied f_z to be <= this value (NaN disables)
    detachment_fz_max: float = float('nan')

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

    # --- (1b) Materials tags for neutronics/materials authority (proxy) ---
    # These tags parameterize the radial stack attenuation and nuclear heating shares.
    # They do NOT call neutronics transport solvers.
    vv_material: str = "VV_STEEL"
    shield_material: str = "WC"
    blanket_material: str = "LiPb"
    fw_material: str = "EUROFER"
    tf_material: str = "REBCO"

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
    # Port fraction (coverage penalty). 0 means full 2π poloidal coverage.
    port_fraction: float = 0.08
    # Li-6 enrichment fraction (0..1) used by the TBR proxy.
    li6_enrichment: float = 0.30
    # Blanket archetype tags for the TBR proxy (separate from blanket_material used in attenuation).
    blanket_type: str = "LiPb"  # e.g. LiPb | FLiBe
    multiplier_material: str = "None"  # e.g. None | Be | Pb
    # Neutronics archetype for heating partitioning (standard | heavy_shield | compact)
    neutronics_archetype: str = "standard"
    # (v321.0) Domain enforcement tightening (off by default)
    # If enabled, proxy validity-domain violations become explicit constraints (no solver/relaxation).
    neutronics_domain_enforce: bool = False
    materials_domain_enforce: bool = False
    TBR_min: float = 1.05
    TBR_lambda_m: float = 0.30
    TBR_multiplier: float = 1.10

    # HTS fast-neutron lifetime proxy
    hts_fluence_limit_n_m2: float = 3.0e22   # placeholder; set to your preferred limit
    atten_len_m: float = 0.25               # attenuation length in shield/blanket
    f_geom_to_tf: float = 0.05              # geometry factor from FW to TF (very approximate)
    lifetime_min_yr: float = 3.0            # minimum acceptable lifetime (screen)
    neutron_wall_load_max_MW_m2: float = 2.5   # neutron wall load limit [MW/m^2] (proxy)            # minimum acceptable lifetime (screen)

    # Optional (materials) replacement / lifetime caps (NaN disables enforcement)
    fw_lifetime_min_yr: float = float('nan')
    blanket_lifetime_min_yr: float = float('nan')

    # ------------------------------------------------------------------
    # (v367.0) Materials lifetime closure policy (deterministic)
    # ------------------------------------------------------------------
    plant_design_lifetime_yr: float = 30.0
    materials_life_cover_plant_enforce: bool = False
    fw_replace_interval_min_yr: float = float('nan')
    blanket_replace_interval_min_yr: float = float('nan')
    fw_capex_fraction_of_blanket: float = 0.20
    blanket_capex_fraction_of_blanket: float = 1.00
    # Optional helium limit overrides (NaN -> use library default; only used for constraints)
    fw_He_total_limit_appm: float = float('nan')
    blanket_He_total_limit_appm: float = float('nan')
    # Optional nuclear heating caps (NaN disables)
    P_nuc_total_max_MW: float = float('nan')
    P_nuc_tf_max_MW: float = float('nan')
    P_nuc_pf_max_MW: float = float('nan')
    P_nuc_cryo_max_kW: float = float('nan')

    # --- (4b) Materials admissibility: temperature windows & stress (proxy) ---
    # Operating temperatures used only for window checks (no thermal solver).
    T_fw_oper_C: float = float('nan')
    T_blanket_oper_C: float = float('nan')
    # If set to 1, enforce temperature window as HARD constraint; otherwise diagnostic.
    fw_T_enforce: bool = False
    blanket_T_enforce: bool = False
    # Operating stresses for screening; NaN disables constraints.
    sigma_fw_oper_MPa: float = float('nan')
    sigma_blanket_oper_MPa: float = float('nan')
    # Replacement horizon used for end-of-life totals (years, bookkeeping only)
    fw_replacement_horizon_yr: float = 1.0

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

    # --- (5b) Plant power ledger caps (optional; NaN disables) ---
    # These act on post-processed bookkeeping keys produced by src.plant.power_ledger.
    f_recirc_max: float = float('nan')        # max recirculating fraction (Precirc/Pe_gross)
    P_pf_avg_max_MW: float = float('nan')     # max average PF electric draw proxy [MW]
    P_aux_max_MW: float = float('nan')        # cap on auxiliary+CD wallplug draw proxy [MW]
    P_supply_peak_max_MW: float = float('nan')  # optional cap on peak electrical power supply draw (max of PF peak, aux/CD wallplug, control power) [MW]
    P_cryo_max_MW: float = float('nan')       # cap on cryo electric draw proxy [MW]

    # --- (5c) Pulse scenario contract (quasi-static) ---
    # 'as_input' keeps the user's explicit pulsed parameters.
    # Other values map to templates in src.control.pulse_scenarios.
    pulse_scenario: str = 'as_input'

    # --- (8) Fuel-cycle / tritium ledger (optional; NaN disables) ---
    T_reserve_days: float = 3.0
    T_processing_margin: float = 1.25
    TBR_required_override: float = float('nan')
    T_inventory_min_kg: float = float('nan')
    T_processing_capacity_min_g_per_day: float = float('nan')

    # --- (v350.0) Tritium & Fuel Cycle Tight Closure (optional; NaN disables) ---
    include_tritium_tight_closure: bool = False
    T_processing_delay_days: float = 1.0
    T_in_vessel_max_kg: float = float('nan')
    T_total_inventory_max_kg: float = float('nan')
    T_startup_inventory_kg: float = float('nan')
    T_loss_fraction: float = float('nan')
    TBR_self_sufficiency_margin: float = float('nan')

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
    f_wet_divertor: float = 1.0          # wetted-area utilization (0<fw<=1), accounts for partial wetting/strike sweep

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
    include_cd_library_v357: bool = False
    include_cd_library_v395: bool = False

    # Target NI closure (used when include_current_drive=True)
    f_noninductive_target: float = 1.0

    # CD efficiency proxy (legacy + scaling models)
    gamma_cd_A_per_W: float = 0.05
    eta_cd_wallplug: float = 0.35
    Pcd_max_MW: float = 200.0

    # CD model selection
    cd_model: str = "fixed_gamma"   # fixed_gamma | actuator_scaling | channel_library_v357 | channel_library_v395
    cd_actuator: str = "ECCD"      # ECCD | LHCD | NBI | ICRF

    # v395.0 multi-channel mix (fractions of launched P_cd; normalized if sum>0)
    cd_mix_enable: bool = False
    cd_mix_frac_eccd: float = 1.0
    cd_mix_frac_lhcd: float = 0.0
    cd_mix_frac_nbi: float = 0.0
    cd_mix_frac_icrf: float = 0.0

    # Optional wall-plug efficiencies per channel (NaN -> use eta_cd_wallplug)
    eta_cd_wallplug_eccd: float = float('nan')
    eta_cd_wallplug_lhcd: float = float('nan')
    eta_cd_wallplug_nbi: float = float('nan')
    eta_cd_wallplug_icrf: float = float('nan')

    # v357.0 channel knobs (used only when include_cd_library_v357=True)
    # LHCD
    lhcd_n_parallel: float = 1.8
    lhcd_n_parallel_min: float = float('nan')
    lhcd_n_parallel_max: float = float('nan')

    # ECCD
    eccd_launcher_area_m2: float = 2.0
    eccd_launch_factor: float = 1.0
    eccd_launcher_power_density_max_MW_m2: float = float('nan')

    # NBI
    nbi_beam_energy_keV: float = 500.0
    nbi_shinethrough_frac_max: float = float('nan')

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
    cs_V_loop_max_V: float = float("nan")     # optional cap on CS loop voltage during ramp (V)

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

    # --- (New) Build closure enforcement (opt-in) ---
    enforce_radial_build: bool = False  # if true, inboard_margin_m >= 0 becomes a hard constraint

    # --- (New) Availability-aware annual energy requirement (optional) ---
    annual_net_MWh_min: float = float('nan')  # optional minimum annual net generation (MWh/y)

    # --- PF system proxy knobs ---
    pf_current_max_MA: float = float('nan')  # optional cap on PF coil current proxy
    pf_stress_max: float = float('nan')  # optional cap on PF coil stress proxy (dimensionless)

    # --- (v226.0) Envelope-based control contracts (deterministic) ---
    # Disabled by default; enabling computes *requirements* and checks optional caps.
    include_control_contracts: bool = False

    # Vertical stability control: map vs_margin -> growth rate with a nominal timescale
    vs_tau_nominal_s: float = 0.30
    vs_bw_factor: float = 3.0
    vs_control_margin_factor: float = 1.30
    vs_control_horizon_s: float = 1.0  # budgeting horizon for VS control energy proxy
    vs_bandwidth_max_Hz: float = float('nan')
    vs_control_power_max_MW: float = float('nan')

    # PF envelope: effective L and R can be provided; if L is NaN it's estimated from CS flux requirement.
    pf_L_eff_H: float = float('nan')
    pf_R_eff_Ohm: float = 1.0e-4
    pf_ramp_s: float = float('nan')  # if NaN, uses pulse_ramp_s
    pf_flat_s: float = float('nan')  # if NaN, uses t_flat_s (output) or t_burn_s

    # Optional PF envelope caps (NaN disables)
    pf_I_peak_max_MA: float = float('nan')
    pf_V_peak_max_V: float = float('nan')
    pf_P_peak_max_MW: float = float('nan')
    pf_dIdt_max_MA_s: float = float('nan')
    pf_E_pulse_max_MJ: float = float('nan')  # optional cap on PF pulse energy proxy (MJ)
    pf_E_pulse_max_MJ: float = float('nan')

    # --- (v229.0) RWM screening (optional) ---
    include_rwm_screening: bool = False
    # Wall time constant; if NaN, a conservative inference is used (authority downgraded)
    rwm_tau_w_s: float = float('nan')
    rwm_wall_thickness_m: float = 0.03
    rwm_wall_resistivity_class: float = 1.0  # dimensionless proxy (>1 => more resistive)

    # Parametric beta limits (PROCESS-class): betaN_NW = C_NW*F(...), betaN_IW = C_IW*F(...)
    rwm_C_betaN_no_wall: float = 2.8
    rwm_C_betaN_ideal_wall: float = 4.0
    rwm_a_kappa: float = 0.25
    rwm_a_delta: float = 0.15
    rwm_q95_ref: float = 3.0
    rwm_a_q95: float = 0.30
    rwm_li_ref: float = 0.8
    rwm_a_li: float = 0.10
    rwm_chi_eps: float = 0.05

    # Rotation stabilization proxy (0..1)
    rwm_rotation_stabilization: float = 0.0
    rwm_k_rot: float = 1.5

    # Control conversion coefficient: P_req ~ C_P * W_pf * gamma
    rwm_C_P: float = 0.15

    # Optional caps: if NaN, defaults to VS caps for bandwidth/power
    rwm_bandwidth_max_Hz: float = float('nan')
    rwm_control_power_max_MW: float = float('nan')

    # SOL radiative control contract cap (NaN disables). Requires include_sol_radiation_control=True.
    f_rad_SOL_max: float = float('nan')

    # --- (v348.0) Edge–Core Coupled Exhaust Authority (optional) ---
    include_edge_core_coupled_exhaust: bool = False
    edge_core_coupling_chi_core: float = 0.25  # 0..1
    f_rad_core_edge_core_max: float = float('nan')  # optional cap on coupled core radiative fraction proxy

    # --- (v349.0) Bootstrap & Pressure Self-Consistency Authority (optional) ---
    include_bootstrap_pressure_selfconsistency: bool = False
    f_bootstrap_consistency_abs_max: float = float('nan')  # optional cap on |f_bs_reported - f_bs_expected|

    # --- Maintenance / replacement assumptions ---
    fw_replace_time_days: float = 30.0
    div_replace_time_days: float = 30.0
    blanket_replace_time_days: float = 90.0
    trips_per_year: float = 5.0  # unscheduled trips per year proxy
    trip_duration_days: float = 2.0


    # --- (v359.0) Availability & replacement ledger authority (optional) ---
    include_availability_replacement_v359: bool = False
    planned_outage_base: float = 0.05
    heating_cd_replace_interval_y: float = 8.0
    heating_cd_replace_duration_days: float = 30.0
    tritium_plant_replace_interval_y: float = 10.0
    tritium_plant_replace_duration_days: float = 30.0
    availability_v359_min: float = float('nan')
    LCOE_max_USD_per_MWh: float = float('nan')


    # --- (v368.0) Maintenance Scheduling Authority 1.0 (optional) ---
    # Deterministic outage calendar proxy (no time simulation; no optimization).
    include_maintenance_scheduling_v368: bool = False
    maintenance_planning_horizon_yr: float = float('nan')
    maintenance_bundle_policy: str = "independent"  # independent|bundle_in_vessel|bundle_all
    maintenance_bundle_overhead_days: float = 7.0
    forced_outage_mode_v368: str = "max"  # max|baseline|trips
    outage_fraction_v368_max: float = float('nan')  # optional cap on total outage fraction
    availability_v368_min: float = float('nan')     # optional min availability under v368


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
    divertor_model: str = "wetted_area_proxy"  # "wetted_area_proxy" (legacy) or "two_point"
    f_expansion: float = 10.0  # magnetic flux expansion factor (two-point model)
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
    # v356.0: additional PROCESS-style component proxies
    # - Heating/CD cost is proportional to launched CD/aux power (MW)
    # - Tritium plant cost is proportional to tritium burn throughput (kg/day)
    cost_k_heating_cd: float = 25.0
    cost_k_tritium_plant: float = 40.0
    # Optional feasibility cap (NaN disables)
    CAPEX_max_proxy_MUSD: float = float('nan')
    # --- (v360.0) Plant Economics Authority 1.0 (optional; OFF by default) ---
    include_economics_v360: bool = False
    opex_fixed_MUSD_per_y: float = 0.0
    tritium_processing_cost_USD_per_g: float = 0.05
    cryo_wallplug_multiplier: float = 250.0
    OPEX_max_MUSD_per_y: float = float('nan')

    # --- (v383.0) Plant Economics & Cost Authority 2.0 (optional; OFF by default) ---
    include_economics_v383: bool = False
    CAPEX_structured_max_MUSD: float = float('nan')
    OPEX_structured_max_MUSD_per_y: float = float('nan')
    LCOE_lite_max_USD_per_MWh: float = float('nan')

    # --- (v388.0.0) Cost Authority 3.0 — Industrial Depth (optional; OFF by default) ---
    # Deterministic, algebraic subsystem scaling envelopes. Governance-only.
    include_cost_authority_v388: bool = False
    CAPEX_industrial_max_MUSD: float = float('nan')
    OPEX_industrial_max_MUSD_per_y: float = float('nan')
    LCOE_lite_v388_max_USD_per_MWh: float = float('nan')

    # --- (v389.0.0) Structural Stress Authority (optional; OFF by default) ---
    # Deterministic, algebraic thin-shell proxies for TF / CS / vacuum vessel.
    include_structural_stress_v389: bool = False

    # TF structural margin minimum (dimensionless). Applied when authority enabled.
    tf_struct_margin_min_v389: float = 1.0

    # CS/PF structural proxy inputs
    t_cs_struct_m_v389: float = 0.20
    sigma_cs_allow_MPa_v389: float = 300.0
    cs_struct_margin_min_v389: float = 1.0

    # Vacuum vessel external pressure proxy inputs
    vv_ext_pressure_MPa_v389: float = 0.101  # ~1 atm
    sigma_vv_allow_MPa_v389: float = 200.0
    vv_struct_margin_min_v389: float = 1.0

    # --- (v390.0.0) Neutronics & Activation Authority 3.0 (optional; OFF by default) ---
    # Deterministic shielding envelope + activation + FW damage proxies (governance-only).
    include_neutronics_activation_v390: bool = False
    blanket_class_v390: str = "STANDARD"
    # Shield requirement envelope exponents
    shield_req_Pfus_exp_v390: float = 0.25
    shield_req_qwall_exp_v390: float = 0.50
    # FW damage proxy parameters
    fw_dpa_per_fpy_per_MWm2_v390: float = 15.0
    fw_dpa_limit_v390: float = 20.0
    # Optional constraints (NaN disables)
    shield_margin_min_cm_v390: float = float("nan")
    fw_life_min_fpy_v390: float = float("nan")
    dpa_per_fpy_max_v390: float = float("nan")
    activation_index_max_v390: float = float("nan")

    # --- (v392.0.0) Neutronics Shield Attenuation Authority (optional; OFF by default) ---
    # Deterministic ex-vessel fluence + bioshield dose proxy using exponential attenuation lengths.
    include_neutronics_shield_attenuation_v392: bool = False
    # Pathlength gaps from FW stack to boundaries (m)
    gap_to_tf_case_m_v392: float = 0.20
    gap_to_cryostat_m_v392: float = 0.80
    gap_to_bioshield_m_v392: float = 1.20
    # Biological shield thickness (m)
    t_bioshield_m_v392: float = 1.20
    # Attenuation length overrides (m). If stack lambda is NaN/<=0, falls back to atten_len_m.
    atten_len_stack_m_v392: float = float("nan")
    atten_len_bioshield_m_v392: float = 0.35
    # Optional inverse-square geometric dilution toggle (screening)
    use_inv_square_geom_v392: bool = True
    # Dose conversion proxy: uSv/h per (n/m^2/s)
    dose_uSv_h_per_flux_n_m2_s_v392: float = 1.0e-20
    # Optional caps (NaN disables)
    tf_case_fluence_max_n_m2_per_fpy_v392: float = float("nan")
    cryostat_fluence_max_n_m2_per_fpy_v392: float = float("nan")
    bioshield_dose_rate_max_uSv_h_v392: float = float("nan")

    # --- (v391.0.0) Availability 2.0 — Reliability Envelope Authority (optional; OFF by default) ---
    # Deterministic algebraic availability envelope driven by explicit MTBF/MTTR + planned/maintenance downtime.
    include_availability_reliability_v391: bool = False
    planned_outage_days_per_y_v391: float = 30.0

    # MTBF/MTTR (hours) by subsystem class (deterministic proxies; user-tunable)
    mtbf_tf_h_v391: float = 80000.0
    mttr_tf_h_v391: float = 240.0
    mtbf_pfcs_h_v391: float = 60000.0
    mttr_pfcs_h_v391: float = 168.0
    mtbf_divertor_h_v391: float = 20000.0
    mttr_divertor_h_v391: float = 336.0
    mtbf_blanket_h_v391: float = 25000.0
    mttr_blanket_h_v391: float = 504.0
    mtbf_cryo_h_v391: float = 40000.0
    mttr_cryo_h_v391: float = 120.0
    mtbf_hcd_h_v391: float = 30000.0
    mttr_hcd_h_v391: float = 168.0
    mtbf_bop_h_v391: float = 50000.0
    mttr_bop_h_v391: float = 72.0

    # Optional caps/minima (NaN disables)
    availability_min_v391: float = float("nan")
    planned_outage_max_frac_v391: float = float("nan")
    unplanned_downtime_max_frac_v391: float = float("nan")
    maint_downtime_max_frac_v391: float = float("nan")


    # --- (v384.0.0) Materials & Lifetime Tightening (optional; OFF by default) ---
    include_materials_lifetime_v384: bool = False
    # Divertor lifetime proxy knobs
    divertor_life_ref_yr: float = 3.0
    divertor_q_ref_MW_m2: float = 10.0
    divertor_q_exp: float = 2.0
    divertor_capex_fraction_of_total: float = 0.05
    # Magnet lifetime proxy knobs
    magnet_life_ref_yr: float = 30.0
    magnet_margin_ref: float = 0.10
    magnet_margin_exp: float = 1.5
    # Replacement downtime coupling
    base_capacity_factor: float = 0.75
    capacity_factor_max: float = 0.95
    fw_downtime_days: float = 30.0
    blanket_downtime_days: float = 60.0
    divertor_downtime_days: float = 20.0
    magnet_downtime_days: float = 120.0
    fw_capex_fraction_of_blanket: float = 0.20
    blanket_capex_fraction_of_blanket: float = 1.00
    # Feasibility caps (NaN disables)
    fw_lifetime_min_yr_v384: float = float('nan')
    blanket_lifetime_min_yr_v384: float = float('nan')
    divertor_lifetime_min_yr_v384: float = float('nan')
    magnet_lifetime_min_yr_v384: float = float('nan')
    replacement_cost_max_MUSD_per_y_v384: float = float('nan')
    capacity_factor_min_v384: float = float('nan')


    @staticmethod
    def from_dict(d: dict) -> "PointInputs":
        """Construct PointInputs from a dict (ignores unknown keys)."""
        fields = {f.name for f in PointInputs.__dataclass_fields__.values()}  # type: ignore
        clean = {k: v for k, v in (d or {}).items() if k in fields}
        return PointInputs(**clean)
