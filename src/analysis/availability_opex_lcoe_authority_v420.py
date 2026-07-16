from __future__ import annotations

"""Availability → OPEX / LCOE coupling authority v420 (Independence Phase 2.4).

Purpose
-------
MATCH-as-overlay deepening of PROCESS-class *plant-availability* coverage:
one explicit availability chain feeding annual energy, annual OPEX, and LCOE
consistently — with provenance for which availability ledger was used,
conservation/consistency residual checks across the ledgers, and PROXY
labels everywhere. No availability or economics iteration enters L0.

Why this overlay exists
-----------------------
Prior ledgers each picked their own availability basis:

- ``annual_net_MWh``            uses ``availability_model`` (incl. ELM v409 coupling)
- ``net_electric_MWh_per_year_v359 / _v368`` use their own ledger availabilities
- ``OPEX_v360_*`` electricity terms use the legacy hours basis even when the
  v360 LCOE energy denominator prefers v368/v359 energy — an hours mismatch.

v420 selects ONE availability (explicit precedence + provenance), derives
operating hours once, and computes energy, OPEX (via the centralized
``economics/opex_coupling.py`` formulas), and LCOE from that same basis.
Existing v359/v360/v368 stamped outputs are untouched (frozen behavior);
v420 cross-checks against them and reports residuals instead of editing them.

Hard laws
---------
- Algebraic, single-pass, deterministic. No solvers, no iteration, no smoothing.
- Does **not** mutate L0 truth equations; governance overlay only.
- Reads already-computed outputs from ``hot_ion_point``; empty patch when OFF.
- Screening / proxy tier — not a bankable plant cost model, not a RAMI simulator.
- No invented PROCESS MFILE reference numbers.
- LCOE / Pe_net display must respect ``plant_kpi_honesty.v1`` watermark.
- Not 1990 Generomak: cost coefficients are transparent in-repo proxies.

Availability precedence (first finite wins; provenance recorded)
----------------------------------------------------------------
1. ``availability_v368``   — maintenance-scheduling authority (most explicit)
2. ``availability_v359``   — availability & replacement ledger
3. ``availability_cert_v391`` — reliability envelope authority
4. ``availability_model``  — L0 availability proxy (ELM v409-coupled when enabled)
5. ``inp.availability``    — user input fallback (default 0.70)

Coupling structure
------------------
A [-] × duty [-] → hours [h/y] = 8760 × A × duty
E_net [MWh/y]    = max(Pe_net, 0) × hours
OPEX  [MUSD/y]   = fixed + electric(recirc, cryo, CD @ same hours) + tritium(@ A·duty) + maintenance
LCOE  [USD/MWh]  = (FCR × CAPEX + replacement_rate + OPEX) × 1e6 / E_net
  with CAPEX precedence: v356 component proxy → legacy CAPEX proxy
  and replacement-rate precedence: v384 → v368 → v359 → 0.

Author
------
© 2026 Afshin Arjhangmehr
"""

import math
from typing import Any, Dict, List, Optional, Tuple

try:
    from economics.opex_coupling import annual_opex_components_MUSD
except ImportError:  # pragma: no cover - package-relative fallback
    from ..economics.opex_coupling import annual_opex_components_MUSD


AUTHORITY_ID = "availability_opex_lcoe_authority_v420"
OVERLAY_VERSION = "v420.0.0"
SCREENING_TIER = "proxy"

# Default relative tolerance for bookkeeping consistency checks.
_DEFAULT_REL_TOL = 1e-9
# Relative tolerance for informational cross-ledger comparisons.
_CROSS_LEDGER_REL_TOL = 1e-6


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
    """Relative-residual consistency record (v419-style, dimensionless residual)."""
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


def _select_availability(out: Dict[str, Any], inp: Any) -> Tuple[float, str]:
    """Pick the authoritative availability with explicit provenance."""
    candidates: Tuple[Tuple[str, float], ...] = (
        ("availability_v368", _f(out.get("availability_v368"))),
        ("availability_v359", _f(out.get("availability_v359"))),
        ("availability_cert_v391", _f(out.get("availability_cert_v391"))),
        ("availability_model", _f(out.get("availability_model"))),
    )
    for source, val in candidates:
        if _finite(val):
            return min(max(val, 0.0), 1.0), source
    fallback = _f(getattr(inp, "availability", 0.70), 0.70)
    return min(max(fallback, 0.0), 1.0), "inp.availability"


def compute(inp: Any, out: Dict[str, Any]) -> Dict[str, Any]:
    rel_tol = _f(getattr(inp, "avail_opex_lcoe_consistency_tol_v420", float("nan")))
    if not _finite(rel_tol) or rel_tol < 0.0:
        rel_tol = _DEFAULT_REL_TOL

    # --- 1. Availability chain (dimensionless) ----------------------------
    A, A_source = _select_availability(out, inp)
    elm_coupled = bool(_f(out.get("elm_availability_coupled_v409"), 0.0) > 0.5)

    duty = _f(out.get("duty_factor"), 1.0)
    duty = min(max(duty, 0.0), 1.0)

    hours = 8760.0 * A * duty  # [h/y]

    # --- 2. Annual net energy [MWh/y] --------------------------------------
    Pe_net = _f(out.get("P_e_net_MW"))
    E_net_MWh = max(Pe_net, 0.0) * hours if _finite(Pe_net) else float("nan")

    # --- 3. OPEX at the SAME hours basis (centralized formulas) -----------
    opex = annual_opex_components_MUSD(
        inp, out, hours_per_year=hours, availability=A, duty_factor=duty
    )
    opex_total = _f(opex.get("OPEX_total_MUSD_per_y"), 0.0)

    # --- 4. Replacement annual cost rate [MUSD/y] (ledger precedence) -----
    repl_candidates: Tuple[Tuple[str, float], ...] = (
        ("replacement_cost_MUSD_per_year_v384", _f(out.get("replacement_cost_MUSD_per_year_v384"))),
        ("replacement_cost_MUSD_per_year_v368", _f(out.get("replacement_cost_MUSD_per_year_v368"))),
        ("replacement_cost_MUSD_per_year_v359", _f(out.get("replacement_cost_MUSD_per_year_v359"))),
    )
    repl_rate = 0.0
    repl_source = "none"
    for source, val in repl_candidates:
        if _finite(val):
            repl_rate = max(val, 0.0)
            repl_source = source
            break

    # --- 5. CAPEX basis [MUSD] (component proxy preferred) -----------------
    capex_candidates: Tuple[Tuple[str, float], ...] = (
        ("CAPEX_component_proxy_MUSD", _f(out.get("CAPEX_component_proxy_MUSD"))),
        ("CAPEX_proxy_MUSD", _f(out.get("CAPEX_proxy_MUSD"))),
    )
    capex = float("nan")
    capex_source = "none"
    for source, val in capex_candidates:
        if _finite(val):
            capex = max(val, 0.0)
            capex_source = source
            break

    fcr = _f(getattr(inp, "fixed_charge_rate", 0.10), 0.10)
    fcr = min(max(fcr, 0.0), 0.30)

    # --- 6. LCOE [USD/MWh] with decomposition ------------------------------
    lcoe = float("nan")
    lcoe_capex = float("nan")
    lcoe_repl = float("nan")
    lcoe_opex = float("nan")
    if _finite(E_net_MWh) and E_net_MWh > 1e-9 and _finite(capex):
        lcoe_capex = (fcr * capex) * 1e6 / E_net_MWh
        lcoe_repl = repl_rate * 1e6 / E_net_MWh
        lcoe_opex = opex_total * 1e6 / E_net_MWh
        lcoe = lcoe_capex + lcoe_repl + lcoe_opex

    # --- 7. Consistency / conservation checks ------------------------------
    checks: List[Dict[str, Any]] = []

    checks.append(
        _rel_check(
            "energy_identity",
            E_net_MWh,
            max(Pe_net, 0.0) * 8760.0 * A * duty if _finite(Pe_net) else float("nan"),
            units="MWh/y",
            rel_tol=rel_tol,
            note="E_net = max(Pe_net,0) × 8760 × A × duty",
        )
    )
    opex_sum = (
        _f(opex.get("OPEX_fixed_MUSD_per_y"), 0.0)
        + _f(opex.get("OPEX_electric_recirc_MUSD_per_y"), 0.0)
        + _f(opex.get("OPEX_electric_cryo_MUSD_per_y"), 0.0)
        + _f(opex.get("OPEX_electric_cd_MUSD_per_y"), 0.0)
        + _f(opex.get("OPEX_tritium_MUSD_per_y"), 0.0)
        + _f(opex.get("OPEX_maintenance_MUSD_per_y"), 0.0)
    )
    checks.append(
        _rel_check(
            "opex_component_sum",
            opex_total,
            opex_sum,
            units="MUSD/y",
            rel_tol=max(rel_tol, 1e-12),
            note="OPEX_total = Σ components",
        )
    )
    checks.append(
        _rel_check(
            "lcoe_decomposition",
            lcoe,
            (lcoe_capex + lcoe_repl + lcoe_opex)
            if all(_finite(x) for x in (lcoe_capex, lcoe_repl, lcoe_opex))
            else float("nan"),
            units="USD/MWh",
            rel_tol=max(rel_tol, 1e-12),
            note="LCOE = capex + replacement + opex shares",
        )
    )
    # Availability bounded on [0, 1] — expressed as a residual vs its clamp.
    checks.append(
        _rel_check(
            "availability_unit_interval",
            A,
            min(max(A, 0.0), 1.0),
            units="-",
            rel_tol=0.0,
            note="A ∈ [0, 1]",
        )
    )

    # Informational cross-ledger comparisons (frozen ledgers not edited).
    for key, note in (
        (
            "net_electric_MWh_per_year_v368",
            "v368 ledger energy vs v420 (differs when availability source ≠ v368)",
        ),
        (
            "net_electric_MWh_per_year_v359",
            "v359 ledger energy vs v420 (differs when availability source ≠ v359)",
        ),
        (
            "annual_net_MWh",
            "legacy annual energy (availability_model basis) vs v420",
        ),
    ):
        stamped = _f(out.get(key))
        if _finite(stamped):
            checks.append(
                _rel_check(
                    f"cross_ledger_{key}",
                    E_net_MWh,
                    stamped,
                    units="MWh/y",
                    rel_tol=_CROSS_LEDGER_REL_TOL,
                    informational=True,
                    note=note,
                )
            )
    for key, note in (
        ("OPEX_v360_total_MUSD_per_y", "frozen v360 OPEX (legacy hours basis) vs v420"),
        ("LCOE_proxy_v360_USD_per_MWh", "frozen v360 LCOE (mixed hours basis) vs v420"),
    ):
        stamped = _f(out.get(key))
        if _finite(stamped):
            checks.append(
                _rel_check(
                    f"cross_ledger_{key}",
                    opex_total if key.startswith("OPEX") else lcoe,
                    stamped,
                    units="MUSD/y" if key.startswith("OPEX") else "USD/MWh",
                    rel_tol=_CROSS_LEDGER_REL_TOL,
                    informational=True,
                    note=note,
                )
            )

    consistency_ok = all(
        bool(c.get("ok")) for c in checks if not c.get("informational")
    )

    # --- 8. Tiering / dominant OPEX driver ----------------------------------
    opex_drivers = [
        ("fixed", _f(opex.get("OPEX_fixed_MUSD_per_y"), 0.0)),
        ("electric_recirc", _f(opex.get("OPEX_electric_recirc_MUSD_per_y"), 0.0)),
        ("electric_cryo", _f(opex.get("OPEX_electric_cryo_MUSD_per_y"), 0.0)),
        ("electric_cd", _f(opex.get("OPEX_electric_cd_MUSD_per_y"), 0.0)),
        ("tritium", _f(opex.get("OPEX_tritium_MUSD_per_y"), 0.0)),
        ("maintenance", _f(opex.get("OPEX_maintenance_MUSD_per_y"), 0.0)),
    ]
    dominant_opex = max(opex_drivers, key=lambda kv: kv[1])[0] if opex_drivers else "none"

    system_tier = "comfortable"
    if not consistency_ok or (_finite(Pe_net) and Pe_net <= 0.0):
        system_tier = "deficit"
    elif A < 0.5:
        system_tier = "near_limit"

    # Optional caps (NaN disables; echoed for the constraint layer).
    A_min = _f(getattr(inp, "availability_min_v420", float("nan")))
    lcoe_max = _f(getattr(inp, "lcoe_max_USD_per_MWh_v420", float("nan")))
    opex_max = _f(getattr(inp, "opex_max_MUSD_per_y_v420", float("nan")))

    narrative = (
        f"A={A:.4g} ({A_source}); hours={hours:.4g} h/y; "
        f"E_net={E_net_MWh:.4g} MWh/y; OPEX={opex_total:.4g} MUSD/y "
        f"(dominant={dominant_opex}); LCOE={lcoe:.4g} USD/MWh; "
        f"consistency_ok={consistency_ok}; PROXY availability→OPEX→LCOE chain "
        f"(watermark LCOE/Pe_net via plant_kpi_honesty.v1)"
        if _finite(E_net_MWh) and _finite(lcoe)
        else (
            f"A={A:.4g} ({A_source}); hours={hours:.4g} h/y; "
            f"LCOE not computable (missing Pe_net/CAPEX or zero energy); "
            f"consistency_ok={consistency_ok}; PROXY chain"
        )
    )

    patch: Dict[str, Any] = {
        "avail_v420_enabled": True,
        "avail_v420_authority_id": AUTHORITY_ID,
        "avail_v420_overlay_version": OVERLAY_VERSION,
        "avail_v420_screening_tier": SCREENING_TIER,
        "avail_v420_extends": (
            "availability_ledger_v359 + maintenance_scheduling_v368 + "
            "elm_duty_v409 coupling + economics_v360 (frozen; cross-checked)"
        ),
        "avail_v420_provenance": (
            "single availability chain → hours → annual energy → OPEX → LCOE; "
            "PROXY screening economics (transparent in-repo coefficients, not "
            "1990 Generomak, not PROCESS MFILE parity); LCOE/Pe_net display "
            "must use plant_kpi_honesty.v1 watermark"
        ),
        "avail_v420_requires_kpi_honesty_watermark": True,
        "avail_v420_kpi_honesty_schema": "plant_kpi_honesty.v1",
        # Availability chain
        "avail_v420_availability": float(A),
        "avail_v420_availability_source": str(A_source),
        "avail_v420_elm_v409_coupled": bool(elm_coupled),
        "avail_v420_duty_factor": float(duty),
        "avail_v420_hours_per_year_h": float(hours),
        # Energy
        "avail_v420_Pe_net_MW": float(Pe_net) if _finite(Pe_net) else float("nan"),
        "avail_v420_E_net_MWh_per_y": float(E_net_MWh) if _finite(E_net_MWh) else float("nan"),
        # OPEX (availability-coupled; same hours basis)
        "avail_v420_OPEX_total_MUSD_per_y": float(opex_total),
        "avail_v420_OPEX_fixed_MUSD_per_y": opex["OPEX_fixed_MUSD_per_y"],
        "avail_v420_OPEX_electric_recirc_MUSD_per_y": opex["OPEX_electric_recirc_MUSD_per_y"],
        "avail_v420_OPEX_electric_cryo_MUSD_per_y": opex["OPEX_electric_cryo_MUSD_per_y"],
        "avail_v420_OPEX_electric_cd_MUSD_per_y": opex["OPEX_electric_cd_MUSD_per_y"],
        "avail_v420_OPEX_tritium_MUSD_per_y": opex["OPEX_tritium_MUSD_per_y"],
        "avail_v420_OPEX_maintenance_MUSD_per_y": opex["OPEX_maintenance_MUSD_per_y"],
        "avail_v420_dominant_opex_driver": str(dominant_opex),
        # Replacement + CAPEX bases
        "avail_v420_replacement_MUSD_per_y": float(repl_rate),
        "avail_v420_replacement_source": str(repl_source),
        "avail_v420_CAPEX_MUSD": float(capex) if _finite(capex) else float("nan"),
        "avail_v420_CAPEX_source": str(capex_source),
        "avail_v420_fixed_charge_rate": float(fcr),
        # LCOE with decomposition
        "avail_v420_LCOE_USD_per_MWh": float(lcoe) if _finite(lcoe) else float("nan"),
        "avail_v420_LCOE_capex_USD_per_MWh": float(lcoe_capex) if _finite(lcoe_capex) else float("nan"),
        "avail_v420_LCOE_replacement_USD_per_MWh": float(lcoe_repl) if _finite(lcoe_repl) else float("nan"),
        "avail_v420_LCOE_opex_USD_per_MWh": float(lcoe_opex) if _finite(lcoe_opex) else float("nan"),
        # Consistency
        "avail_v420_consistency_ok": bool(consistency_ok),
        "avail_v420_consistency_rel_tol": float(rel_tol),
        "avail_v420_consistency_checks": checks,
        "avail_v420_system_tier": str(system_tier),
        # Optional caps echoed for constraint layer (NaN disables)
        "availability_min_v420": float(A_min),
        "lcoe_max_USD_per_MWh_v420": float(lcoe_max),
        "opex_max_MUSD_per_y_v420": float(opex_max),
        # Traceability of loads/prices used by the centralized OPEX formulas
        "avail_v420_P_recirc_el_used_MW": opex["P_recirc_el_used_MW"],
        "avail_v420_P_cryo_wallplug_used_MW": opex["P_cryo_wallplug_used_MW"],
        "avail_v420_P_cd_wallplug_used_MW": opex["P_cd_wallplug_used_MW"],
        "avail_v420_electricity_price_used_USD_per_MWh": opex["electricity_price_used_USD_per_MWh"],
        "avail_v420_tritium_processing_used_g_per_day": opex["tritium_processing_used_g_per_day"],
        "avail_v420_units": {
            "availability": "dimensionless (fraction of year)",
            "duty_factor": "dimensionless",
            "hours": "h/y",
            "energy": "MWh/y",
            "opex": "MUSD/y",
            "capex": "MUSD",
            "lcoe": "USD/MWh",
            "fixed_charge_rate": "1/y",
        },
        "avail_v420_narrative": narrative,
    }
    return patch


def evaluate_availability_opex_lcoe_authority_v420(
    out: Dict[str, Any], inp: Any
) -> Dict[str, Any]:
    """Deterministic availability→OPEX→LCOE coupling overlay. No re-solve.

    When disabled, returns ``{}`` so default evaluator outputs (and goldens)
    are unchanged — L0 numeric truth and artifact key sets stay frozen.
    """
    enabled = bool(getattr(inp, "include_availability_opex_lcoe_authority_v420", False))
    if not enabled:
        return {}
    patch = compute(inp, out)
    patch["include_availability_opex_lcoe_authority_v420"] = True
    return patch


def availability_lcoe_chain_rows(out: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """UI helper: availability→energy→OPEX→LCOE narrative rows (None when off)."""
    if not bool(out.get("avail_v420_enabled", False)):
        return None
    return [
        {
            "stage": "Availability",
            "value": out.get("avail_v420_availability"),
            "units": "-",
            "provenance": str(out.get("avail_v420_availability_source", "")),
        },
        {
            "stage": "Operating hours",
            "value": out.get("avail_v420_hours_per_year_h"),
            "units": "h/y",
            "provenance": "8760 × A × duty",
        },
        {
            "stage": "Annual net energy",
            "value": out.get("avail_v420_E_net_MWh_per_y"),
            "units": "MWh/y",
            "provenance": "max(Pe_net, 0) × hours (watermarked)",
        },
        {
            "stage": "OPEX",
            "value": out.get("avail_v420_OPEX_total_MUSD_per_y"),
            "units": "MUSD/y",
            "provenance": f"dominant: {out.get('avail_v420_dominant_opex_driver', '-')}",
        },
        {
            "stage": "LCOE",
            "value": out.get("avail_v420_LCOE_USD_per_MWh"),
            "units": "USD/MWh",
            "provenance": (
                f"CAPEX: {out.get('avail_v420_CAPEX_source', '-')}; "
                f"repl: {out.get('avail_v420_replacement_source', '-')}"
            ),
        },
    ]
