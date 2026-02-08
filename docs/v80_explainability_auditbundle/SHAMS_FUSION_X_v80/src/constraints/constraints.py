from __future__ import annotations
from dataclasses import dataclass

from .metadata import default_best_knobs
from typing import Dict, List

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

def evaluate_constraints(outputs: Dict[str, float]) -> List[Constraint]:
    """Evaluate a PROCESS-like constraint set from point outputs.

    This function is intentionally conservative and proxy-based. It only evaluates
    constraints when the required keys exist in ``outputs``. Limits are taken
    from explicit *_max/*_min/*_allow keys when available, otherwise from
    reasonable default caps suitable for early-stage screening.
    """
    cs: List[Constraint] = []

    def le(name, value, limit, units="", note="", severity="hard", group: str = "general", meaning: str = "", best_knobs=None):
        if best_knobs is None:
            best_knobs = default_best_knobs(name)
        value = float(value)
        limit = float(limit)
        cs.append(Constraint(name=name, value=value, limit=limit, sense="<=", passed=(value <= limit),
                             units=units, note=note, severity=severity, group=group,
                             meaning=(meaning or note), best_knobs=best_knobs))

    def ge(name, value, limit, units="", note="", severity="hard", group: str = "general", meaning: str = "", best_knobs=None):
        if best_knobs is None:
            best_knobs = default_best_knobs(name)
        value = float(value)
        limit = float(limit)
        cs.append(Constraint(name=name, value=value, limit=limit, sense=">=", passed=(value >= limit),
                             units=units, note=note, severity=severity, group=group,
                             meaning=(meaning or note), best_knobs=best_knobs))

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


    # -------- Magnets / TF coil --------
    if "B_peak_T" in outputs:
        lim = outputs.get("B_peak_allow_T", 1000.0)
        le("B_peak", outputs["B_peak_T"], lim, units="T", note="Peak field on TF conductor/structure", group="magnets")
    if "sigma_vm_MPa" in outputs:
        lim = outputs.get("sigma_allow_MPa", 9999.0)
        le("sigma_vm", outputs["sigma_vm_MPa"], lim, units="MPa", note="Von Mises stress proxy", group="magnets")
    if "hts_margin" in outputs:
        mmin = outputs.get("hts_margin_min", 1.0)
        ge("HTS margin", outputs["hts_margin"], mmin, units="-", note="Critical-surface margin (≥1 is allowed)", group="magnets")
    if "hts_lifetime_yr" in outputs:
        # soft screen: prefer at least ~5 years
        ge("HTS lifetime", outputs["hts_lifetime_yr"], 5.0, units="yr", note="Fluence-based HTS lifetime proxy", severity="soft", group="magnets")

    # -------- Neutronics --------
    if "TBR" in outputs:
        tbr_min = outputs.get("TBR_min", 1.05)
        ge("TBR", outputs["TBR"], tbr_min, units="-", note="Tritium breeding ratio proxy", group="neutronics")
    if "neutron_wall_load_MW_m2" in outputs:
        lim = outputs.get("neutron_wall_load_max_MW_m2", 4.0)
        le("NWL", outputs["neutron_wall_load_MW_m2"], lim, units="MW/m²", note="Neutron wall load proxy", group="neutronics")

    # -------- Plant net-electric --------
    if "COE_proxy_USD_per_MWh" in outputs:
        coe_max = outputs.get("COE_max_USD_per_MWh", float("nan"))
        if coe_max == coe_max and outputs["COE_proxy_USD_per_MWh"] == outputs["COE_proxy_USD_per_MWh"]:
            le("COE", outputs["COE_proxy_USD_per_MWh"], coe_max, units="USD/MWh", note="Cost of electricity proxy", severity="soft", group="economics")

    if "P_e_net_MW" in outputs:
        pmin = outputs.get("P_net_min_MW", 0.0)
        ge("P_net", outputs["P_e_net_MW"], pmin, units="MW(e)", note="Net electric ≥ minimum requirement", severity="hard" if pmin>0 else "soft", group="economics")

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
