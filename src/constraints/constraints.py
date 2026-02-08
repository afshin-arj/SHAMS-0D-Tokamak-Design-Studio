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
