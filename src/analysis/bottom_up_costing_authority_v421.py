from __future__ import annotations

"""Bottom-up modular costing authority v421 (Independence Phase 2.5).

Purpose
-------
MATCH-as-overlay replacement for the *role* of PROCESS cost-models: a modular,
account-by-account bottom-up CAPEX ledger with explicit drivers, unit rates,
units, and PROXY provenance. This is deliberately **not** a port of the 1990
Generomak / PROCESS cost accounts — every coefficient is a transparent
in-repo screening proxy, and the ledger is honest about that.

Why this overlay exists
-----------------------
Prior SHAMS CAPEX figures are either single-formula proxies (legacy
``CAPEX_proxy_MUSD``), a component overlay (v356), or industrial-depth
envelopes (v388, inside ``economics/cost.py``). None presents a modular
direct/indirect account structure a reviewer can audit line by line
(driver → unit rate → account → subtotal → contingency → total). v421 adds
that structure as a versioned overlay:

- direct accounts driven by already-computed outputs (masses, powers,
  throughputs) with recorded per-account provenance,
- fraction-based balance accounts (buildings, remote handling, I&C),
- indirect engineering/management and contingency layers,
- bookkeeping identity checks plus informational cross-checks against the
  frozen legacy/v356/v388/v420 CAPEX bases (never edited),
- optional LCOE restatement on the v420 availability chain basis so cost and
  availability honesty stay coupled.

Hard laws
---------
- Algebraic, single-pass, deterministic. No solvers, no iteration.
- Does **not** mutate L0 truth equations; governance overlay only.
- Reads already-computed outputs from ``hot_ion_point``; empty patch when OFF.
- Screening / proxy tier — not a bankable plant cost model.
- **Not** 1990 Generomak: unit rates are transparent in-repo proxies below.
- No invented PROCESS MFILE reference numbers.
- COE / LCOE display must respect ``plant_kpi_honesty.v1`` watermark.

Account structure (all CAPEX in MUSD)
-------------------------------------
Direct (driver × unit rate):
  magnets                    magnet mass [kg] × USD/kg × field-bin multiplier
  blanket_first_wall         blanket mass [kg] × USD/kg
  divertor                   fraction of blanket account × q_div multiplier
  vacuum_vessel              vessel mass [kg] × USD/kg
  cryostat_cryoplant         P_cryo@20K [MW] × MUSD/MW
  heating_current_drive      installed aux power [MW] × MUSD/MW
  tritium_plant_fuel_cycle   T burn [kg/day] × MUSD/(kg/day)
  power_conversion_bop       P_thermal [MW] × MUSD/MWth
Direct (fraction of equipment subtotal):
  buildings_site, remote_handling, instrumentation_control
Indirect:
  engineering_management     fraction of direct subtotal
  contingency                fraction of (direct + engineering)
Total overnight CAPEX = direct + indirect.

Mass drivers prefer stamped v388 proxies when that overlay is ON; otherwise
v421 computes its own documented geometry mass proxies (torus surface area
× thickness × density) and records the source.

Author
------
© 2026 Afshin Arjhangmehr
"""

import math
from typing import Any, Dict, List, Optional, Tuple

AUTHORITY_ID = "bottom_up_costing_authority_v421"
OVERLAY_VERSION = "v421.0.0"
SCREENING_TIER = "proxy"

# Default relative tolerance for bookkeeping identity checks.
_DEFAULT_REL_TOL = 1e-9
# Relative tolerance for informational cross-ledger comparisons.
_CROSS_LEDGER_REL_TOL = 1e-6

# ---------------------------------------------------------------------------
# Transparent in-repo unit rates and fractions (screening proxies).
# Values chosen consistent with the v388 industrial-depth envelopes so the
# two ledgers cross-check; they are NOT Generomak accounts and NOT calibrated
# to any PROCESS MFILE. Units are embedded in every key.
# ---------------------------------------------------------------------------
DEFAULT_UNIT_RATES: Dict[str, float] = {
    "magnet_USD_per_kg": 220.0,
    "blanket_USD_per_kg": 75.0,
    "vacuum_vessel_USD_per_kg": 18.0,
    "cryoplant_MUSD_per_MW20K": 25.0,
    "heating_cd_MUSD_per_MW_installed": 4.0,
    "fuel_cycle_MUSD_per_kg_day": 55.0,
    "bop_MUSD_per_MWth": 0.45,
}

DEFAULT_FRACTIONS: Dict[str, float] = {
    "divertor_frac_of_blanket": 0.12,
    "buildings_site_frac_of_equipment": 0.20,
    "remote_handling_frac_of_equipment": 0.08,
    "instrumentation_control_frac_of_equipment": 0.05,
    "engineering_management_frac_of_direct": 0.12,
    "contingency_frac": 0.15,
}

# Field-bin multiplier on the magnet account (peak field drives conductor
# grade / structure mass in real plants; screening steps only).
_FIELD_BINS_T: Tuple[Tuple[float, float, str], ...] = (
    (12.0, 1.00, "LOW (<12 T)"),
    (16.0, 1.25, "MID (12–16 T)"),
    (float("inf"), 1.60, "HIGH (>16 T)"),
)

# q_div multiplier on the divertor account (high heat flux → more exotic PFCs).
_QDIV_LOW_MW_M2 = 7.0
_QDIV_HIGH_MW_M2 = 15.0
_QDIV_MULT_LOW = 0.90
_QDIV_MULT_HIGH = 1.50

# Geometry mass-proxy densities/thicknesses (used only when v388 masses are
# not stamped; documented fallbacks, same basis as the v388 envelopes).
_RHO_MAGNET_KG_M3 = 7000.0
_RHO_STRUCT_KG_M3 = 8000.0
_T_COIL_DEFAULT_M = 0.5
_T_VV_DEFAULT_M = 0.06


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else float(default)
    except (TypeError, ValueError):
        return float(default)


def _finite(x: float) -> bool:
    return x == x and math.isfinite(x)


def _rel_check(
    name: str,
    left: float,
    right: float,
    *,
    units: str,
    rel_tol: float,
    informational: bool = False,
    note: str = "",
) -> Dict[str, Any]:
    """Relative-residual consistency record (v419/v420-style)."""
    ok = False
    resid = float("nan")
    if _finite(left) and _finite(right):
        scale = max(abs(left), abs(right), 1e-12)
        resid = (left - right) / scale
        ok = abs(resid) <= max(rel_tol, 0.0)
    elif not _finite(left) and not _finite(right):
        ok = True
        resid = 0.0
    rec = {
        "name": name,
        "left": float(left) if _finite(left) else float("nan"),
        "right": float(right) if _finite(right) else float("nan"),
        "rel_residual": float(resid) if _finite(resid) else float("nan"),
        "rel_tol": float(rel_tol),
        "ok": bool(ok),
        "units": units,
    }
    if informational:
        rec["informational"] = True
    if note:
        rec["note"] = note
    return rec


def _torus_surface_area_m2(R0_m: float, a_m: float, kappa: float) -> float:
    """Torus surface-area proxy 4·pi^2·R0·a·kappa [m^2] (screening geometry)."""
    return 4.0 * math.pi**2 * max(R0_m, 0.1) * max(a_m, 0.05) * max(kappa, 1.0)


def _field_bin(B_peak_T: float) -> Tuple[float, str]:
    if not _finite(B_peak_T):
        return 1.25, "MID (unknown B_peak)"
    for hi, mult, label in _FIELD_BINS_T:
        if B_peak_T < hi:
            return mult, label
    return 1.60, "HIGH (>16 T)"


def _qdiv_multiplier(q_div_MW_m2: float) -> float:
    if not _finite(q_div_MW_m2):
        return 1.0
    if q_div_MW_m2 > _QDIV_HIGH_MW_M2:
        return _QDIV_MULT_HIGH
    if q_div_MW_m2 < _QDIV_LOW_MW_M2:
        return _QDIV_MULT_LOW
    return 1.0


def _mass_drivers(inp: Any, out: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve mass drivers [kg] with recorded provenance.

    Prefers stamped v388 magnet mass; otherwise computes documented geometry
    proxies from inputs/outputs (torus area × thickness × density).
    """
    R0 = _f(getattr(inp, "R0_m", float("nan")), _f(out.get("R0_m")))
    a = _f(getattr(inp, "a_m", float("nan")), _f(out.get("a_m")))
    kappa = _f(getattr(inp, "kappa", 1.0), 1.0)
    area = _torus_surface_area_m2(R0, a, kappa) if _finite(R0) and _finite(a) else float("nan")

    magnet_mass = _f(out.get("magnet_mass_proxy_v388_kg"))
    magnet_src = "magnet_mass_proxy_v388_kg"
    if not _finite(magnet_mass):
        t_coil = _f(getattr(inp, "t_coil_proxy_m", _T_COIL_DEFAULT_M), _T_COIL_DEFAULT_M)
        magnet_mass = (
            area * max(t_coil, 0.1) * _RHO_MAGNET_KG_M3 if _finite(area) else float("nan")
        )
        magnet_src = "geometry_proxy(area x t_coil x rho_magnet)"

    t_blanket = _f(getattr(inp, "t_shield_m", float("nan")), _f(out.get("t_shield_m"), 0.7))
    if not _finite(t_blanket):
        t_blanket = 0.7
    blanket_mass = (
        area * max(t_blanket, 0.01) * _RHO_STRUCT_KG_M3 if _finite(area) else float("nan")
    )
    vv_mass = area * _T_VV_DEFAULT_M * _RHO_STRUCT_KG_M3 if _finite(area) else float("nan")

    return {
        "surface_area_m2": area,
        "magnet_mass_kg": magnet_mass,
        "magnet_mass_source": magnet_src,
        "blanket_mass_kg": blanket_mass,
        # t_shield_m is used as the blanket/shield stack thickness proxy —
        # SHAMS has no separate blanket-thickness input at screening tier.
        "blanket_mass_source": "geometry_proxy(area x t_shield_m-as-blanket-stack x rho_struct)",
        "vv_mass_kg": vv_mass,
        "vv_mass_source": "geometry_proxy(area x t_vv x rho_struct)",
    }


def compute(inp: Any, out: Dict[str, Any]) -> Dict[str, Any]:
    rel_tol = _f(getattr(inp, "costing_consistency_tol_v421", float("nan")))
    if not _finite(rel_tol) or rel_tol < 0.0:
        rel_tol = _DEFAULT_REL_TOL

    rates = dict(DEFAULT_UNIT_RATES)
    fracs = dict(DEFAULT_FRACTIONS)

    # --- 1. Drivers -------------------------------------------------------
    masses = _mass_drivers(inp, out)
    B_peak = _f(out.get("B_peak_T"), _f(getattr(inp, "Bt_T", float("nan"))))
    field_mult, field_bin_label = _field_bin(B_peak)
    q_div = _f(out.get("q_div_MW_m2"))
    qdiv_mult = _qdiv_multiplier(q_div)

    P_cryo = _f(getattr(inp, "P_cryo_20K_MW", 0.0), 0.0)
    P_aux = _f(getattr(inp, "Paux_MW", float("nan")), _f(out.get("Paux_MW"), 0.0))
    # NaN propagates to the recorded driver_value (cost clamps to 0 and the
    # ledger row is flagged as a screening gap, not a certified zero cost).
    Pth = _f(out.get("Pth_total_MW"))
    T_burn = _f(out.get("T_burn_kg_per_day"))

    def _acct(driver: float, rate: float) -> float:
        if not _finite(driver):
            return 0.0
        return max(driver, 0.0) * max(rate, 0.0)

    # --- 2. Equipment accounts [MUSD] --------------------------------------
    acct_magnets = (
        _acct(masses["magnet_mass_kg"], rates["magnet_USD_per_kg"]) * field_mult / 1e6
    )
    acct_blanket = _acct(masses["blanket_mass_kg"], rates["blanket_USD_per_kg"]) / 1e6
    acct_divertor = acct_blanket * fracs["divertor_frac_of_blanket"] * qdiv_mult
    acct_vv = _acct(masses["vv_mass_kg"], rates["vacuum_vessel_USD_per_kg"]) / 1e6
    acct_cryo = _acct(P_cryo, rates["cryoplant_MUSD_per_MW20K"])
    acct_hcd = _acct(P_aux, rates["heating_cd_MUSD_per_MW_installed"])
    acct_fuel = _acct(T_burn, rates["fuel_cycle_MUSD_per_kg_day"])
    acct_bop = _acct(Pth, rates["bop_MUSD_per_MWth"])

    equipment_subtotal = (
        acct_magnets
        + acct_blanket
        + acct_divertor
        + acct_vv
        + acct_cryo
        + acct_hcd
        + acct_fuel
        + acct_bop
    )

    # --- 3. Fraction-based direct accounts [MUSD] --------------------------
    acct_buildings = equipment_subtotal * fracs["buildings_site_frac_of_equipment"]
    acct_remote = equipment_subtotal * fracs["remote_handling_frac_of_equipment"]
    acct_ic = equipment_subtotal * fracs["instrumentation_control_frac_of_equipment"]

    direct_subtotal = equipment_subtotal + acct_buildings + acct_remote + acct_ic

    # --- 4. Indirect accounts [MUSD] ----------------------------------------
    acct_engineering = direct_subtotal * fracs["engineering_management_frac_of_direct"]
    acct_contingency = (direct_subtotal + acct_engineering) * fracs["contingency_frac"]
    indirect_subtotal = acct_engineering + acct_contingency

    capex_total = direct_subtotal + indirect_subtotal

    # --- 5. Account ledger (reviewer-auditable rows) ------------------------
    def _row(
        account: str,
        cost_MUSD: float,
        *,
        driver: str,
        driver_value: float,
        driver_units: str,
        rate: str,
        kind: str,
        note: str = "",
    ) -> Dict[str, Any]:
        return {
            "account": account,
            "cost_MUSD": float(cost_MUSD),
            "driver": driver,
            "driver_value": float(driver_value) if _finite(driver_value) else float("nan"),
            "driver_units": driver_units,
            "rate": rate,
            "kind": kind,
            "note": note,
        }

    ledger: List[Dict[str, Any]] = [
        _row(
            "magnets",
            acct_magnets,
            driver="magnet mass",
            driver_value=masses["magnet_mass_kg"],
            driver_units="kg",
            rate=(
                f"{rates['magnet_USD_per_kg']:g} USD/kg × {field_mult:g} "
                f"(field bin {field_bin_label})"
            ),
            kind="equipment",
            note=f"mass source: {masses['magnet_mass_source']}",
        ),
        _row(
            "blanket_first_wall",
            acct_blanket,
            driver="blanket mass",
            driver_value=masses["blanket_mass_kg"],
            driver_units="kg",
            rate=f"{rates['blanket_USD_per_kg']:g} USD/kg",
            kind="equipment",
            note=f"mass source: {masses['blanket_mass_source']}",
        ),
        _row(
            "divertor",
            acct_divertor,
            driver="fraction of blanket account",
            driver_value=fracs["divertor_frac_of_blanket"],
            driver_units="-",
            rate=f"× {qdiv_mult:g} (q_div multiplier)",
            kind="equipment",
            note=(
                (f"q_div = {q_div:.3g} MW/m^2" if _finite(q_div) else "q_div not stamped")
                + (
                    "; parent blanket driver not stamped — account contributes"
                    " 0 MUSD (screening gap, not a cost claim)"
                    if not _finite(masses["blanket_mass_kg"])
                    else ""
                )
            ),
        ),
        _row(
            "vacuum_vessel",
            acct_vv,
            driver="vessel mass",
            driver_value=masses["vv_mass_kg"],
            driver_units="kg",
            rate=f"{rates['vacuum_vessel_USD_per_kg']:g} USD/kg",
            kind="equipment",
            note=f"mass source: {masses['vv_mass_source']}",
        ),
        _row(
            "cryostat_cryoplant",
            acct_cryo,
            driver="cryo plant load @20K",
            driver_value=P_cryo,
            driver_units="MW",
            rate=f"{rates['cryoplant_MUSD_per_MW20K']:g} MUSD/MW",
            kind="equipment",
        ),
        _row(
            "heating_current_drive",
            acct_hcd,
            driver="installed aux heating power",
            driver_value=P_aux,
            driver_units="MW",
            rate=f"{rates['heating_cd_MUSD_per_MW_installed']:g} MUSD/MW",
            kind="equipment",
        ),
        _row(
            "tritium_plant_fuel_cycle",
            acct_fuel,
            driver="tritium burn throughput",
            driver_value=T_burn,
            driver_units="kg/day",
            rate=f"{rates['fuel_cycle_MUSD_per_kg_day']:g} MUSD/(kg/day)",
            kind="equipment",
        ),
        _row(
            "power_conversion_bop",
            acct_bop,
            driver="thermal power",
            driver_value=Pth,
            driver_units="MW(th)",
            rate=f"{rates['bop_MUSD_per_MWth']:g} MUSD/MWth",
            kind="equipment",
        ),
        _row(
            "buildings_site",
            acct_buildings,
            driver="equipment subtotal",
            driver_value=equipment_subtotal,
            driver_units="MUSD",
            rate=f"× {fracs['buildings_site_frac_of_equipment']:g}",
            kind="direct_fraction",
        ),
        _row(
            "remote_handling",
            acct_remote,
            driver="equipment subtotal",
            driver_value=equipment_subtotal,
            driver_units="MUSD",
            rate=f"× {fracs['remote_handling_frac_of_equipment']:g}",
            kind="direct_fraction",
        ),
        _row(
            "instrumentation_control",
            acct_ic,
            driver="equipment subtotal",
            driver_value=equipment_subtotal,
            driver_units="MUSD",
            rate=f"× {fracs['instrumentation_control_frac_of_equipment']:g}",
            kind="direct_fraction",
        ),
        _row(
            "engineering_management",
            acct_engineering,
            driver="direct subtotal",
            driver_value=direct_subtotal,
            driver_units="MUSD",
            rate=f"× {fracs['engineering_management_frac_of_direct']:g}",
            kind="indirect",
        ),
        _row(
            "contingency",
            acct_contingency,
            driver="direct + engineering",
            driver_value=direct_subtotal + acct_engineering,
            driver_units="MUSD",
            rate=f"× {fracs['contingency_frac']:g}",
            kind="indirect",
        ),
    ]

    # A non-finite driver contributes 0 MUSD (screening); flag it so the
    # ledger cannot be misread as a certified "free" account.
    for row in ledger:
        dv = row.get("driver_value", float("nan"))
        if isinstance(dv, float) and not _finite(dv):
            extra = "driver not stamped — account contributes 0 MUSD (screening gap, not a cost claim)"
            row["note"] = f"{row['note']}; {extra}" if row.get("note") else extra

    dominant = max(ledger, key=lambda r: r["cost_MUSD"]) if ledger else None
    dominant_account = str(dominant["account"]) if dominant else "none"
    dominant_frac = (
        float(dominant["cost_MUSD"]) / capex_total
        if dominant and capex_total > 0.0
        else float("nan")
    )

    # --- 6. Bookkeeping identity checks -------------------------------------
    checks: List[Dict[str, Any]] = []
    checks.append(
        _rel_check(
            "direct_sum",
            direct_subtotal,
            sum(r["cost_MUSD"] for r in ledger if r["kind"] in ("equipment", "direct_fraction")),
            units="MUSD",
            rel_tol=max(rel_tol, 1e-12),
            note="direct subtotal = sum of equipment + direct-fraction accounts",
        )
    )
    checks.append(
        _rel_check(
            "total_identity",
            capex_total,
            sum(r["cost_MUSD"] for r in ledger),
            units="MUSD",
            rel_tol=max(rel_tol, 1e-12),
            note="total CAPEX = sum of all accounts",
        )
    )
    checks.append(
        _rel_check(
            "accounts_nonnegative",
            1.0 if all(r["cost_MUSD"] >= 0.0 for r in ledger) else 0.0,
            1.0,
            units="-",
            rel_tol=0.0,
            note="every account >= 0",
        )
    )

    # Informational cross-ledger comparisons (frozen CAPEX bases untouched).
    for key, note in (
        ("CAPEX_industrial_v388_MUSD", "industrial-depth CAPEX envelope vs bottom-up ledger"),
        ("CAPEX_component_proxy_MUSD", "component CAPEX proxy vs bottom-up ledger"),
        ("CAPEX_proxy_MUSD", "legacy CAPEX proxy vs bottom-up ledger"),
        ("avail_v420_CAPEX_MUSD", "availability-coupling CAPEX basis vs bottom-up ledger"),
    ):
        stamped = _f(out.get(key))
        if _finite(stamped):
            checks.append(
                _rel_check(
                    f"cross_ledger_{key}",
                    capex_total,
                    stamped,
                    units="MUSD",
                    rel_tol=_CROSS_LEDGER_REL_TOL,
                    informational=True,
                    note=note,
                )
            )

    consistency_ok = all(bool(c.get("ok")) for c in checks if not c.get("informational"))

    # --- 7. LCOE restatement on the v420 availability chain basis ----------
    # Reuses stamped v420 energy / OPEX / replacement (no re-derivation) so
    # the bottom-up CAPEX and the availability chain share one honesty story.
    lcoe = float("nan")
    lcoe_basis = "unavailable (enable availability-OPEX-LCOE coupling overlay)"
    if bool(out.get("avail_v420_enabled", False)):
        E_net = _f(out.get("avail_v420_E_net_MWh_per_y"))
        opex = _f(out.get("avail_v420_OPEX_total_MUSD_per_y"), 0.0)
        repl = _f(out.get("avail_v420_replacement_MUSD_per_y"), 0.0)
        fcr = _f(out.get("avail_v420_fixed_charge_rate"), _f(getattr(inp, "fixed_charge_rate", 0.10), 0.10))
        if _finite(E_net) and E_net > 1e-9:
            lcoe = (fcr * capex_total + repl + opex) * 1e6 / E_net
            lcoe_basis = (
                "availability-coupling chain (same energy/OPEX/replacement basis; "
                "CAPEX replaced by bottom-up ledger total)"
            )
        else:
            lcoe_basis = "availability chain has no positive net energy (watermarked point)"

    system_tier = "comfortable"
    if not consistency_ok:
        system_tier = "deficit"
    elif _finite(dominant_frac) and dominant_frac > 0.5:
        system_tier = "near_limit"

    # Optional caps (NaN disables; echoed for the constraint layer).
    capex_max = _f(getattr(inp, "capex_total_max_MUSD_v421", float("nan")))
    lcoe_max = _f(getattr(inp, "lcoe_bottom_up_max_USD_per_MWh_v421", float("nan")))

    narrative = (
        f"Bottom-up CAPEX={capex_total:.4g} MUSD "
        f"(direct={direct_subtotal:.4g}, indirect={indirect_subtotal:.4g}; "
        f"dominant account={dominant_account}"
        + (f" @ {dominant_frac:.0%}" if _finite(dominant_frac) else "")
        + f"); consistency_ok={consistency_ok}; "
        f"LCOE basis: {lcoe_basis}; PROXY modular account ledger "
        f"(transparent in-repo rates — not 1990 Generomak, no PROCESS MFILE parity)"
    )

    patch: Dict[str, Any] = {
        "costing_v421_enabled": True,
        "costing_v421_authority_id": AUTHORITY_ID,
        "costing_v421_overlay_version": OVERLAY_VERSION,
        "costing_v421_screening_tier": SCREENING_TIER,
        "costing_v421_extends": (
            "legacy cost proxies + component CAPEX v356 + industrial depth v388 "
            "+ availability coupling v420 (frozen; cross-checked)"
        ),
        "costing_v421_provenance": (
            "modular bottom-up CAPEX account ledger; every account = explicit "
            "driver x transparent in-repo unit rate (PROXY screening tier, not "
            "1990 Generomak, no invented PROCESS MFILE numbers); COE/LCOE "
            "display must use plant_kpi_honesty.v1 watermark"
        ),
        "costing_v421_requires_kpi_honesty_watermark": True,
        "costing_v421_kpi_honesty_schema": "plant_kpi_honesty.v1",
        # Ledger + subtotals
        "costing_v421_account_ledger": ledger,
        "costing_v421_n_accounts": len(ledger),
        "costing_v421_equipment_subtotal_MUSD": float(equipment_subtotal),
        "costing_v421_direct_subtotal_MUSD": float(direct_subtotal),
        "costing_v421_indirect_subtotal_MUSD": float(indirect_subtotal),
        "costing_v421_CAPEX_total_MUSD": float(capex_total),
        "costing_v421_dominant_account": dominant_account,
        "costing_v421_dominant_account_frac": (
            float(dominant_frac) if _finite(dominant_frac) else float("nan")
        ),
        # Per-account mirrors for tables/exports
        "costing_v421_magnets_MUSD": float(acct_magnets),
        "costing_v421_blanket_first_wall_MUSD": float(acct_blanket),
        "costing_v421_divertor_MUSD": float(acct_divertor),
        "costing_v421_vacuum_vessel_MUSD": float(acct_vv),
        "costing_v421_cryostat_cryoplant_MUSD": float(acct_cryo),
        "costing_v421_heating_current_drive_MUSD": float(acct_hcd),
        "costing_v421_tritium_plant_fuel_cycle_MUSD": float(acct_fuel),
        "costing_v421_power_conversion_bop_MUSD": float(acct_bop),
        "costing_v421_buildings_site_MUSD": float(acct_buildings),
        "costing_v421_remote_handling_MUSD": float(acct_remote),
        "costing_v421_instrumentation_control_MUSD": float(acct_ic),
        "costing_v421_engineering_management_MUSD": float(acct_engineering),
        "costing_v421_contingency_MUSD": float(acct_contingency),
        # Drivers / multipliers traceability
        "costing_v421_field_bin": field_bin_label,
        "costing_v421_field_multiplier": float(field_mult),
        "costing_v421_qdiv_multiplier": float(qdiv_mult),
        "costing_v421_magnet_mass_source": str(masses["magnet_mass_source"]),
        "costing_v421_unit_rates": dict(rates),
        "costing_v421_fractions": dict(fracs),
        # LCOE restatement (watermarked display)
        "costing_v421_LCOE_USD_per_MWh": float(lcoe) if _finite(lcoe) else float("nan"),
        "costing_v421_LCOE_basis": lcoe_basis,
        # Consistency
        "costing_v421_consistency_ok": bool(consistency_ok),
        "costing_v421_consistency_rel_tol": float(rel_tol),
        "costing_v421_consistency_checks": checks,
        "costing_v421_system_tier": str(system_tier),
        # Optional caps echoed for constraint layer (NaN disables)
        "capex_total_max_MUSD_v421": float(capex_max),
        "lcoe_bottom_up_max_USD_per_MWh_v421": float(lcoe_max),
        "costing_v421_units": {
            "accounts": "MUSD",
            "capex": "MUSD",
            "lcoe": "USD/MWh",
            "masses": "kg",
            "powers": "MW",
            "throughput": "kg/day",
        },
        "costing_v421_narrative": narrative,
    }
    return patch


def evaluate_bottom_up_costing_authority_v421(
    out: Dict[str, Any], inp: Any
) -> Dict[str, Any]:
    """Deterministic bottom-up modular costing overlay. No re-solve.

    When disabled, returns ``{}`` so default evaluator outputs (and goldens)
    are unchanged — L0 numeric truth and artifact key sets stay frozen.
    """
    enabled = bool(getattr(inp, "include_bottom_up_costing_authority_v421", False))
    if not enabled:
        return {}
    patch = compute(inp, out)
    patch["include_bottom_up_costing_authority_v421"] = True
    return patch


def costing_account_rows(out: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """UI helper: account ledger rows for tables (None when overlay off)."""
    if not bool(out.get("costing_v421_enabled", False)):
        return None
    ledger = out.get("costing_v421_account_ledger")
    if not isinstance(ledger, list):
        return None
    return [dict(r) for r in ledger if isinstance(r, dict)]
