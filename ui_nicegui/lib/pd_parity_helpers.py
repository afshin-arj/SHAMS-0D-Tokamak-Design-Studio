"""Point Designer parity data helpers (no Streamlit)."""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ui_nicegui.session import DesignSession

try:
    from constraints.pipeline_diff import build_pipeline_diff_dossier
    from constraints.unified import build_all_constraints
    from constraints.constraints import constraint_is_hard
    from diagnostics.no_solution_atlas import build_no_solution_atlas
    from decision.kpis import headline_kpis
except ImportError:
    from src.constraints.pipeline_diff import build_pipeline_diff_dossier
    from src.constraints.unified import build_all_constraints
    from src.constraints.constraints import constraint_is_hard
    from src.diagnostics.no_solution_atlas import build_no_solution_atlas
    from src.decision.kpis import headline_kpis

from ui.constraint_trace import build_infeasibility_trace


def pipeline_diff_rows(out: Dict[str, Any], *, design_intent: str) -> Dict[str, Any]:
    dossier = build_pipeline_diff_dossier(out, design_intent=design_intent)
    parity = dossier.get("parity") or {}
    return {
        "parity": parity,
        "aligned": bool(parity.get("pipelines_aligned", True)),
        "registry_governance": dossier.get("registry_governance") or [],
        "legacy_governance": dossier.get("legacy_governance") or [],
        "merged_governance": dossier.get("merged_governance") or [],
    }


def no_solution_atlas_summary(out: Dict[str, Any], *, design_intent: str) -> Dict[str, Any]:
    atlas = build_no_solution_atlas(out, design_intent=design_intent)
    mech_map = atlas.get("mechanism_map") or {}
    rows: List[Dict[str, str]] = []
    for mech, names in sorted(mech_map.items()):
        for nm in names:
            rows.append({"mechanism": str(mech), "constraint": str(nm)})
    return {
        "verdict": str(atlas.get("verdict", "UNKNOWN")),
        "dominant_mechanism": str(atlas.get("dominant_mechanism") or "GENERAL"),
        "dominant_constraint": str(atlas.get("dominant_constraint") or "(none)"),
        "mechanism_rows": rows,
    }


def constraint_notebook_rows(out: Dict[str, Any]) -> List[Dict[str, Any]]:
    bundle = build_all_constraints(out)
    rows: List[Dict[str, Any]] = []
    for c in bundle.governance:
        rows.append({
            "name": str(getattr(c, "name", "")),
            "passed": bool(getattr(c, "passed", True)),
            "hard": bool(constraint_is_hard(c)),
            "value": getattr(c, "value", None),
            "limit": getattr(c, "limit", None),
            "sense": str(getattr(c, "sense", "")),
            "group": str(getattr(c, "group", "")),
            "note": str(getattr(c, "note", "") or ""),
            "residual": getattr(c, "residual", None),
        })
    rows.sort(key=lambda r: (0 if r["passed"] else 1, str(r["name"])))
    return rows


def failed_hard_names(out: Dict[str, Any]) -> List[str]:
    return [
        r["name"]
        for r in constraint_notebook_rows(out)
        if r["hard"] and not r["passed"]
    ]


def headline_kpi_pairs(
    out: Dict[str, Any],
    *,
    hard_feasible: Optional[bool] = None,
) -> List[Tuple[str, str]]:
    """Compatibility wrapper — prefer hero_kpi_cells for PHYS-KPI-001 surfaces."""
    return headline_kpis(out, hard_feasible=hard_feasible)


def infeasibility_trace(out: Dict[str, Any]) -> List[Dict[str, Any]]:
    return build_infeasibility_trace(out)


POWER_LEDGER_KEYS = [
    ("Paux_MW", "Aux heating [MW]"),
    ("Pfus_DT_adj_MW", "Fusion (DT-adj) [MW]"),
    ("Palpha_MW", "Alpha power [MW]"),
    ("Prad_core_MW", "Core radiation [MW]"),
    ("P_SOL_MW", "SOL power [MW]"),
    ("Ploss_MW", "Ploss [MW]"),
    ("P_e_net_MW", "Net electric [MW]"),
    ("P_recirc_MW", "Recirculating [MW]"),
]


def power_ledger_rows(out: Dict[str, Any]) -> List[Dict[str, str]]:
    rows = []
    # Alias map when L0 uses a different primary key than the ledger label key.
    aliases = {
        "Palpha_MW": ("Palpha_MW", "Palpha_dep_MW"),
        "P_e_net_MW": ("P_e_net_MW", "P_net_e_MW"),
        "Pfus_DT_adj_MW": ("Pfus_DT_adj_MW", "Pfus_total_MW"),
    }
    for key, label in POWER_LEDGER_KEYS:
        val = None
        for kk in aliases.get(key, (key,)):
            if kk in out and out[kk] is not None:
                val = out[kk]
                break
        if val is None:
            continue
        try:
            v = float(val)
            if v == v:
                rows.append({"channel": label, "MW": f"{v:.4g}"})
        except (TypeError, ValueError):
            pass
    return rows


def load_industrial_template(name: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    from tools.industrial_scenario_templates_v354 import get_template, get_template_payload

    overrides = get_template(name)
    payload = get_template_payload(name)
    return dict(overrides), dict(payload)


def template_names() -> List[str]:
    from tools.industrial_scenario_templates_v354 import template_names as _names

    return _names()


def _safe_float(v: Any) -> float:
    try:
        f = float(v)
        return f if f == f else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def fmt_num(v: Any) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
        if math.isnan(f):
            return "—"
        return f"{f:.4g}"
    except (TypeError, ValueError):
        return str(v)


def fmt_magnet_margin(v: Any, *, v400_enabled: bool = False) -> str:
    """Magnet margin display — avoid raw nan in telemetry (MAG-NAN-001)."""
    f = _safe_float(v)
    if not math.isfinite(f):
        return "OFF" if not v400_enabled else "—"
    return f"{f:.4g}"


def assumptions_snapshot(session: "DesignSession") -> Dict[str, Any]:
    """UI-level model/assumption snapshot (does not affect physics)."""
    inp = session.inputs
    overlay = session.overlay
    try:
        return {
            "design_intent": str(session.design_intent),
            "confinement_scaling_ref": str(inp.get("confinement_scaling", "IPB98(y,2)")),
            "profile_model": str(inp.get("profile_model", "none")),
            "profile_peaking_ne": float(inp.get("profile_peaking_ne", float("nan"))),
            "profile_peaking_T": float(inp.get("profile_peaking_T", float("nan"))),
            "bootstrap_model": str(inp.get("bootstrap_model", "proxy")),
            "include_radiation": bool(overlay.get("include_radiation", False)),
            "radiation_model": str(inp.get("radiation_model", "off")),
            "radiation_db": str(inp.get("radiation_db", "proxy_v1")),
            "include_synchrotron": bool(overlay.get("include_synchrotron", False)),
            "Zeff_mode": str(inp.get("zeff_mode", "fixed")),
            "Zeff": float(inp.get("zeff", inp.get("Zeff", float("nan")))),
            "dilution_fuel": float(inp.get("dilution_fuel", float("nan"))),
            "f_rad_core": float(inp.get("f_rad_core", float("nan"))),
            "impurity_species": str(inp.get("impurity_species", "")),
            "impurity_frac": float(inp.get("impurity_frac", float("nan"))),
            "include_alpha_loss": bool(overlay.get("include_alpha_loss", False)),
            "alpha_loss_model": str(inp.get("alpha_loss_model", "disabled")),
            "include_hmode_physics": bool(overlay.get("include_hmode_physics", False)),
            "require_Hmode": bool(inp.get("require_Hmode", False)),
            "PLH_margin": float(inp.get("PLH_margin", float("nan"))),
            "use_lambda_q": bool(inp.get("use_lambda_q", False)),
            "particle_balance_enabled": bool(overlay.get("include_particle_balance", False)),
            "ash_dilution_mode": str(inp.get("ash_dilution_mode", "default")),
            "fuel_mode": str(inp.get("fuel_mode", "DT")),
        }
    except Exception:
        return {"design_intent": str(session.design_intent)}


def authority_snapshot(out: Dict[str, Any]) -> Dict[str, Any]:
    try:
        try:
            from provenance.authority import authority_snapshot_from_outputs
        except ImportError:
            from src.provenance.authority import authority_snapshot_from_outputs  # type: ignore
        return authority_snapshot_from_outputs(out if isinstance(out, dict) else {})
    except Exception:
        return {}


def authority_contract_rows(out: Dict[str, Any]) -> Tuple[List[Dict[str, str]], int]:
    snap = authority_snapshot(out)
    subs = (snap.get("subsystems") or {}) if isinstance(snap, dict) else {}
    rows: List[Dict[str, str]] = []
    n_proxy = 0
    for k, v in subs.items():
        tier = str((v or {}).get("tier", ""))
        if tier.strip().lower() == "proxy":
            n_proxy += 1
        rows.append({
            "subsystem": str(k),
            "tier": tier,
            "validity": str((v or {}).get("validity_domain", "")),
        })
    rows.sort(key=lambda r: r["subsystem"])
    return rows, n_proxy


_REGIME_TYPICAL = {
    "rho_star": (1e-4, 3e-2),
    "H98": (0.7, 1.5),
    "fG": (0.2, 1.2),
    "nGW": (0.1, 2.0),
    "betaN_proxy": (0.5, 4.0),
    "q95_proxy": (2.5, 6.0),
    "P_SOL_over_R_MW_m": (0.0, 50.0),
    "f_bs_proxy": (0.0, 1.0),
    "ne20": (0.0, 3.0),
    "Zeff": (1.0, 3.0),
    "lambda_q_mm": (0.1, 10.0),
    "q_div_MW_m2": (0.0, 50.0),
    "P_CD_MW": (0.0, 300.0),
    "eta_CD_A_W": (0.0, 5e-6),
    "TBR": (0.7, 1.4),
    "B_peak_T": (0.0, 30.0),
}


def regime_compass_rows(
    out: Dict[str, Any],
    *,
    include_radiation: bool = False,
    use_lambda_q: bool = False,
    show_unc: bool = False,
    unc_proxy_frac: float = 0.15,
    unc_neut_frac: float = 0.20,
) -> List[Dict[str, Any]]:
    spec = [
        ("ρ*", "rho_star", "–", "Diagnostic"),
        ("H98", "H98", "–", "Authoritative"),
        ("fG", "fG", "–", "Authoritative"),
        ("nGW", "nGW", "×1e20 m⁻³", "Diagnostic"),
        ("βN", "betaN_proxy", "–", "Proxy"),
        ("q95", "q95_proxy", "–", "Proxy"),
        ("P_SOL/R", "P_SOL_over_R_MW_m", "MW/m", "Proxy"),
        ("Bootstrap f_bs", "f_bs_proxy", "–", "Proxy"),
        ("n̄e", "ne20", "×1e20 m⁻³", "Authoritative"),
        ("Z_eff", "Zeff", "–", "Proxy" if include_radiation else "Diagnostic"),
        ("λq", "lambda_q_mm", "mm", "Proxy" if use_lambda_q else "Diagnostic"),
        ("q_div", "q_div_MW_m2", "MW/m²", "Proxy"),
        ("P_CD", "P_CD_MW", "MW", "Proxy"),
        ("η_CD", "eta_CD_A_W", "A/W", "Proxy"),
        ("TBR", "TBR", "–", "Proxy"),
        ("B_peak", "B_peak_T", "T", "Authoritative"),
    ]
    rows: List[Dict[str, Any]] = []
    for label, key, unit, badge_type in spec:
        v = _safe_float(out.get(key, float("nan")))
        lo, hi = _REGIME_TYPICAL.get(key, (float("nan"), float("nan")))
        flag = ""
        if math.isfinite(v) and math.isfinite(lo) and math.isfinite(hi):
            if v < lo:
                flag = "LOW"
            elif v > hi:
                flag = "HIGH"
        unc = ""
        if show_unc and badge_type == "Proxy" and math.isfinite(v):
            frac = unc_neut_frac if key in ("TBR", "lambda_q_mm") else unc_proxy_frac
            unc = f"±{(100 * frac):.0f}%"
        typical = f"{lo:g}–{hi:g}" if math.isfinite(lo) and math.isfinite(hi) else ""
        rows.append({
            "metric": label,
            "key": key,
            "value": fmt_num(v) if math.isfinite(v) else "n/a",
            "units": unit,
            "type": badge_type,
            "typical": typical,
            "flag": flag,
            "unc": unc,
        })
    return rows


def build_coils_metrics(out: Dict[str, Any]) -> List[Tuple[str, str]]:
    pairs = [
        ("Inboard margin (m)", "inboard_margin_m", "{:.3f}"),
        ("R_coil_inner (m)", "R_coil_inner_m", "{:.3f}"),
        ("B_peak (T)", "B_peak_T", "{:.2f}"),
        ("σ_vm (MPa)", "sigma_vm_MPa", "{:.0f}"),
        ("HTS margin", "hts_margin", "{:.2f}"),
        ("TF Jop (MA/mm²)", "tf_Jop_MA_per_mm2", "{:.3f}"),
        ("TF strain", "tf_strain", "{:.4f}"),
        ("Cryo power (MW)", "cryo_power_MW", "{:.2f}"),
    ]
    rows: List[Tuple[str, str]] = []
    v400 = bool(out.get("magnet_v400_enabled", False))
    for lab, key, fmt in pairs:
        v = _safe_float(out.get(key, float("nan")))
        if key == "hts_margin" and not math.isfinite(v):
            rows.append((lab, fmt_magnet_margin(v, v400_enabled=v400)))
        else:
            rows.append((lab, fmt.format(v) if math.isfinite(v) else "—"))
    return rows


def fuel_cycle_metric_groups(out: Dict[str, Any]) -> List[List[Tuple[str, str]]]:
    def _m(k: str, fmt: str = "{:.3g}", suffix: str = "") -> str:
        v = _safe_float(out.get(k, float("nan")))
        return (fmt.format(v) + suffix) if math.isfinite(v) else "n/a"

    groups: List[List[Tuple[str, str]]] = [
        [
            ("T burn (g/day)", _m("T_burn_g_per_day", "{:.2f}")),
            ("T inventory proxy (g)", _m("T_inventory_proxy_g", "{:.2f}")),
            ("TBR (proxy)", _m("TBR", "{:.2f}")),
            ("FW dpa/y", _m("fw_dpa_per_year", "{:.2f}")),
        ],
        [
            ("Availability", _m("availability_model", "{:.2f}")),
            ("Annual net (MWh/y)", _m("annual_net_MWh", "{:.3g}")),
            ("FW interval (y)", _m("fw_replace_interval_y", "{:.2f}")),
            ("DIV interval (y)", _m("div_replace_interval_y", "{:.2f}")),
        ],
    ]
    av359 = _safe_float(out.get("availability_v359", float("nan")))
    if math.isfinite(av359):
        groups.append([
            ("Availability (replacement ledger)", _m("availability_v359", "{:.2f}")),
            ("Net MWh/y (replacement ledger)", _m("net_electric_MWh_per_year_v359", "{:.3g}")),
            ("LCOE (replacement ledger) (USD/MWh)", _m("LCOE_proxy_v359_USD_per_MWh", "{:.2f}")),
            ("Repl. cost (MUSD/y)", _m("replacement_cost_MUSD_per_year_v359", "{:.2f}")),
        ])
    av368 = _safe_float(out.get("availability_v368", float("nan")))
    if math.isfinite(av368):
        groups.append([
            ("Availability (maintenance scheduling)", _m("availability_v368", "{:.2f}")),
            ("Outage total (maintenance scheduling)", _m("outage_total_frac_v368", "{:.2f}")),
            ("Net MWh/y (maintenance scheduling)", _m("net_electric_MWh_per_year_v368", "{:.3g}")),
            ("Repl. cost (MUSD/y)", _m("replacement_cost_MUSD_per_year_v368", "{:.2f}")),
        ])
    av391 = _safe_float(out.get("availability_cert_v391", float("nan")))
    if math.isfinite(av391):
        groups.append([
            ("Availability (reliability envelope)", _m("availability_cert_v391", "{:.3f}")),
            ("Planned outage (reliability envelope)", _m("planned_outage_frac_v391", "{:.3f}")),
            ("Maintenance downtime (reliability envelope)", _m("maint_downtime_frac_v391", "{:.3f}")),
            ("Unplanned downtime (reliability envelope)", _m("unplanned_downtime_frac_v391", "{:.3f}")),
        ])
    return groups


def fuel_cycle_caps_caption(out: Dict[str, Any]) -> str:
    lims = []
    for k in ("tritium_inventory_max_g", "fw_dpa_max_per_year", "availability_min", "annual_net_MWh_min"):
        v = _safe_float(out.get(k, float("nan")))
        if math.isfinite(v):
            lims.append(f"{k}={v:.3g}")
    if lims:
        return "Active caps/requirements: " + "; ".join(lims)
    return "No explicit caps/requirements set for fuel-cycle/lifetime/annual-energy in this run."


def magnet_card_metrics(out: Dict[str, Any]) -> Dict[str, Any]:
    tf_sc = _safe_float(out.get("tf_sc_flag", float("nan")))
    sc_margin = out.get("sc_margin", out.get("hts_margin", float("nan")))
    p_tf_ohm = _safe_float(out.get("P_tf_ohmic_MW", float("nan")))
    policy = out.get("constraint_policy") or {}
    hb = set(policy.get("hard_blocking") or [])
    diag = set(policy.get("diagnostic_only") or [])
    if "TF_SC" in hb:
        tf_note = "Blocking (reactor covenant)"
    elif "TF_SC" in diag:
        tf_note = "Diagnostic (research)"
    else:
        tf_note = ""
    return {
        "tech": str(out.get("magnet_technology", "unknown")),
        "tf_sc": tf_sc,
        "sc_margin": sc_margin,
        "sc_margin_display": fmt_magnet_margin(
            sc_margin, v400_enabled=bool(out.get("magnet_v400_enabled", False))
        ),
        "p_tf_ohm": p_tf_ohm,
        "tcoil_K": out.get("Tcoil_K"),
        "tf_note": tf_note,
        "hts_lifetime_yr": out.get("hts_lifetime_yr"),
        "V_dump_kV": out.get("V_dump_kV"),
        "P_e_net_MW": out.get("P_e_net_MW", out.get("P_net_e_MW")),
        # Legacy alias kept for callers that still unpack P_net_e_MW.
        "P_net_e_MW": out.get("P_e_net_MW", out.get("P_net_e_MW")),
    }


def magnet_v400_summary(out: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not bool(out.get("magnet_v400_enabled", False)):
        return None
    return {
        "combined_margin": out.get("magnet_v400_margin"),
        "tier": out.get("magnet_v400_tier", "unknown"),
        "dominant": out.get("magnet_v400_dominant_limiter", "unknown"),
        "dominant_margin": out.get("magnet_v400_dominant_margin"),
        "per_aspect_margins": {
            "B margin (allow/req - 1)": out.get("magnet_v400_b_margin"),
            "J margin (allow/req - 1)": out.get("magnet_v400_j_margin"),
            "Stress margin (allow/req - 1)": out.get("magnet_v400_stress_margin"),
            "SC operating margin ((sc/sc_min)-1)": out.get("magnet_v400_sc_oper_margin"),
            "T-window margin (normalized)": out.get("magnet_v400_t_window_margin"),
            "Cu ohmic power margin (Pmax/Pohmic - 1)": out.get("magnet_v400_p_tf_ohmic_margin"),
        },
        "per_aspect_tiers": {
            "B tier": out.get("magnet_v400_b_tier"),
            "J tier": out.get("magnet_v400_j_tier"),
            "Stress tier": out.get("magnet_v400_stress_tier"),
            "SC tier": out.get("magnet_v400_sc_tier"),
            "T-window tier": out.get("magnet_v400_t_window_tier"),
            "Cu ohmic tier": out.get("magnet_v400_p_tf_ohmic_tier"),
        },
    }


def magnet_v410_summary(out: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """TF/PF/CS SC system depth overlay (proxy). None when disabled."""
    if not bool(out.get("magnet_v410_enabled", False)):
        return None
    return {
        "screening_tier": out.get("magnet_v410_screening_tier", "proxy"),
        "overlay_version": out.get("magnet_v410_overlay_version", "v410"),
        "system_margin": out.get("magnet_v410_system_margin"),
        "system_tier": out.get("magnet_v410_system_tier", "unknown"),
        "dominant_family": out.get("magnet_v410_dominant_family", "unknown"),
        "dominant_family_margin": out.get("magnet_v410_dominant_family_margin"),
        "provenance": out.get("magnet_v410_provenance", ""),
        "family_margins": {
            "TF family": out.get("magnet_v410_tf_margin"),
            "PF family": out.get("magnet_v410_pf_margin"),
            "CS family": out.get("magnet_v410_cs_margin"),
        },
        "family_tiers": {
            "TF": out.get("magnet_v410_tf_tier"),
            "PF": out.get("magnet_v410_pf_tier"),
            "CS": out.get("magnet_v410_cs_tier"),
        },
        "family_dominants": {
            "TF": out.get("magnet_v410_tf_dominant"),
            "PF": out.get("magnet_v410_pf_dominant"),
            "CS": out.get("magnet_v410_cs_dominant"),
        },
    }


def machine_v412_summary(out: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Radial / machine-build closure overlay (proxy). None when disabled."""
    if not bool(out.get("machine_v412_enabled", False)):
        return None
    return {
        "screening_tier": out.get("machine_v412_screening_tier", "proxy"),
        "overlay_version": out.get("machine_v412_overlay_version", "v412"),
        "system_margin": out.get("machine_v412_system_margin"),
        "system_tier": out.get("machine_v412_system_tier", "unknown"),
        "dominant_aspect": out.get("machine_v412_dominant_aspect", "unknown"),
        "dominant_aspect_margin": out.get("machine_v412_dominant_aspect_margin"),
        "inboard_margin_m": out.get("machine_v412_inboard_margin_m"),
        "closure_ok": out.get("machine_v412_closure_ok"),
        "n_layers": out.get("machine_v412_n_layers"),
        "outboard_R_outer_m": out.get("machine_v412_outboard_R_outer_m"),
        "provenance": out.get("machine_v412_provenance", ""),
        "narrative": out.get("machine_v412_narrative", ""),
        "aspect_margins": {
            "Inboard closure": out.get("machine_v412_inboard_closure_margin"),
            "Coil bore": out.get("machine_v412_coil_bore_margin"),
            "Build gap": out.get("machine_v412_gap_clearance_margin"),
            "Layer mins": out.get("machine_v412_layer_mins_margin"),
        },
        "layer_ledger": out.get("machine_v412_layer_ledger"),
    }


def plant_v419_summary(out: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Summary dict for plant Sankey ledger (None when disabled)."""
    if not bool(out.get("plant_v419_enabled", False)):
        return None
    return {
        "screening_tier": out.get("plant_v419_screening_tier", "proxy"),
        "overlay_version": out.get("plant_v419_overlay_version", "v419"),
        "system_tier": out.get("plant_v419_system_tier", "unknown"),
        "dominant_aspect": out.get("plant_v419_dominant_aspect", "unknown"),
        "Pe_net_MW": out.get("plant_v419_Pe_net_MW"),
        "Pe_gross_MW": out.get("plant_v419_Pe_gross_MW"),
        "Precirc_MW": out.get("plant_v419_Precirc_MW"),
        "f_recirc": out.get("plant_v419_f_recirc"),
        "conservation_ok": out.get("plant_v419_conservation_ok"),
        "n_flows": out.get("plant_v419_n_flows"),
        "provenance": out.get("plant_v419_provenance", ""),
        "narrative": out.get("plant_v419_narrative", ""),
        "flow_table": out.get("plant_v419_flow_table"),
        "sankey_kwargs": out.get("plant_v419_sankey_kwargs"),
        "requires_kpi_honesty_watermark": out.get(
            "plant_v419_requires_kpi_honesty_watermark", True
        ),
        "recirc_breakdown": {
            "HCD": out.get("plant_v419_P_hcd_el_MW"),
            "cryo": out.get("plant_v419_P_cryo_el_MW"),
            "pumping": out.get("plant_v419_P_pumps_el_MW"),
            "tritium": out.get("plant_v419_P_tritium_el_MW"),
            "BOP": out.get("plant_v419_P_bop_el_MW"),
            "TF_ohmic": out.get("plant_v419_P_tf_el_MW"),
        },
    }


def avail_v420_summary(out: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Summary dict for availability→OPEX/LCOE coupling (None when disabled)."""
    if not bool(out.get("avail_v420_enabled", False)):
        return None
    return {
        "screening_tier": out.get("avail_v420_screening_tier", "proxy"),
        "overlay_version": out.get("avail_v420_overlay_version", "v420"),
        "system_tier": out.get("avail_v420_system_tier", "unknown"),
        "availability": out.get("avail_v420_availability"),
        "availability_source": out.get("avail_v420_availability_source", ""),
        "elm_v409_coupled": out.get("avail_v420_elm_v409_coupled"),
        "duty_factor": out.get("avail_v420_duty_factor"),
        "hours_per_year_h": out.get("avail_v420_hours_per_year_h"),
        "E_net_MWh_per_y": out.get("avail_v420_E_net_MWh_per_y"),
        "OPEX_total_MUSD_per_y": out.get("avail_v420_OPEX_total_MUSD_per_y"),
        "dominant_opex_driver": out.get("avail_v420_dominant_opex_driver", ""),
        "LCOE_USD_per_MWh": out.get("avail_v420_LCOE_USD_per_MWh"),
        "LCOE_capex_USD_per_MWh": out.get("avail_v420_LCOE_capex_USD_per_MWh"),
        "LCOE_replacement_USD_per_MWh": out.get("avail_v420_LCOE_replacement_USD_per_MWh"),
        "LCOE_opex_USD_per_MWh": out.get("avail_v420_LCOE_opex_USD_per_MWh"),
        "CAPEX_source": out.get("avail_v420_CAPEX_source", ""),
        "replacement_source": out.get("avail_v420_replacement_source", ""),
        "consistency_ok": out.get("avail_v420_consistency_ok"),
        "consistency_checks": out.get("avail_v420_consistency_checks"),
        "provenance": out.get("avail_v420_provenance", ""),
        "narrative": out.get("avail_v420_narrative", ""),
        "requires_kpi_honesty_watermark": out.get(
            "avail_v420_requires_kpi_honesty_watermark", True
        ),
        "opex_breakdown_MUSD_per_y": {
            "fixed": out.get("avail_v420_OPEX_fixed_MUSD_per_y"),
            "electric_recirc": out.get("avail_v420_OPEX_electric_recirc_MUSD_per_y"),
            "electric_cryo": out.get("avail_v420_OPEX_electric_cryo_MUSD_per_y"),
            "electric_cd": out.get("avail_v420_OPEX_electric_cd_MUSD_per_y"),
            "tritium": out.get("avail_v420_OPEX_tritium_MUSD_per_y"),
            "maintenance": out.get("avail_v420_OPEX_maintenance_MUSD_per_y"),
        },
    }


def costing_v421_summary(out: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Summary dict for bottom-up modular costing (None when disabled)."""
    if not bool(out.get("costing_v421_enabled", False)):
        return None
    return {
        "screening_tier": out.get("costing_v421_screening_tier", "proxy"),
        "overlay_version": out.get("costing_v421_overlay_version", "v421"),
        "system_tier": out.get("costing_v421_system_tier", "unknown"),
        "CAPEX_total_MUSD": out.get("costing_v421_CAPEX_total_MUSD"),
        "direct_subtotal_MUSD": out.get("costing_v421_direct_subtotal_MUSD"),
        "indirect_subtotal_MUSD": out.get("costing_v421_indirect_subtotal_MUSD"),
        "equipment_subtotal_MUSD": out.get("costing_v421_equipment_subtotal_MUSD"),
        "dominant_account": out.get("costing_v421_dominant_account", ""),
        "dominant_account_frac": out.get("costing_v421_dominant_account_frac"),
        "LCOE_USD_per_MWh": out.get("costing_v421_LCOE_USD_per_MWh"),
        "LCOE_basis": out.get("costing_v421_LCOE_basis", ""),
        "field_bin": out.get("costing_v421_field_bin", ""),
        "magnet_mass_source": out.get("costing_v421_magnet_mass_source", ""),
        "consistency_ok": out.get("costing_v421_consistency_ok"),
        "consistency_checks": out.get("costing_v421_consistency_checks"),
        "account_ledger": out.get("costing_v421_account_ledger"),
        "provenance": out.get("costing_v421_provenance", ""),
        "narrative": out.get("costing_v421_narrative", ""),
        "requires_kpi_honesty_watermark": out.get(
            "costing_v421_requires_kpi_honesty_watermark", True
        ),
    }


POWER_LEDGER_BADGED = [
    ("Input power Pin", "Pin_MW", "Authoritative"),
    ("Aux heating", "Paux_MW", "Authoritative"),
    ("Ohmic", "Pohm_MW", "Proxy"),
    ("Fusion alpha (generated)", "Palpha_MW", "Authoritative"),
    ("Core radiation", "Prad_core_MW", "Proxy"),
    ("SOL/Separatrix power", "P_SOL_MW", "Authoritative"),
    ("Total loss Ploss", "Ploss_MW", "Authoritative"),
    ("Net electric", "P_e_net_MW", "Proxy"),
]

_POWER_LEDGER_ALIASES = {
    "P_e_net_MW": ("P_e_net_MW", "P_net_e_MW"),
    "Palpha_MW": ("Palpha_MW", "Palpha_dep_MW"),
}


def power_ledger_badged_rows(
    out: Dict[str, Any],
    *,
    include_radiation: bool = False,
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for lbl, key, badge in POWER_LEDGER_BADGED:
        v = None
        for kk in _POWER_LEDGER_ALIASES.get(key, (key,)):
            if kk in out and out.get(kk) is not None:
                v = out.get(kk)
                break
        if v is None:
            v = float("nan")
        b = badge
        if key == "Prad_core_MW":
            b = "Proxy" if include_radiation else "Diagnostic"
        try:
            fv = float(v)
            mw = fmt_num(fv) if fv == fv else "n/a"
        except (TypeError, ValueError):
            mw = "n/a"
        rows.append({"item": lbl, "key": key, "MW": mw, "type": b})
    return rows


def pin_ploss_closure_mw(out: Dict[str, Any]) -> Optional[float]:
    pin = _safe_float(out.get("Pin_MW", float("nan")))
    ploss = _safe_float(out.get("Ploss_MW", float("nan")))
    if math.isfinite(pin) and math.isfinite(ploss):
        return pin - ploss
    return None


CONSTRAINT_PROVENANCE: Dict[str, Dict[str, str]] = {
    "q95": {"def": "Proxy q95 computed from geometry/Bt/Ip assumptions.", "drivers": "Ip, Bt, R0, a, κ", "sense": ">=", "notes": "Always hard in both intents."},
    "q_div": {"def": "Divertor peak heat flux proxy from P_SOL and wetted area / λq model.", "drivers": "P_SOL, R0, λq, f_rad", "sense": "<=", "notes": "Definition depends on SOL-width toggle."},
    "P_SOL/R": {"def": "Separatrix power normalized by major radius.", "drivers": "P_SOL, R0", "sense": "<=", "notes": "Often used as a heat-exhaust severity proxy."},
    "sigma_vm": {"def": "Von Mises stress proxy in TF structure from peak field + build.", "drivers": "B_peak, coil build, R0", "sense": "<=", "notes": "Engineering screening, not a full FEA."},
    "HTS margin": {"def": "HTS current-density/temperature margin proxy.", "drivers": "B_peak, Top, Jop, conductor assumption", "sense": ">=", "notes": "Screening margin; label as proxy if conductor model simplified."},
    "TBR": {"def": "Tritium breeding ratio proxy from blanket/shield thickness + coverage assumptions.", "drivers": "t_blanket, t_shield, coverage", "sense": ">=", "notes": "Proxy unless driven by external neutronics."},
    "NWL": {"def": "Neutron wall loading proxy from fusion power and surface area.", "drivers": "Pfus, R0, a, κ", "sense": "<=", "notes": "Screening metric."},
    "beta": {"def": "Beta or normalized beta proxy guardrail.", "drivers": "pressure, Bt, Ip", "sense": "<=", "notes": "Proxy stability screen."},
}


def constraint_provenance(name: str) -> Optional[Dict[str, str]]:
    key_l = str(name).lower()
    for k, v in CONSTRAINT_PROVENANCE.items():
        if k.lower() in key_l:
            return v
    return None


def constraint_suggestion(name: str) -> str:
    n = name.lower()
    if "q_div" in n or "p_sol" in n:
        return "Reduce P_SOL (increase radiation, reduce aux), increase R0, or increase lambda_q (design/multiplier)."
    if "hts" in n or "b_peak" in n or "sigma" in n:
        return "Reduce B_peak (increase coil build/R0, reduce Bt), reduce stress (increase thickness, reduce B_peak), or raise HTS margin (lower Top or improve conductor)."
    if "tbr" in n:
        return "Increase blanket/shield thickness or improve breeding/coverage assumptions."
    if "nwl" in n:
        return "Reduce fusion power density (increase size R0 or reduce performance targets) or improve shielding."
    if "beta" in n:
        return "Increase size R0 or reduce Ip/pressure (lower Ti or fG) to bring beta below limit."
    if "q95" in n:
        return "Increase q95 (reduce Ip or increase Bt/R0) for stability margin."
    if "fg" in n:
        return "Reduce density target (lower fG) or increase Ip to raise Greenwald limit."
    if "p_net" in n:
        return "Increase Pfus (within constraints), increase thermal efficiency, or reduce recirculating loads."
    if "t_flat" in n:
        return "Increase available flux swing (CS design), reduce loop voltage (improve resistivity/current profile), or allow lower Ip."
    return "Adjust major radius / field / current / aux power to recover feasibility."


def constraint_radar_rows(out: Dict[str, Any], art: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    cons = []
    if isinstance(art, dict) and art.get("constraints"):
        cons = art["constraints"]
    if not cons:
        try:
            try:
                from constraints.constraints import evaluate_constraints
            except ImportError:
                from src.constraints.constraints import evaluate_constraints  # type: ignore
            cons = evaluate_constraints(out)
        except Exception:
            cons = []
    for c in cons:
        if isinstance(c, dict):
            name = str(c.get("name", ""))
            try:
                margin = float(c.get("margin_frac", c.get("margin", float("nan"))))
            except (TypeError, ValueError):
                margin = float("nan")
            rows.append({
                "constraint": name,
                "sense": c.get("sense", ""),
                "value": c.get("value"),
                "limit": c.get("limit"),
                "units": c.get("units", ""),
                "passed": bool(c.get("passed", True)),
                "margin_frac": margin,
                "severity": c.get("severity", "hard"),
                "note": c.get("note", ""),
            })
        else:
            try:
                margin = float(getattr(c, "margin", float("nan")))
            except (TypeError, ValueError):
                margin = float("nan")
            rows.append({
                "constraint": str(getattr(c, "name", "")),
                "sense": getattr(c, "sense", ""),
                "value": getattr(c, "value", None),
                "limit": getattr(c, "limit", None),
                "units": getattr(c, "units", ""),
                "passed": bool(getattr(c, "passed", True)),
                "margin_frac": margin,
                "severity": getattr(c, "severity", "hard"),
                "note": getattr(c, "note", "") or "",
            })
    rows.sort(key=lambda r: (r["passed"], str(r.get("severity", "hard")), r.get("margin_frac", float("inf"))))
    return rows


def dominant_limiter_summary(rows: List[Dict[str, Any]]) -> Optional[str]:
    hard = [r for r in rows if str(r.get("severity", "hard")) == "hard"]
    hard = [r for r in hard if isinstance(r.get("margin_frac"), (int, float)) and r["margin_frac"] == r["margin_frac"]]
    if not hard:
        return None
    dom = min(hard, key=lambda r: float(r.get("margin_frac", float("inf"))))
    mf = float(dom.get("margin_frac", float("nan")))
    if not math.isfinite(mf):
        return None
    return f"**Dominant limiter:** {dom.get('constraint')} (margin {mf:.3g}). This is the tightest hard constraint at this point."


BASELINE_DELTA_KPIS = [
    ("Q_DT_eqv", "Q_DT_eqv", "–", ("Q_DT_eqv", "Q")),
    ("H98", "H98", "–", ("H98",)),
    ("P_net_e", "P_e_net_MW", "MW(e)", ("P_e_net_MW", "P_net_e_MW")),
    ("q95", "q95_proxy", "–", ("q95_proxy", "q95")),
    ("betaN", "beta_N", "–", ("beta_N", "betaN_proxy", "betaN")),
    ("q_div", "q_div_MW_m2", "MW/m²", ("q_div_MW_m2",)),
    ("P_SOL", "P_SOL_MW", "MW", ("P_SOL_MW",)),
    ("TBR", "TBR", "–", ("TBR",)),
]


def baseline_delta_rows(
    baseline_art: Dict[str, Any],
    current_art: Dict[str, Any],
) -> List[Dict[str, Any]]:
    bo = (baseline_art.get("outputs") or {}) if isinstance(baseline_art, dict) else {}
    co = (current_art.get("outputs") or {}) if isinstance(current_art, dict) else {}
    rows: List[Dict[str, Any]] = []
    for label, _primary, unit, aliases in BASELINE_DELTA_KPIS:
        vb = float("nan")
        vc = float("nan")
        for kk in aliases:
            if kk in bo and bo.get(kk) is not None:
                vb = _safe_float(bo.get(kk))
                break
        for kk in aliases:
            if kk in co and co.get(kk) is not None:
                vc = _safe_float(co.get(kk))
                break
        dlt = vc - vb if math.isfinite(vb) and math.isfinite(vc) else float("nan")
        rows.append({
            "KPI": label,
            "baseline": fmt_num(vb) if math.isfinite(vb) else "n/a",
            "current": fmt_num(vc) if math.isfinite(vc) else "n/a",
            "delta": fmt_num(dlt) if math.isfinite(dlt) else "n/a",
            "unit": unit,
        })
    return rows


PERT_SCAN_PARAMS = ["R0_m", "a_m", "kappa", "Bt_T", "Ip_MA", "fG", "Ti_keV", "Paux_MW"]


def run_perturbation_scan(
    base_pi: Any,
    evaluator: Callable[[Any], Dict[str, Any]],
    *,
    params: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """±10% perturbation scan reporting hard-constraint flips (Streamlit parity)."""
    try:
        try:
            from constraints.constraints import evaluate_constraints
        except ImportError:
            from src.constraints.constraints import evaluate_constraints  # type: ignore
    except ImportError:
        return []

    keys = list(params or PERT_SCAN_PARAMS)
    base_out = evaluator(base_pi)
    base_failed = [
        str(getattr(c, "name", ""))
        for c in (evaluate_constraints(base_out) or [])
        if str(getattr(c, "severity", "hard")) == "hard" and not bool(getattr(c, "passed", False))
    ]
    rows: List[Dict[str, Any]] = []
    for k in keys:
        if not hasattr(base_pi, k):
            continue
        x0 = _safe_float(getattr(base_pi, k))
        if not math.isfinite(x0) or x0 == 0.0:
            continue
        for fac in (0.9, 1.1):
            pi = replace(base_pi, **{k: x0 * fac})
            y = evaluator(pi)
            failed = [
                str(getattr(c, "name", ""))
                for c in (evaluate_constraints(y) or [])
                if str(getattr(c, "severity", "hard")) == "hard" and not bool(getattr(c, "passed", False))
            ]
            rows.append({
                "param": k,
                "factor": fac,
                "value": fmt_num(x0 * fac),
                "hard_failed": ", ".join(failed),
                "new_failures": ", ".join(sorted(set(failed) - set(base_failed))),
                "resolved": ", ".join(sorted(set(base_failed) - set(failed))),
            })
    return rows


def local_fd_sensitivity_rows(
    base_pi: Any,
    evaluator: Callable[[Any], Dict[str, Any]],
    *,
    params: Optional[List[str]] = None,
    outputs: Optional[List[str]] = None,
    rel_step: float = 1e-3,
) -> List[Dict[str, Any]]:
    try:
        try:
            from solvers.sensitivity import finite_difference_sensitivities
        except ImportError:
            from src.solvers.sensitivity import finite_difference_sensitivities  # type: ignore
    except ImportError:
        return []

    p_list = list(params or ["R0_m", "a_m", "kappa", "Bt_T", "Ip_MA", "fG", "H98", "eta_CD", "n_neu_frac", "Zeff"])
    o_list = list(outputs or ["Q_DT_eqv", "P_e_net_MW", "beta_N", "q_div_MW_m2", "B_peak_T"])
    sens = finite_difference_sensitivities(base_pi, evaluator, params=p_list, outputs=o_list, rel_step=rel_step)
    rows: List[Dict[str, Any]] = []
    for o in o_list:
        base_y = _safe_float(sens.get("_base", {}).get(o, float("nan")))
        for p in p_list:
            if p not in sens.get(o, {}):
                continue
            dydx = float(sens[o][p])
            x0 = _safe_float(getattr(base_pi, p, float("nan"))) if hasattr(base_pi, p) else float("nan")
            norm = float("nan")
            if math.isfinite(x0) and math.isfinite(base_y) and x0 != 0.0 and base_y != 0.0:
                norm = dydx * (x0 / base_y)
            rows.append({
                "output": o,
                "param": p,
                "dY/dX": fmt_num(dydx),
                "elasticity": fmt_num(norm) if math.isfinite(norm) else "n/a",
            })
    rows.sort(key=lambda r: (r["output"], r["param"]))
    return rows


def lever_recipe_tables(ff: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """Increase-margin and avoid/regression lever tables for dominant blocker."""
    dom_adv = ff.get("dominant_advice") or {}
    dom_c = str(dom_adv.get("dominant_constraint", ""))
    tornado = ff.get("tornado") or {}
    if not dom_c or not isinstance(tornado, dict) or not tornado.get(dom_c):
        return [], [], dom_c

    dom_rows = list(tornado.get(dom_c, []) or [])
    help_rows = [r for r in dom_rows if float(r.get("dmargin_per_unit", 0.0)) > 0]
    hurt_rows = [r for r in dom_rows if float(r.get("dmargin_per_unit", 0.0)) < 0]

    def _mk_help(rows: List[Dict[str, Any]], action: str) -> List[Dict[str, Any]]:
        out_rows: List[Dict[str, Any]] = []
        for r in rows[:5]:
            dmdx = _safe_float(r.get("dmargin_per_unit", float("nan")))
            dx = _safe_float(r.get("step", float("nan")))
            if not math.isfinite(dmdx) or not math.isfinite(dx):
                continue
            delta = dmdx * dx if action == "increase" else (-dmdx) * dx
            out_rows.append({
                "knob": str(r.get("knob", "")),
                "action": action,
                "Δx": fmt_num(dx),
                "Δmargin @ Δx": fmt_num(delta),
                "|Δmargin|": fmt_num(abs(delta)),
            })
        out_rows.sort(key=lambda rr: -_safe_float(rr["|Δmargin|"]) if math.isfinite(_safe_float(rr["|Δmargin|"])) else float("inf"))
        return out_rows

    actions_help = _mk_help(help_rows, "increase")
    actions_hurt = _mk_help(hurt_rows, "decrease")
    return actions_help, actions_hurt, dom_c


def control_vs_caps_row(out: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "bw_req_Hz": out.get("vs_bandwidth_req_Hz"),
        "bw_max_Hz": out.get("vs_bandwidth_max_Hz"),
        "P_req_MW": out.get("vs_control_power_req_MW"),
        "P_max_MW": out.get("vs_control_power_max_MW"),
        "ok": out.get("vs_control_ok"),
    }


def control_pf_caps_row(out: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "I_peak": out.get("pf_I_peak_MA"),
        "I_max": out.get("pf_I_peak_max_MA"),
        "V_peak": out.get("pf_V_peak_V"),
        "V_max": out.get("pf_V_peak_max_V"),
        "P_peak": out.get("pf_P_peak_MW"),
        "P_max": out.get("pf_P_peak_max_MW"),
        "dIdt": out.get("pf_dIdt_peak_MA_s"),
        "dIdt_max": out.get("pf_dIdt_max_MA_s"),
        "E_pulse": out.get("pf_E_pulse_MJ"),
        "E_max": out.get("pf_E_pulse_max_MJ"),
        "ok": out.get("pf_envelope_ok"),
    }


def control_cs_row(out: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "cs_flux_required_Wb": out.get("cs_flux_required_Wb"),
        "cs_flux_available_Wb": out.get("cs_flux_available_Wb"),
        "cs_flux_margin": out.get("cs_flux_margin"),
        "V_loop_ramp_V": out.get("cs_V_loop_ramp_V"),
        "V_loop_max_V": out.get("cs_V_loop_max_V"),
    }


def control_signed_margins(out: Dict[str, Any], section: str) -> Dict[str, Any]:
    m = out.get("control_contract_margins") or {}
    if not isinstance(m, dict):
        return {}
    if section == "vs":
        return {k: m.get(k) for k in ("vs_bandwidth_margin_Hz", "vs_control_power_margin_MW") if m.get(k) is not None}
    if section == "pf":
        return {k: m.get(k) for k in (
            "pf_I_peak_margin_MA", "pf_dIdt_margin_MA_s", "pf_V_peak_margin_V",
            "pf_P_peak_margin_MW", "pf_E_pulse_margin_MJ",
        ) if m.get(k) is not None}
    if section == "sol":
        return {"f_rad_SOL_margin": m.get("f_rad_SOL_margin")} if m.get("f_rad_SOL_margin") is not None else {}
    if section == "rwm":
        return {k: m.get(k) for k in ("rwm_bandwidth_margin_Hz", "rwm_control_power_margin_MW") if m.get(k) is not None}
    return {}


def v398_control_ledger(out: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not bool(out.get("control_stability_v398_enabled", False)):
        return None
    return {
        "vs_budget_margin": out.get("vs_budget_margin_v398"),
        "vde_headroom": out.get("vde_headroom_v398"),
        "rwm_index": out.get("rwm_proximity_index_v398"),
        "vde_headroom_tier": out.get("vde_headroom_tier_v398"),
        "rwm_proximity_tier": out.get("rwm_proximity_tier_v398"),
        "psi_req_Vs": out.get("psi_required_Vs_v398"),
        "psi_av_Vs": out.get("psi_available_Vs_v398"),
        "vde_power_headroom": out.get("vde_power_headroom_v398"),
        "vde_bw_headroom": out.get("vde_bw_headroom_v398"),
    }


def tau_peaking_panel_data(out: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Data for v397 τE peaking panel (mirrors ui/authority_dashboard.render_profile_tau_peaking_panel)."""
    if not isinstance(out, dict) or not out:
        return None
    factor = out.get("tau_e_profile_factor_v397", out.get("tau_e_density_peaking_factor_v397"))
    enabled = float(out.get("include_profile_proxy_v397", out.get("profile_proxy_v397_enabled", 0)) or 0) > 0.5
    if factor in (None, float("nan")):
        if not enabled:
            return {"enabled": False, "message": "Profile peaking proxy disabled — τE peaking factor not computed."}
        return None
    f = _safe_float(factor)
    if not math.isfinite(f):
        return None
    data: Dict[str, Any] = {"enabled": True, "factor": f, "factor_label": f"{f:.3f}"}
    tau0 = out.get("tauE_s")
    if tau0 is not None:
        t0 = _safe_float(tau0)
        if math.isfinite(t0) and f > 0:
            data["tauE_s_caption"] = f"Baseline τE_s ≈ {t0:.3f} s (after peaking coupling when enabled)."
    return data


def v396_scaling_rows(out: Dict[str, Any]) -> List[Dict[str, str]]:
    d = out.get("tauE_scalings_v396", {})
    if not isinstance(d, dict) or not d:
        return []
    return [{"scaling": str(k), "tauE_s": fmt_num(v)} for k, v in d.items()]


def v397_profile_summary(out: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not bool(out.get("profile_proxy_v397_enabled", False)):
        return None
    return {
        "peaking_n": out.get("profile_peaking_n_v397"),
        "peaking_T": out.get("profile_peaking_T_v397"),
        "peaking_p": out.get("profile_peaking_p_v397"),
        "peaking_j": out.get("profile_peaking_j_v397"),
        "q95_proxy": out.get("q95_proxy_v397"),
        "q0_proxy": out.get("q0_proxy_v397"),
        "li_proxy": out.get("li_proxy_v397"),
        "bootstrap_localization": out.get("bootstrap_localization_index_v397"),
        "sample": out.get("profile_proxy_v397_sample", {}),
    }


def radial_build_png_bytes(artifact: Dict[str, Any]) -> Optional[bytes]:
    try:
        import tempfile
        from pathlib import Path

        try:
            from shams_io.plotting import plot_radial_build_from_artifact
        except ImportError:
            from src.shams_io.plotting import plot_radial_build_from_artifact  # type: ignore
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "radial_build.png"
            plot_radial_build_from_artifact(artifact, path)
            data = path.read_bytes()
            return data if data else None
    except Exception:
        return None


PLOT_PHYSICAL_MEANING = {
    "power_balance": (
        "**Q (fusion gain proxy)** is defined as fusion power divided by auxiliary heating power "
        "(here the UI uses *Paux_for_Q* as the denominator).\n\n"
        "**H98** is a confinement multiplier relative to the empirical **IPB98(y,2)** ELMy H-mode scaling "
        "used as an ITER physics-basis reference.\n\n"
        "**P_LH / H-mode access** comparisons follow the multi-machine ITPA threshold scaling "
        "(often referred to as Martin-2008 / PLH-08).\n\n"
        "If you enable SOL-width physics, the app’s λq proxy is motivated by the multi-machine "
        "H-mode power-falloff width scaling (Eich-2013)."
    ),
    "stability": (
        "**q95** (safety factor near 95% flux) is a standard operational metric used as a proxy for MHD margin; "
        "lower q tends to reduce kink/tearing stability margin.\n\n"
        "**Normalized beta βN** is a widely used performance/stability figure of merit that scales pressure "
        "relative to magnetic field and current (often discussed in terms of the Troyon aB/I scaling).\n\n"
        "**Bootstrap fraction f_bs** indicates how much of the plasma current is self-driven by pressure "
        "gradients (important for steady-state operation). This UI uses a simple proxy coefficient rather than "
        "a full neoclassical calculation."
    ),
    "geometry": (
        "**Greenwald fraction fG** (used internally by the solver) expresses density as a fraction of the "
        "empirical tokamak density limit scaling with I_p and minor radius (often called the Greenwald limit).\n\n"
        "The *radial build* and **Bpeak/B0** mapping are engineering proxies; they’re not meant to replace "
        "detailed coil/stress finite-element analysis."
    ),
    "confinement": (
        "H98 is defined as tauE_eff / tauE_IPB98(y,2). H_scaling compares against the selected reference scaling. "
        "See also the IPB98(y,2) and ITER89-P scaling references."
    ),
}


_POINT_SUMMARY_KEYS = [
    # (display_label, lookup_keys…) — first present L0/alias wins.
    ("Ip [MA]", ("Ip_MA",)),
    ("fG [-]", ("fG",)),
    ("H98 [-]", ("H98",)),
    ("Q [-]", ("Q_DT_eqv", "Q")),
    ("Pfus [MW]", ("Pfus_total_MW", "Pfus_MW", "P_fus_MW")),
    ("P_net,e [MW]", ("P_e_net_MW", "P_net_e_MW")),
    ("B_peak [T]", ("B_peak_T", "Bpeak_T")),
    ("TBR (proxy) [-]", ("TBR",)),
    ("q95 (cyl. proxy) [-]", ("q95_proxy", "q95")),
    ("βN (screening) [-]", ("beta_N", "betaN_proxy", "betaN")),
]


def point_summary_rows(out: Dict[str, Any]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for label, keys in _POINT_SUMMARY_KEYS:
        raw = None
        for key in keys:
            if key in out and out.get(key) is not None:
                raw = out.get(key)
                break
        if raw is None:
            continue
        try:
            v = float(raw)
            if v != v:
                val = "n/a"
            else:
                val = f"{v:.4g}"
        except (TypeError, ValueError):
            val = str(raw)
        rows.append({"quantity": label, "value": val})
    return rows


_RAW_TELEMETRY_PRIORITY = [
    "Ip_MA", "fG", "Ti_keV", "Paux_MW", "Pfus_total_MW", "H98", "Q_DT_eqv", "tauE_eff_s",
    "Ploss_MW", "Palpha_MW", "Prad_core_MW", "P_SOL_MW", "P_e_net_MW", "B_peak_T",
    "q95_proxy", "beta_N", "n_e20", "TBR", "feasible", "mirage_flag_v402",
]


def raw_telemetry_rows(out: Dict[str, Any], *, max_rows: int = 80) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    seen: set[str] = set()
    for key in _RAW_TELEMETRY_PRIORITY:
        if key in out and key not in seen:
            seen.add(key)
            rows.append({"key": key, "value": fmt_num(out.get(key))})
    for key in sorted(out.keys()):
        if len(rows) >= max_rows:
            break
        if key in seen or key.startswith("_"):
            continue
        val = out[key]
        if isinstance(val, (dict, list)):
            continue
        seen.add(key)
        rows.append({"key": str(key), "value": fmt_num(val) if isinstance(val, (int, float)) else str(val)})
    return rows[:max_rows]
