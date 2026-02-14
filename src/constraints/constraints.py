from __future__ import annotations
from dataclasses import dataclass

from .metadata import default_best_knobs
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class Constraint:
    name: str
    value: float
    limit: float
    sense: str  # '<=' or '>='
    passed: bool
    severity: str = "hard"
    units: str = ""
    note: str = ""  # backward compatible freeform note
    group: str = "general"
    # Mechanism cartography (v228+): coarse mechanism class for overlays
    mechanism_group: str = "GENERAL"
    # Authority linkage (v228+): maps to provenance.authority.AUTHORITY_CONTRACTS
    subsystem: str = ""
    authority_tier: str = "unknown"  # proxy | semi-authoritative | authoritative | unknown
    validity_domain: str = ""
    meaning: str = ""  # why this constraint exists (decision guidance)
    dominant_inputs: List[tuple] = None  # optional [(input, sensitivity)]
    best_knobs: List[str] = None  # optional recommended knob directions
    validity: dict = None  # optional validity tags/ranges
    maturity: dict = None  # optional maturity tags (TRL/envelope)
    provenance: dict = None  # optional provenance fingerprints

    @property
    def margin(self) -> float:
        """Signed fractional margin relative to limit.

        For <= constraints: margin = (limit - value)/limit.
        For >= constraints: margin = (value - limit)/limit.
        Returns NaN if limit is zero or non-finite.
        """
        try:
            if self.limit == 0:
                return float("nan")
            if self.sense.strip() == "<=":
                return (self.limit - self.value) / self.limit
            return (self.value - self.limit) / self.limit
        except Exception:
            return float("nan")



    @property
    def failed(self) -> bool:
        """Backward-compatible flag used by older UI code."""
        return not bool(self.passed)

    def as_dict(self) -> Dict[str, Any]:
        """Serialize to a dict for UI tables and evidence packs."""
        return {
            "name": self.name,
            "value": self.value,
            "limit": self.limit,
            "sense": self.sense,
            "passed": self.passed,
            "failed": self.failed,
            "severity": self.severity,
            "units": self.units,
            "note": self.note,
            "group": self.group,
            "mechanism_group": self.mechanism_group,
            "subsystem": self.subsystem,
            "authority_tier": self.authority_tier,
            "validity_domain": self.validity_domain,
            "meaning": self.meaning,
            "dominant_inputs": self.dominant_inputs,
            "best_knobs": self.best_knobs,
            "validity": self.validity,
            "maturity": self.maturity,
            "provenance": self.provenance,
            "margin": self.margin,
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like getter for backward compatibility with UI code."""
        if key == "failed":
            return self.failed
        if key == "margin":
            return self.margin
        if hasattr(self, key):
            return getattr(self, key)
        for bucket in ("validity", "maturity", "provenance"):
            b = getattr(self, bucket, None)
            if isinstance(b, dict) and key in b:
                return b.get(key, default)
        return default

def evaluate_constraints(
    outputs: Dict[str, float],
    policy: Optional[Dict[str, Any]] = None,
    *,
    point_inputs: Optional[Dict[str, Any]] = None,
    **_unused_kwargs: Any,
) -> List[Constraint]:
    """Evaluate a PROCESS-like constraint set from point outputs.

    Parameters
    ----------
    outputs:
        Frozen truth outputs for a single point.
    policy:
        Optional feasibility semantics overrides (e.g. downgrade certain constraints to diagnostic).
    point_inputs:
        Optional original point inputs. Accepted for UI/backward-compatibility wiring. Truth is
        *not* modified by these inputs; they may be used only for metadata/provenance enrichment
        in the future.
    **_unused_kwargs:
        Forward/backward compatibility shim. Ignored.

    This function is intentionally conservative and proxy-based. It only evaluates
    constraints when the required keys exist in ``outputs``. Limits are taken
    from explicit *_max/*_min/*_allow keys when available, otherwise from
    reasonable default caps suitable for early-stage screening.
    """
    cs: List[Constraint] = []

    # Policy contract is a *feasibility semantics* layer: it does not alter physics outputs,
    # but may downgrade selected constraints from HARD->SOFT (diagnostic) explicitly.
    if policy is None:
        try:
            pol = outputs.get("_policy_contract") if isinstance(outputs, dict) else None
            policy = pol if isinstance(pol, dict) else None
        except Exception:
            policy = None
    policy = policy or {}

    maturity_contract = None
    try:
        mc = outputs.get('_maturity_contract') if isinstance(outputs, dict) else None
        maturity_contract = mc if isinstance(mc, dict) else None
    except Exception:
        maturity_contract = None

    def _tier(name: str) -> str:
        # only supported tiers: hard | diagnostic
        try:
            if name == "q95":
                return str(policy.get("q95_enforcement", "hard")).strip().lower()
            if name == "q95_min":
                return str(policy.get("q95_enforcement", "hard")).strip().lower()
            if name == "fG":
                return str(policy.get("greenwald_enforcement", "hard")).strip().lower()
        except Exception:
            pass
        return "hard"

    def _severity_for(name: str, default: str) -> tuple[str, dict | None]:
        t = _tier(name)
        if t == "diagnostic":
            return "soft", {"policy_override": {"tier": "diagnostic", "original_severity": default}}
        return default, None


    from .taxonomy import enrich_constraint_meta

    def _meta(name: str, group: str) -> Dict[str, str]:
        m = enrich_constraint_meta(name, group=group)
        return m

    def le(name, value, limit, units="", note="", severity="hard", group: str = "general", meaning: str = "", best_knobs=None):
        if best_knobs is None:
            best_knobs = default_best_knobs(name)
        sev, prov = _severity_for(name, severity)
        severity = sev
        value = float(value)
        limit = float(limit)
        m = _meta(name, group)
        cs.append(Constraint(name=name, value=value, limit=limit, sense="<=", passed=(value <= limit),
                             units=units, note=note, severity=severity, group=group,
                             meaning=(meaning or note), best_knobs=best_knobs,
                             mechanism_group=m.get("mechanism_group","GENERAL"),
                             subsystem=m.get("subsystem",""),
                             authority_tier=m.get("authority_tier","unknown"),
                             validity_domain=m.get("validity_domain",""), maturity=maturity_contract, provenance=prov))

    def ge(name, value, limit, units="", note="", severity="hard", group: str = "general", meaning: str = "", best_knobs=None):
        if best_knobs is None:
            best_knobs = default_best_knobs(name)
        sev, prov = _severity_for(name, severity)
        severity = sev
        value = float(value)
        limit = float(limit)
        m = _meta(name, group)
        cs.append(Constraint(name=name, value=value, limit=limit, sense=">=", passed=(value >= limit),
                             units=units, note=note, severity=severity, group=group,
                             meaning=(meaning or note), best_knobs=best_knobs,
                             mechanism_group=m.get("mechanism_group","GENERAL"),
                             subsystem=m.get("subsystem",""),
                             authority_tier=m.get("authority_tier","unknown"),
                             validity_domain=m.get("validity_domain",""), maturity=maturity_contract, provenance=prov))

    # -------- Plasma / stability proxies --------
    q95_val = outputs.get("q95", outputs.get("q95_proxy", float("nan")))
    if q95_val == q95_val:
        ge("q95", q95_val, 2.0, units="-", note="Proxy safety factor", group="plasma")
        q95_min = outputs.get("q95_min", float("nan"))
        q95_max = outputs.get("q95_max", float("nan"))
        if q95_min == q95_min:
            ge("q95_min", q95_val, q95_min, units="-", note="User q95 lower bound", group="plasma")
        if q95_max == q95_max:
            le("q95_max", q95_val, q95_max, units="-", note="User q95 upper bound", severity="soft", group="plasma")

    q0_val = outputs.get("q0", outputs.get("q0_proxy", float("nan")))
    if q0_val == q0_val:
        q0_min = outputs.get("q0_min", float("nan"))
        if q0_min == q0_min:
            ge("q0", q0_val, q0_min, units="-", note="User q0 lower bound", severity="soft", group="plasma")
    if "betaN" in outputs:
        le("betaN", outputs["betaN"], 3.0, units="-", note="Proxy normalized beta limit", group="plasma")
    if "fG" in outputs:
        le("fG", outputs["fG"], 1.0, units="-", note="Greenwald fraction should be ≤ 1", group="plasma")

    # --- Confinement requirement (v371: transport contracts / H_required caps) ---
    Hreq = outputs.get("H_required", float("nan"))
    if Hreq == Hreq:
        # Legacy cap retained: H98_allow
        H98_allow = outputs.get("H98_allow", float("nan"))
        if H98_allow == H98_allow and float(H98_allow) > 0.0:
            le("H_required", Hreq, float(H98_allow), units="-", note="Required confinement cap via H98_allow", group="plasma")
        # v371 caps (explicit optimistic/robust)
        Hopt = outputs.get("H_required_max_optimistic", float("nan"))
        if Hopt == Hopt and float(Hopt) > 0.0:
            le("H_required_opt", Hreq, float(Hopt), units="-", note="Transport contract cap (optimistic)", group="plasma")
        Hrob = outputs.get("H_required_max_robust", float("nan"))
        if Hrob == Hrob and float(Hrob) > 0.0:
            le("H_required_rob", Hreq, float(Hrob), units="-", note="Transport contract cap (robust)", group="plasma")

    # -------- Heat exhaust --------
    if "q_div_MW_m2" in outputs:
        qmax = outputs.get("q_div_max_MW_m2", 10.0)
        le("q_div", outputs["q_div_MW_m2"], qmax, units="MW/m²", note="Divertor peak heat flux proxy", group="exhaust")
    if "P_SOL_over_R_MW_m" in outputs:
        lim = outputs.get("P_SOL_over_R_max_MW_m", 20.0)
        le("P_SOL/R", outputs["P_SOL_over_R_MW_m"], lim, units="MW/m", note="SOL loading proxy (P_SOL/R)", group="exhaust")
    if "q_midplane_MW_m2" in outputs:
        qmax = outputs.get("q_midplane_max_MW_m2", float("nan"))
        if qmax == qmax:  # not NaN => enforce
            le("q_midplane", outputs["q_midplane_MW_m2"], qmax, units="MW/m²", note="Midplane/SOL heat flux proxy", group="exhaust")

    # --- (v320.0) Detachment feasibility cap (optional) ---
    # Enforce that the implied impurity seeding fraction required to meet a q_div target
    # is within a user-declared maximum. This does NOT change the operating point.
    if "detachment_f_z_required" in outputs:
        fz_max = outputs.get("detachment_fz_max", float("nan"))
        if fz_max == fz_max and outputs["detachment_f_z_required"] == outputs["detachment_f_z_required"]:
            le(
                "detachment_fz",
                outputs["detachment_f_z_required"],
                fz_max,
                units="-",
                note="Implied impurity fraction for detachment target",
                group="exhaust",
                severity="soft",
            )


    # -------- Magnets / TF coil --------
    if "tf_sc_flag" in outputs:
        # Technology gate: 1 for superconducting TF, 0 for copper/resistive.
        ge("TF_SC", outputs["tf_sc_flag"], 1.0, units="-", note="TF magnet technology is superconducting (copper TF is research-only)", group="magnets")
    if "B_peak_T" in outputs:
        lim = outputs.get("B_peak_allow_T", 1000.0)
        le("B_peak", outputs["B_peak_T"], lim, units="T", note="Peak field on TF conductor/structure", group="magnets")
    if "sigma_vm_MPa" in outputs:
        lim = outputs.get("sigma_allow_MPa", 9999.0)
        le("sigma_vm", outputs["sigma_vm_MPa"], lim, units="MPa", note="Von Mises stress proxy", group="magnets")
    if "hts_margin" in outputs:
        mmin = outputs.get("hts_margin_min", 1.0)
        ge("HTS margin", outputs["hts_margin"], mmin, units="-", note="SC critical-surface margin proxy (technology-aware)", group="magnets")

    # Magnet technology regime + additional margins (v328.0)
    if "magnet_regime_consistent" in outputs:
        ge("MAG_REGIME_OK", outputs["magnet_regime_consistent"], 1.0, units="bool",
           note="Magnet technology string is consistent with selected regime contract", group="magnets")

    if "J_eng_A_mm2" in outputs:
        lim = outputs.get("J_eng_max_A_mm2", float("nan"))
        if lim == lim:
            le("J_eng", outputs["J_eng_A_mm2"], lim, units="A/mm^2", note="TF winding-pack engineering current density", group="magnets")

    if "Tcoil_K" in outputs:
        tmin = outputs.get("Tcoil_min_K", float("nan"))
        tmax = outputs.get("Tcoil_max_K", float("nan"))
        if tmin == tmin:
            ge("Tcoil_min", outputs["Tcoil_K"], tmin, units="K", note="TF coil temperature within regime window (min)", group="magnets")
        if tmax == tmax:
            le("Tcoil_max", outputs["Tcoil_K"], tmax, units="K", note="TF coil temperature within regime window (max)", group="magnets")

    if "coil_heat_nuclear_MW" in outputs:
        lim = outputs.get("coil_heat_nuclear_max_MW", float("nan"))
        if lim == lim:
            le("coil_heat_nuclear", outputs["coil_heat_nuclear_MW"], lim, units="MW",
               note="Nuclear heating to TF coils (proxy) below regime budget", group="magnets")

    if "coil_thermal_margin" in outputs:
        lim = outputs.get("coil_thermal_margin_min", 0.0)
        ge("coil_thermal_margin", outputs["coil_thermal_margin"], lim, units="-",
           note="Coil thermal margin proxy (cooling headroom) must be non-negative", group="magnets")

    if "quench_proxy_margin" in outputs:
        lim = outputs.get("quench_proxy_min", float("nan"))
        if lim == lim:
            ge("quench_proxy", outputs["quench_proxy_margin"], lim, units="-",
               note="Conservative quench proxy margin (min of dump-voltage headroom and coil thermal margin)", group="magnets")

    if "P_tf_ohmic_MW" in outputs:
        lim = outputs.get("P_tf_ohmic_max_MW", float("nan"))
        if lim == lim and outputs["P_tf_ohmic_MW"] == outputs["P_tf_ohmic_MW"]:
            le("P_TF_ohmic", outputs["P_tf_ohmic_MW"], lim, units="MW", note="Copper TF ohmic dissipation proxy", severity="soft", group="magnets")
    if "hts_lifetime_yr" in outputs:
        # soft screen: prefer at least ~5 years
        ge("HTS lifetime", outputs["hts_lifetime_yr"], 5.0, units="yr", note="Fluence-based HTS lifetime proxy", severity="soft", group="magnets")

    # -------- Neutronics --------
    if "TBR" in outputs:
        tbr_min = outputs.get("TBR_min", 1.05)
        ge("TBR", outputs["TBR"], tbr_min, units="-", note="Tritium breeding ratio proxy", group="neutronics")

        # (v321.0) TBR proxy validity-domain gate (optional; off by default)
        if "TBR_domain_ok" in outputs:
            enforce = bool(outputs.get("neutronics_domain_enforce", 0.0))
            sev = "hard" if enforce else "soft"
            ge("TBR_domain", outputs["TBR_domain_ok"], 1.0, units="-", note="TBR proxy validity-domain satisfied", group="neutronics", severity=sev)


    # Nuclear heating caps (optional; NaN disables)
    if "P_nuc_PF_MW" in outputs:
        lim = outputs.get("P_nuc_pf_max_MW", float("nan"))
        if lim == lim:
            le("P_nuc_PF", outputs["P_nuc_PF_MW"], lim, units="MW", note="PF nuclear heating proxy ≤ cap", severity="soft", group="neutronics")
    if "P_nuc_cryo_kW" in outputs:
        lim = outputs.get("P_nuc_cryo_max_kW", float("nan"))
        if lim == lim:
            le("P_nuc_cryo", outputs["P_nuc_cryo_kW"], lim, units="kW", note="Cryo nuclear load proxy ≤ cap", severity="soft", group="neutronics")

    # DPA / He lifetime caps
    if "fw_lifetime_yr" in outputs:
        lim = outputs.get("fw_lifetime_min_yr", float("nan"))
        if lim == lim:
            ge("fw_lifetime", outputs["fw_lifetime_yr"], lim, units="yr", note="FW replacement lifetime ≥ minimum", group="materials")
    if "blanket_lifetime_yr" in outputs:
        lim = outputs.get("blanket_lifetime_min_yr", float("nan"))
        if lim == lim:
            ge("blanket_lifetime", outputs["blanket_lifetime_yr"], lim, units="yr", note="Blanket replacement lifetime ≥ minimum", group="materials")

    # (v367.0) Replacement cadence and plant-life coverage (materials lifetime closure)
    # These constraints are *feasibility-authoritative* when enabled/finite; they never negotiate.
    if "fw_replace_interval_y" in outputs:
        lim = outputs.get("fw_replace_interval_min_yr", float("nan"))
        if lim == lim:
            ge(
                "fw_replace_interval",
                outputs["fw_replace_interval_y"],
                lim,
                units="yr",
                note="FW replacement cadence ≥ minimum interval",
                group="materials_lifetime",
            )
    if "blanket_replace_interval_y" in outputs:
        lim = outputs.get("blanket_replace_interval_min_yr", float("nan"))
        if lim == lim:
            ge(
                "blanket_replace_interval",
                outputs["blanket_replace_interval_y"],
                lim,
                units="yr",
                note="Blanket replacement cadence ≥ minimum interval",
                group="materials_lifetime",
            )

    try:
        enforce = bool(outputs.get("materials_life_cover_plant_enforce", 0.0))
    except Exception:
        enforce = False
    if enforce:
        # When enforced, require the material lifetime proxy to cover declared plant design lifetime.
        # This is a policy constraint, not a physics closure.
        plant_life = outputs.get("plant_design_lifetime_yr", float("nan"))
        if "fw_lifetime_yr" in outputs and plant_life == plant_life:
            ge(
                "fw_life_covers_plant",
                outputs["fw_lifetime_yr"],
                plant_life,
                units="yr",
                note="FW lifetime proxy ≥ plant design lifetime (policy enforcement)",
                severity="hard",
                group="materials_lifetime",
            )
        if "blanket_lifetime_yr" in outputs and plant_life == plant_life:
            ge(
                "blanket_life_covers_plant",
                outputs["blanket_lifetime_yr"],
                plant_life,
                units="yr",
                note="Blanket lifetime proxy ≥ plant design lifetime (policy enforcement)",
                severity="hard",
                group="materials_lifetime",
            )

    # Temperature window checks (proxy); enforcement can be hardened by policy/inputs.
    if "fw_T_margin_C" in outputs:
        _enf = bool(outputs.get("materials_domain_enforce", 0.0))
        sev = "hard" if (_enf or bool(outputs.get("fw_T_enforce", 0.0))) else "soft"
        ge("fw_T_window", outputs["fw_T_margin_C"], 0.0, units="°C", note="FW operating temperature within material window", severity=sev, group="materials")
    if "blanket_T_margin_C" in outputs:
        _enf = bool(outputs.get("materials_domain_enforce", 0.0))
        sev = "hard" if (_enf or bool(outputs.get("blanket_T_enforce", 0.0))) else "soft"
        ge("blanket_T_window", outputs["blanket_T_margin_C"], 0.0, units="°C", note="Blanket operating temperature within material window", severity=sev, group="materials")

    # Allowable stress proxy (if sigma_oper provided)
    if "fw_sigma_margin_MPa" in outputs and outputs.get("fw_sigma_margin_MPa", float("nan")) == outputs.get("fw_sigma_margin_MPa", float("nan")):
        sev = "hard" if bool(outputs.get("materials_domain_enforce", 0.0)) else "soft"
        ge("fw_stress", outputs["fw_sigma_margin_MPa"], 0.0, units="MPa", note="FW stress ≤ irradiation-adjusted allowable", severity=sev, group="materials")
    if "blanket_sigma_margin_MPa" in outputs and outputs.get("blanket_sigma_margin_MPa", float("nan")) == outputs.get("blanket_sigma_margin_MPa", float("nan")):
        sev = "hard" if bool(outputs.get("materials_domain_enforce", 0.0)) else "soft"
        ge("blanket_stress", outputs["blanket_sigma_margin_MPa"], 0.0, units="MPa", note="Blanket stress ≤ irradiation-adjusted allowable", severity=sev, group="materials")
    if "neutron_wall_load_MW_m2" in outputs:
        lim = outputs.get("neutron_wall_load_max_MW_m2", 4.0)
        le("NWL", outputs["neutron_wall_load_MW_m2"], lim, units="MW/m²", note="Neutron wall load proxy", group="neutronics")

    # Nuclear heating caps (materials/neutronics authority; optional)
    if "P_nuc_total_MW" in outputs:
        lim = outputs.get("P_nuc_total_max_MW", float("nan"))
        if lim == lim:
            le("P_nuc_total", outputs["P_nuc_total_MW"], lim, units="MW", note="Total nuclear heating proxy ≤ cap", severity="soft", group="neutronics")
    if "P_nuc_TF_MW" in outputs:
        lim = outputs.get("P_nuc_tf_max_MW", float("nan"))
        if lim == lim:
            le("P_nuc_TF", outputs["P_nuc_TF_MW"], lim, units="MW", note="TF nuclear heating proxy ≤ cap", severity="soft", group="neutronics")

    # -------- Fuel cycle / lifetime (optional) --------
    if "T_inventory_proxy_g" in outputs:
        lim = outputs.get("tritium_inventory_max_g", float("nan"))
        if lim == lim:
            le(
                "T_inventory",
                outputs["T_inventory_proxy_g"],
                lim,
                units="g",
                note="Tritium inventory proxy ≤ maximum (fuel-cycle feasibility screen)",
                severity="hard",
                group="fuel_cycle",
            )

    if "fw_dpa_per_year" in outputs:
        lim = outputs.get("fw_dpa_max_per_year", float("nan"))
        if lim == lim:
            le(
                "FW dpa/y",
                outputs["fw_dpa_per_year"],
                lim,
                units="dpa/y",
                note="First-wall damage rate proxy ≤ maximum",
                severity="soft",
                group="neutronics",
            )

    # -------- Plant net-electric --------
    if "COE_proxy_USD_per_MWh" in outputs:
        coe_max = outputs.get("COE_max_USD_per_MWh", float("nan"))
        if coe_max == coe_max and outputs["COE_proxy_USD_per_MWh"] == outputs["COE_proxy_USD_per_MWh"]:
            le("COE", outputs["COE_proxy_USD_per_MWh"], coe_max, units="USD/MWh", note="Cost of electricity proxy", severity="soft", group="economics")

    if "P_e_net_MW" in outputs:
        pmin = outputs.get("P_net_min_MW", 0.0)
        ge("P_net", outputs["P_e_net_MW"], pmin, units="MW(e)", note="Net electric ≥ minimum requirement", severity="hard" if pmin>0 else "soft", group="economics")

    if "annual_net_MWh" in outputs:
        amin = outputs.get("annual_net_MWh_min", float("nan"))
        if amin == amin:
            ge(
                "Annual net",
                outputs["annual_net_MWh"],
                amin,
                units="MWh/y",
                note="Annual net generation ≥ minimum (availability-aware)",
                severity="soft",
                group="economics",
            )

    # -------- Build / coils (opt-in enforcement) --------
    if "inboard_margin_m" in outputs:
        enforce = outputs.get("enforce_radial_build", 0.0)
        try:
            enforce = float(enforce)
        except Exception:
            enforce = 0.0
        if enforce >= 0.5:
            ge(
                "Inboard build",
                outputs["inboard_margin_m"],
                0.0,
                units="m",
                note="Inboard radial build closure margin ≥ 0 (explicit stack closure)",
                severity="hard",
                group="engineering",
            )


    # -------- Engineering Actuator Limits Authority (v361.0) --------
    # These are *capacity* constraints: they gate feasibility only when explicit *_max caps are finite.
    # They do not change frozen truth; they compare precomputed requirement proxies to declared limits.

    # Auxiliary + CD wallplug draw
    if "P_aux_total_el_MW" in outputs:
        cap = outputs.get("P_aux_max_MW", float("nan"))
        if cap == cap and outputs["P_aux_total_el_MW"] == outputs["P_aux_total_el_MW"]:
            le(
                "P_aux_total_el",
                outputs["P_aux_total_el_MW"],
                cap,
                units="MW",
                note="Aux+CD wallplug electric draw proxy must be ≤ declared cap",
                group="actuators",
            )

    # Current-drive actuator capacity: required launched CD power to meet NI target
    if "P_cd_required_MW" in outputs:
        cap = outputs.get("Pcd_max_MW", float("nan"))
        if cap == cap and outputs["P_cd_required_MW"] == outputs["P_cd_required_MW"]:
            le(
                "P_cd_required",
                outputs["P_cd_required_MW"],
                cap,
                units="MW",
                note="Launched CD power required to meet NI target must be ≤ installed CD capacity",
                group="actuators",
            )

    # Channel-specific screens (opt-in via finite caps)
    if "eccd_launcher_power_density_MW_m2" in outputs:
        cap = outputs.get("eccd_launcher_power_density_max_MW_m2", float("nan"))
        if cap == cap and outputs["eccd_launcher_power_density_MW_m2"] == outputs["eccd_launcher_power_density_MW_m2"]:
            le(
                "eccd_power_density",
                outputs["eccd_launcher_power_density_MW_m2"],
                cap,
                units="MW/m^2",
                note="ECCD launcher power density proxy must be ≤ cap",
                severity="soft",
                group="actuators",
            )
    if "nbi_shinethrough_frac" in outputs:
        cap = outputs.get("nbi_shinethrough_frac_max", float("nan"))
        if cap == cap and outputs["nbi_shinethrough_frac"] == outputs["nbi_shinethrough_frac"]:
            le(
                "nbi_shinethrough",
                outputs["nbi_shinethrough_frac"],
                cap,
                units="-",
                note="NBI shine-through fraction proxy must be ≤ cap",
                severity="soft",
                group="actuators",
            )

    # PF envelope capacity caps (from control contracts)
    for key, lim_key, units, name, note in [
        ("pf_I_peak_MA", "pf_I_peak_max_MA", "MA", "pf_I_peak", "PF peak current requirement must be ≤ cap"),
        ("pf_dIdt_peak_MA_s", "pf_dIdt_max_MA_s", "MA/s", "pf_dIdt_peak", "PF peak dI/dt requirement must be ≤ cap"),
        ("pf_V_peak_V", "pf_V_peak_max_V", "V", "pf_V_peak", "PF peak voltage requirement must be ≤ cap"),
        ("pf_P_peak_MW", "pf_P_peak_max_MW", "MW", "pf_P_peak", "PF peak power requirement must be ≤ cap"),
        ("pf_E_pulse_MJ", "pf_E_pulse_max_MJ", "MJ", "pf_E_pulse", "PF pulse energy requirement must be ≤ cap"),
    ]:
        if key in outputs:
            lim = outputs.get(lim_key, float("nan"))
            if lim == lim and outputs[key] == outputs[key]:
                le(name, outputs[key], lim, units=units, note=note, group="actuators")

    # CS loop-voltage ramp proxy cap (from PF/CS authority)
    if "cs_V_loop_ramp_V" in outputs:
        cap = outputs.get("cs_V_loop_max_V", float("nan"))
        if cap == cap and outputs["cs_V_loop_ramp_V"] == outputs["cs_V_loop_ramp_V"]:
            le(
                "cs_V_loop_ramp",
                outputs["cs_V_loop_ramp_V"],
                cap,
                units="V",
                note="CS loop-voltage ramp proxy must be ≤ cap",
                group="actuators",
            )

    # Average PF draw cap (ledger)
    if "P_pf_avg_MW" in outputs:
        cap = outputs.get("P_pf_avg_max_MW", float("nan"))
        if cap == cap and outputs["P_pf_avg_MW"] == outputs["P_pf_avg_MW"]:
            le(
                "P_pf_avg",
                outputs["P_pf_avg_MW"],
                cap,
                units="MW",
                note="Average PF electric draw proxy must be ≤ cap",
                group="actuators",
            )

    # Peak power supply draw cap (optional): max(PF peak, aux/CD wallplug, VS control, RWM control)
    if "P_supply_peak_MW" in outputs:
        cap = outputs.get("P_supply_peak_max_MW", float("nan"))
        if cap == cap and outputs["P_supply_peak_MW"] == outputs["P_supply_peak_MW"]:
            le(
                "P_supply_peak",
                outputs["P_supply_peak_MW"],
                cap,
                units="MW",
                note="Peak power-supply draw proxy must be ≤ cap",
                group="actuators",
            )

    # -------- Pulsed operation --------
    if "cycles_per_year" in outputs:
        cmax = outputs.get("cycles_max", float("nan"))
        if cmax == cmax and outputs["cycles_per_year"] == outputs["cycles_per_year"]:
            le("cycles", outputs["cycles_per_year"], cmax, units="1/y", note="Fatigue cycle count proxy", severity="soft", group="pulse")

    if "t_flat_s" in outputs and str(outputs.get("t_flat_s")) != "nan":
        tmin = outputs.get("pulse_min_s", float("nan"))
        if tmin == tmin:  # not nan
            ge("t_flat", outputs["t_flat_s"], tmin, units="s", note="Flat-top duration (pulsed mode)", group="pulse")

    # -------- Profile-consistency (lightweight sanity checks) --------
    # These do not attempt transport; they are screens to prevent numerically-feasible
    # but physically nonsensical combinations.
    # Only active when the relevant keys exist in outputs.
    if "bootstrap_frac" in outputs:
        # Prefer 0 <= f_bs <= 1, allow mild overshoot as soft.
        ge("f_bs_min", outputs["bootstrap_frac"], 0.0, units="-", note="Bootstrap fraction ≥ 0", group="profiles")
        le("f_bs_max", outputs["bootstrap_frac"], 1.2, units="-", note="Bootstrap fraction not unphysically high", severity="soft", group="profiles")
    if "ped_width_frac" in outputs:
        ge("ped_width_min", outputs["ped_width_frac"], 0.005, units="-", note="Pedestal width fraction not vanishing", severity="soft", group="profiles")
        le("ped_width_max", outputs["ped_width_frac"], 0.25, units="-", note="Pedestal width fraction not excessive", severity="soft", group="profiles")
    if "P_sep_MW" in outputs and "P_rad_frac" in outputs:
        # If radiation fraction is very high, ensure some P_sep remains (avoid negative P_sep proxies).
        ge("P_sep_nonneg", outputs["P_sep_MW"], 0.0, units="MW", note="Power crossing separatrix non-negative", group="profiles")
        le("Prad_frac", outputs["P_rad_frac"], 0.95, units="-", note="Radiated power fraction not near 1", severity="soft", group="profiles")

    return cs
