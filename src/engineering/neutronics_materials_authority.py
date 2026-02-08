from __future__ import annotations

"""Neutronics & Materials Authority (proxy, deterministic).

SHAMS law compliance
--------------------
- Purely algebraic proxies (no Monte Carlo, no iterative solvers).
- Frozen truth: deterministic and conservative.
- Constraints are explicit; NaN disables enforcement.

This module provides:
- fast (14 MeV) and gamma attenuation through a radial stack
- nuclear heating partitioning across regions (in-vessel + ex-vessel)
- DPA and He production rate proxies and derived replacement lifetimes
- simple material temperature window checks
- simple irradiation- & temperature-adjusted allowable stress proxy
- improved TBR proxy (still monotonic, transparent)

All coefficients are screening-level, stored in :mod:`engineering.materials_library`.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

try:
    from .materials_library import get_material_v2, MaterialNeutronicsPropsV2
except Exception:  # pragma: no cover
    from engineering.materials_library import get_material_v2, MaterialNeutronicsPropsV2  # type: ignore


@dataclass(frozen=True)
class StackRegionV2:
    name: str
    thickness_m: float
    material: MaterialNeutronicsPropsV2


def build_stack_v2(inp: Dict[str, float | str]) -> List[StackRegionV2]:
    """Build a standard inboard radial stack for neutronics/materials proxies."""

    def _mat(key: str, fallback_name: str) -> MaterialNeutronicsPropsV2:
        return get_material_v2(str(inp.get(key, fallback_name)))

    return [
        StackRegionV2("First wall", float(inp.get("t_fw_m", 0.0)), _mat("fw_material", "EUROFER")),
        StackRegionV2("Blanket", float(inp.get("t_blanket_m", 0.0)), _mat("blanket_material", "LiPb")),
        StackRegionV2("Shield", float(inp.get("t_shield_m", 0.0)), _mat("shield_material", "WC")),
        StackRegionV2("Vacuum vessel", float(inp.get("t_vv_m", 0.0)), _mat("vv_material", "VV_STEEL")),
        StackRegionV2("TF winding pack", float(inp.get("t_tf_wind_m", 0.0)), _mat("tf_material", "REBCO")),
        StackRegionV2("TF structure", float(inp.get("t_tf_struct_m", 0.0)), _mat("tf_material", "REBCO")),
    ]


def attenuation_factors(stack: List[StackRegionV2]) -> Dict[str, float]:
    """Compute fast and gamma attenuation factors through the stack.

    Uses macroscopic removal coefficients per region:
    A = exp(-Σ Σ_R * t)
    """
    import math

    tau_fast = 0.0
    tau_gam = 0.0
    for r in stack:
        if r.thickness_m <= 0:
            continue
        tau_fast += max(r.material.Sigma_R_14_1_per_m, 0.0) * max(r.thickness_m, 0.0)
        tau_gam += max(r.material.Sigma_R_gamma_1_per_m, 0.0) * max(r.thickness_m, 0.0)

    return {
        "neutron_attenuation_fast": float(math.exp(-tau_fast)),
        "neutron_attenuation_gamma": float(math.exp(-tau_gam)),
        "tau_fast": float(tau_fast),
        "tau_gamma": float(tau_gam),
    }


def cumulative_fast_to_region(stack: List[StackRegionV2]) -> Dict[str, float]:
    """Return cumulative fast attenuation from plasma to each region entrance."""
    import math

    out: Dict[str, float] = {}
    tau = 0.0
    for r in stack:
        out[f"A_fast_to_{r.name}"] = float(math.exp(-tau))
        if r.thickness_m > 0:
            tau += max(r.material.Sigma_R_14_1_per_m, 0.0) * max(r.thickness_m, 0.0)
    return out


def nuclear_heating_partition(
    P_fus_MW: float,
    stack: List[StackRegionV2],
    *,
    f_geom_to_tf: float,
    archetype: str = "standard",
) -> Dict[str, float]:
    """Allocate nuclear heating across regions.

    This is *not* transport. We use an archetype fraction table for in-vessel
    deposition and a simple attenuated leak fraction for ex-vessel components.

    Parameters
    ----------
    P_fus_MW:
        Total fusion power (thermal) [MW].
    f_geom_to_tf:
        Geometry factor from FW to TF (dimensionless, very approximate).
    archetype:
        One of: standard | heavy_shield | compact
    """

    P = float(max(P_fus_MW, 0.0))

    # In-vessel deposition fractions (must sum <= 1; remainder treated as "other/leak").
    frac_tables = {
        "standard": {
            "First wall": 0.08,
            "Blanket": 0.25,
            "Shield": 0.12,
            "Vacuum vessel": 0.05,
        },
        "heavy_shield": {
            "First wall": 0.07,
            "Blanket": 0.22,
            "Shield": 0.15,
            "Vacuum vessel": 0.05,
        },
        "compact": {
            "First wall": 0.09,
            "Blanket": 0.28,
            "Shield": 0.10,
            "Vacuum vessel": 0.05,
        },
    }
    fr = frac_tables.get(archetype, frac_tables["standard"])

    out: Dict[str, float] = {}
    for r in stack:
        if r.name in fr and r.thickness_m > 0:
            out[f"P_nuc_{r.name}_MW"] = P * fr[r.name]

    P_in = sum(out.values())

    # Ex-vessel heating to coils is treated as a small fraction of attenuated leakage.
    # Use fast attenuation proxy to represent leakage reduction.
    att = attenuation_factors(stack)["neutron_attenuation_fast"]
    leak_frac = max(0.0, 1.0 - (P_in / max(P, 1e-30)))
    P_leak = P * leak_frac

    # Partition of leakage to TF/PF/cryo (placeholders; explicitly labeled).
    P_to_tf = P_leak * max(min(float(f_geom_to_tf), 1.0), 0.0) * att
    P_to_pf = 0.35 * P_to_tf
    P_to_cryo = 0.02 * P_to_tf

    out["P_nuc_TF_MW"] = float(P_to_tf)
    out["P_nuc_PF_MW"] = float(P_to_pf)
    out["P_nuc_cryo_kW"] = float(P_to_cryo * 1e3)

    out["P_nuc_total_MW"] = float(P_in + P_to_tf + P_to_pf)
    out["P_nuc_in_vessel_MW"] = float(P_in)
    out["P_nuc_leak_MW"] = float(P_leak)

    return out


def dpa_he_lifetimes(
    neutron_wall_load_MW_m2: float,
    stack: List[StackRegionV2],
    *,
    fw_oper_years: float = 1.0,
) -> Dict[str, float]:
    """Compute DPA & He production proxies and replacement lifetimes.

    We tie rates to neutron wall load and apply cumulative fast attenuation
    before each region.
    """
    W_n = float(max(neutron_wall_load_MW_m2 if neutron_wall_load_MW_m2 == neutron_wall_load_MW_m2 else 0.0, 0.0))
    A_to = cumulative_fast_to_region(stack)

    # Identify key regions/materials
    fw = next((r for r in stack if r.name == "First wall"), None)
    bl = next((r for r in stack if r.name == "Blanket"), None)

    out: Dict[str, float] = {}

    def _region_rates(prefix: str, reg: StackRegionV2, W_local: float) -> None:
        mat = reg.material
        dpa_y = mat.k_dpa_per_MWm2_fpy * W_local
        he_y = mat.k_He_appm_per_MWm2_fpy * W_local
        out[f"{prefix}_dpa_per_year"] = float(dpa_y)
        out[f"{prefix}_He_appm_per_year"] = float(he_y)
        out[f"{prefix}_dpa_total_limit"] = float(mat.dpa_total_limit)
        out[f"{prefix}_He_total_limit_appm"] = float(mat.He_total_limit_appm)
        out[f"{prefix}_lifetime_dpa_yr"] = float(mat.dpa_total_limit / max(dpa_y, 1e-30))
        out[f"{prefix}_lifetime_He_yr"] = float(mat.He_total_limit_appm / max(he_y, 1e-30))
        out[f"{prefix}_lifetime_yr"] = float(min(out[f"{prefix}_lifetime_dpa_yr"], out[f"{prefix}_lifetime_He_yr"]))

    if fw is not None:
        W_fw = W_n * float(A_to.get("A_fast_to_First wall", 1.0))
        _region_rates("fw", fw, W_fw)

    if bl is not None:
        W_bl = W_n * float(A_to.get("A_fast_to_Blanket", 1.0))
        _region_rates("blanket", bl, W_bl)

    # Provide end-of-life totals for a nominal replacement horizon (fw_oper_years)
    # This is not a time-domain simulation; it is a simple scaling.
    if fw is not None:
        out["fw_dpa_total_at_years"] = float(out.get("fw_dpa_per_year", 0.0) * max(fw_oper_years, 0.0))
        out["fw_He_total_appm_at_years"] = float(out.get("fw_He_appm_per_year", 0.0) * max(fw_oper_years, 0.0))
    if bl is not None:
        out["blanket_dpa_total_at_years"] = float(out.get("blanket_dpa_per_year", 0.0) * max(fw_oper_years, 0.0))
        out["blanket_He_total_appm_at_years"] = float(out.get("blanket_He_appm_per_year", 0.0) * max(fw_oper_years, 0.0))

    return out


def temperature_window_checks(
    *,
    T_C: float,
    mat: MaterialNeutronicsPropsV2,
    name: str,
) -> Dict[str, float]:
    """Return margin to stay within [Tmin, Tmax]."""
    T = float(T_C)
    Tmin = float(mat.T_min_C)
    Tmax = float(mat.T_max_C)
    margin_low = T - Tmin
    margin_high = Tmax - T
    margin = min(margin_low, margin_high)
    return {
        f"{name}_T_oper_C": T,
        f"{name}_T_min_C": Tmin,
        f"{name}_T_max_C": Tmax,
        f"{name}_T_margin_C": float(margin),
    }


def allowable_stress_proxy(
    *,
    sigma_oper_MPa: float,
    dpa_total: float,
    T_C: float,
    mat: MaterialNeutronicsPropsV2,
    prefix: str,
) -> Dict[str, float]:
    """Compute a conservative allowable stress proxy.

    sigma_allow = sigma0 * f_irr(dpa) * f_T(T)
    - f_irr = 1 / (1 + dpa / dpa_ref)
    - f_T peaks at mid-window and falls linearly to 0.6 at edges

    If sigma_oper_MPa is NaN, returns NaN margin and keeps numbers for display.
    """
    import math

    sigma0 = float(mat.sigma0_allow_MPa)
    dpa_ref = max(float(mat.dpa_ref_for_strength_drop), 1e-6)

    f_irr = 1.0 / (1.0 + max(dpa_total, 0.0) / dpa_ref)

    Tmin = float(mat.T_min_C)
    Tmax = float(mat.T_max_C)
    T = float(T_C)
    if Tmax <= Tmin:
        f_T = 0.6
    else:
        mid = 0.5 * (Tmin + Tmax)
        span = 0.5 * (Tmax - Tmin)
        x = abs(T - mid) / max(span, 1e-6)
        # x in [0,1] inside window, >1 outside.
        f_T = max(0.2, 1.0 - 0.4 * min(max(x, 0.0), 1.5))

    sigma_allow = sigma0 * f_irr * f_T

    op = float(sigma_oper_MPa)
    margin = float("nan")
    if op == op:
        margin = sigma_allow - op

    return {
        f"{prefix}_sigma_oper_MPa": op,
        f"{prefix}_sigma_allow_MPa": float(sigma_allow),
        f"{prefix}_sigma_margin_MPa": float(margin),
        f"{prefix}_sigma_f_irr": float(f_irr),
        f"{prefix}_sigma_f_T": float(f_T),
    }


@dataclass(frozen=True)
class TBRProxyResultV2:
    TBR: float
    TBR_min: float
    margin: float
    validity: str


def tbr_proxy_v2(
    *,
    t_blanket_m: float,
    blanket_coverage: float,
    li6_enrichment: float,
    port_fraction: float,
    blanket_type: str,
    multiplier_material: str,
    neutron_attenuation_fast: float,
    TBR_min: float,
) -> TBRProxyResultV2:
    """Transparent TBR proxy with explicit knobs.

    This remains a monotonic screening model.
    """
    import math

    tb = float(max(t_blanket_m, 0.0))
    cov = float(max(min(blanket_coverage, 1.0), 0.0))
    port = float(max(min(port_fraction, 0.8), 0.0))
    e6 = float(max(min(li6_enrichment, 0.95), 0.0))

    base = {
        "LiPb": 1.15,
        "FLiBe": 1.10,
    }.get(str(blanket_type), 1.12)

    mult = {
        "None": 1.0,
        "Be": 1.05,
        "Pb": 1.03,
        "Be2": 1.08,
    }.get(str(multiplier_material), 1.0)

    f_thk = 1.0 - math.exp(-tb / 0.45)
    f_cov = cov * (1.0 - port)
    f_enr = 0.65 + 0.9 * e6
    f_pen = 0.75 + 0.25 * max(min(float(neutron_attenuation_fast), 1.0), 0.0)

    TBR = base * mult * (0.6 + 0.55 * f_thk) * f_cov * f_enr * f_pen

    validity = "proxy"
    if tb < 0.25 or tb > 1.8:
        validity = "out_of_range"
    if cov < 0.5 or cov > 0.95:
        validity = "out_of_range"

    margin = TBR - float(TBR_min)
    return TBRProxyResultV2(TBR=float(TBR), TBR_min=float(TBR_min), margin=float(margin), validity=validity)




# --- (v321.0) Validity-domain enforcement helpers ---

def _tbr_domain_check_v3(*, t_blanket_m: float, blanket_coverage: float) -> dict:
    """Return validity-domain flags and margins for the TBR proxy.

    Domain is intentionally *tight* and screening-level. This does not alter the operating point.

    Returns
    -------
    dict with keys:
      - TBR_domain_ok (1.0/0.0)
      - TBR_domain_margin (min distance to bounds; negative if out-of-range)
      - TBR_domain_tb_margin_m
      - TBR_domain_cov_margin
      - TBR_domain_driver (string label)
    """
    tb=float(t_blanket_m)
    cov=float(blanket_coverage)

    tb_lo, tb_hi = 0.25, 1.80
    cov_lo, cov_hi = 0.50, 0.95

    tb_margin=min(tb-tb_lo, tb_hi-tb)
    cov_margin=min(cov-cov_lo, cov_hi-cov)

    domain_margin=min(tb_margin, cov_margin)
    ok = 1.0 if domain_margin >= 0.0 else 0.0

    driver = 'ok'
    if ok < 0.5:
        # deterministically select most-negative contributor
        if tb_margin <= cov_margin:
            driver = 't_blanket_m'
        else:
            driver = 'blanket_coverage'

    return {
        'TBR_domain_ok': float(ok),
        'TBR_domain_margin': float(domain_margin),
        'TBR_domain_tb_margin_m': float(tb_margin),
        'TBR_domain_cov_margin': float(cov_margin),
        'TBR_domain_driver': str(driver),
    }
def compute_neutronics_materials_bundle(
    out: Dict[str, float],
    inp: object,
) -> Dict[str, float]:
    """Return additional outputs for neutronics/materials authority.

    Inputs are read from ``inp`` only to fetch explicit contract values.
    This does not modify or iterate on physics.
    """

    # Stack inputs
    stack_inp = {
        "t_fw_m": float(getattr(inp, "t_fw_m", 0.0)),
        "t_blanket_m": float(getattr(inp, "t_blanket_m", 0.0)),
        "t_shield_m": float(getattr(inp, "t_shield_m", 0.0)),
        "t_vv_m": float(getattr(inp, "t_vv_m", 0.0)),
        "t_tf_wind_m": float(getattr(inp, "t_tf_wind_m", 0.0)),
        "t_tf_struct_m": float(getattr(inp, "t_tf_struct_m", 0.0)),
        "fw_material": str(getattr(inp, "fw_material", "EUROFER")),
        "blanket_material": str(getattr(inp, "blanket_material", "LiPb")),
        "shield_material": str(getattr(inp, "shield_material", "WC")),
        "vv_material": str(getattr(inp, "vv_material", "VV_STEEL")),
        "tf_material": str(getattr(inp, "tf_material", "REBCO")),
    }

    stack = build_stack_v2(stack_inp)
    att = attenuation_factors(stack)

    # Heating
    Pfus_total_MW = float(max(out.get("P_fusion_total_MW", out.get("P_fusion_MW", 0.0)), 0.0))
    archetype = str(getattr(inp, "neutronics_archetype", "standard"))
    heat = nuclear_heating_partition(
        Pfus_total_MW,
        stack,
        f_geom_to_tf=float(getattr(inp, "f_geom_to_tf", 0.05)),
        archetype=archetype,
    )

    # Damage / lifetimes
    nwl = float(out.get("neutron_wall_load_MW_m2", float("nan")))
    dmg = dpa_he_lifetimes(nwl, stack, fw_oper_years=float(getattr(inp, "fw_replacement_horizon_yr", 1.0)))

    # Temperature windows
    fw_mat = get_material_v2(str(getattr(inp, "fw_material", "EUROFER")))
    bl_mat = get_material_v2(str(getattr(inp, "blanket_material", "LiPb")))

    tw_fw = temperature_window_checks(T_C=float(getattr(inp, "T_fw_oper_C", float("nan"))), mat=fw_mat, name="fw")
    tw_bl = temperature_window_checks(T_C=float(getattr(inp, "T_blanket_oper_C", float("nan"))), mat=bl_mat, name="blanket")

    # Allowable stress proxies
    sig_fw = allowable_stress_proxy(
        sigma_oper_MPa=float(getattr(inp, "sigma_fw_oper_MPa", float("nan"))),
        dpa_total=float(dmg.get("fw_dpa_total_at_years", dmg.get("fw_dpa_per_year", 0.0))),
        T_C=float(getattr(inp, "T_fw_oper_C", float("nan"))),
        mat=fw_mat,
        prefix="fw",
    )
    sig_bl = allowable_stress_proxy(
        sigma_oper_MPa=float(getattr(inp, "sigma_blanket_oper_MPa", float("nan"))),
        dpa_total=float(dmg.get("blanket_dpa_total_at_years", dmg.get("blanket_dpa_per_year", 0.0))),
        T_C=float(getattr(inp, "T_blanket_oper_C", float("nan"))),
        mat=bl_mat,
        prefix="blanket",
    )

    # TBR proxy v2
    tbr = tbr_proxy_v2(
        t_blanket_m=float(getattr(inp, "t_blanket_m", 0.0)),
        blanket_coverage=float(getattr(inp, "blanket_coverage", 0.80)),
        li6_enrichment=float(getattr(inp, "li6_enrichment", 0.30)),
        port_fraction=float(getattr(inp, "port_fraction", 0.08)),
        blanket_type=str(getattr(inp, "blanket_type", getattr(inp, "blanket_material", "LiPb"))),
        multiplier_material=str(getattr(inp, "multiplier_material", "None")),
        neutron_attenuation_fast=float(att["neutron_attenuation_fast"]),
        TBR_min=float(getattr(inp, "TBR_min", 1.05)),
    )


    # (v321.0) Validity-domain check (screening; does not alter TBR value)
    dom = _tbr_domain_check_v3(
        t_blanket_m=float(getattr(inp, 't_blanket_m', 0.0)),
        blanket_coverage=float(getattr(inp, 'blanket_coverage', 0.80)),
    )
    # Collect outputs
    out2: Dict[str, float] = {}
    out2.update(att)
    out2.update(heat)
    out2.update(dmg)
    out2.update(tw_fw)
    out2.update(tw_bl)
    out2.update(sig_fw)
    out2.update(sig_bl)

    out2["TBR"] = float(tbr.TBR)
    out2["TBR_min"] = float(tbr.TBR_min)
    out2["TBR_margin"] = float(tbr.margin)
    out2["TBR_validity"] = 0.0 if tbr.validity == "proxy" else 1.0  # numeric flag for plotting

    # Domain flags (tight screening validity domain for proxy)
    out2.update(dom)

    # Forward enforcement policy knobs for constraints/governance
    out2['neutronics_domain_enforce'] = 1.0 if bool(getattr(inp, 'neutronics_domain_enforce', False)) else 0.0
    out2['materials_domain_enforce'] = 1.0 if bool(getattr(inp, 'materials_domain_enforce', False)) else 0.0

    # Input caps (forwarded for constraints display)
    out2["P_nuc_total_max_MW"] = float(getattr(inp, "P_nuc_total_max_MW", float("nan")))
    out2["P_nuc_tf_max_MW"] = float(getattr(inp, "P_nuc_tf_max_MW", float("nan")))
    out2["P_nuc_pf_max_MW"] = float(getattr(inp, "P_nuc_pf_max_MW", float("nan")))
    out2["P_nuc_cryo_max_kW"] = float(getattr(inp, "P_nuc_cryo_max_kW", float("nan")))

    out2["fw_lifetime_min_yr"] = float(getattr(inp, "fw_lifetime_min_yr", float("nan")))
    out2["blanket_lifetime_min_yr"] = float(getattr(inp, "blanket_lifetime_min_yr", float("nan")))
    out2["fw_He_total_limit_appm"] = float(getattr(inp, "fw_He_total_limit_appm", float("nan")))
    out2["blanket_He_total_limit_appm"] = float(getattr(inp, "blanket_He_total_limit_appm", float("nan")))

    out2["fw_T_enforce"] = float(getattr(inp, "fw_T_enforce", 0.0))
    out2["blanket_T_enforce"] = float(getattr(inp, "blanket_T_enforce", 0.0))

    # v321: domain enforcement flags (forwarded for constraints/governance)
    out2["neutronics_domain_enforce"] = float(1.0 if bool(getattr(inp, "neutronics_domain_enforce", False)) else 0.0)
    out2["materials_domain_enforce"] = float(1.0 if bool(getattr(inp, "materials_domain_enforce", False)) else 0.0)

    return out2
