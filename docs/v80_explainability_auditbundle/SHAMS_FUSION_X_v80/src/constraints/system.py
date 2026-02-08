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


def build_constraints_from_outputs(out: Dict[str, float]) -> List[Constraint]:
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

    # Pulse / flux
    add("Flat-top duration", "t_flat_s", lo_key="pulse_min_s", units="s",
        description="Flat-top duration in pulsed mode (if computed).")
    add("CS flux swing (required ≤ available)", "cs_flux_required_Wb", hi_key="cs_flux_available_Wb", units="Wb",
        description="Central-solenoid flux swing proxy: required inductive flux must be below available CS flux.")
    add("CS flux margin", "cs_flux_margin", lo_key="cs_flux_margin_min", units="-",
        description="Flux margin (avail-req)/req; optional minimum requirement.")

    # TF coil thermal (optional)
    add("TF coil thermal load", "coil_heat_MW", hi_key="coil_cooling_capacity_MW", units="MW",
        description="TF coil heating proxy (nuclear + AC) must not exceed cooling capacity proxy.")
    add("TF coil heat (hard cap)", "coil_heat_MW", hi_key="coil_heat_max_MW", units="MW",
        description="Optional hard cap on TF coil heating proxy.")

    # Net electric (optional)
    add("Net electric power", "P_net_MW", lo_key="P_net_min_MW", units="MW",
        description="Net electric power must exceed minimum, if enabled.")


# Risk / lifetime / availability / PF / Tritium
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
    add("Tritium inventory proxy", "T_inventory_proxy_g", hi_key="tritium_inventory_max_g", units="g",
    description="Tritium inventory proxy derived from burn rate and processing reserve.")
    add("PF coil current proxy", "pf_I_pf_MA", hi_key="pf_current_max_MA", units="MA",
    description="PF coil current demand proxy (screening).")
    add("PF stress proxy", "pf_stress_proxy", hi_key="pf_stress_max", units="-",
    description="PF coil stress proxy (screening).")
    
    # --- Phase-2 engineering closures (PROCESS-inspired) ---
    add("TF current density", "tf_Jop_MA_per_mm2", hi_key="tf_Jop_limit_MA_per_mm2", units="MA/mm^2",
    description="Operating current density must be below limit (proxy).")
    add("TF stress", "tf_stress_MPa", hi_key="tf_stress_allow_MPa", units="MPa",
    description="TF coil stress proxy must be below allowable.")
    add("TF strain", "tf_strain", hi_key="tf_strain_allow", units="-",
    description="TF coil strain proxy must be below allowable (screening). Optional cap.")
    add("Divertor heat flux", "q_parallel_MW_per_m2", hi_key="q_parallel_limit_MW_per_m2", units="MW/m^2",
    description="Parallel heat flux proxy must be below technology-mode limit.")
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
