"""Physics deepening decks — 11 read-only cards (Streamlit parity)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from nicegui import ui

from ui_nicegui.components.kpi_row import kpi_row

DEEP_VIEWS = [
    "Regime & Confinement",
    "Global Dominance & Regime",
    "Current Profile & Current Drive",
    "Bootstrap–Pressure Self-Consistency Authority",
    "Current Drive Tech Authority",
    "Non-Inductive Closure Authority",
    "Burn & Alpha Power",
    "Impurities & Core Radiation",
    "Edge/Divertor & Exhaust Control",
    "Neutronics & Nuclear Loads",
    "Coupling Narratives",
]


def _sf(out: Dict[str, Any], key: str, *alts: str) -> float:
    for k in (key, *alts):
        if k not in out or out.get(k) is None:
            continue
        try:
            return float(out.get(k))
        except (TypeError, ValueError):
            continue
    return float("nan")


def _fmt(v: float, prec: int = 2) -> str:
    return f"{v:.{prec}f}" if v == v else "n/a"


def _claim_disp(out: Dict[str, Any], key: str, *alts: str, feasible: bool, prec: int = 2) -> str:
    """PHYS-KPI-001: watermark claim KPIs on INFEASIBLE deepening cards."""
    from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table, is_claim_kpi_key

    v = _sf(out, key, *alts)
    canon = key if is_claim_kpi_key(key) else next((a for a in alts if is_claim_kpi_key(a)), key)
    if is_claim_kpi_key(canon):
        return format_claim_kpi_for_table(canon, v, feasible=feasible, point_out=out, digits=prec)
    return _fmt(v, prec)


def _margin_rows(out: Dict[str, Any], prefix: str, replace: str = "") -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for k, v in sorted(out.items(), key=lambda kv: str(kv[0])):
        if not str(k).startswith(prefix):
            continue
        try:
            rows.append({"check": str(k).replace(replace, ""), "margin_frac": float(v)})
        except (TypeError, ValueError):
            rows.append({"check": str(k).replace(replace, ""), "margin_frac": float("nan")})
    return rows


def _table_from_dicts(rows: List[Dict[str, Any]], *, row_key: str = "check") -> None:
    if not rows:
        ui.label("(no rows)").classes("text-caption")
        return
    cols = [{"name": k, "label": k, "field": k, "align": "left"} for k in rows[0].keys()]
    ui.table(columns=cols, rows=rows[:50], row_key=row_key).classes("w-full")


def render_physics_deepening(out: Dict[str, Any], *, base: Optional[Any] = None) -> None:
    from ui_nicegui.lib.verdict_core import verdict_summary

    feasible = bool(verdict_summary(out).get("feasible"))
    if not feasible:
        ui.label(
            "PHYS-KPI-001: confinement / burn / performance KPIs below are diagnostic residue on an INFEASIBLE point — not design claims."
        ).classes("text-caption text-orange q-mb-sm")
    view_sel = ui.select(DEEP_VIEWS, label="Select deck", value=DEEP_VIEWS[0]).classes("w-full")
    panel = ui.column().classes("w-full")

    def _render() -> None:
        panel.clear()
        v = view_sel.value
        with panel:
            if v == "Regime & Confinement":
                kpi_row([
                    ("Regime label", str(out.get("confinement_regime", "unknown"))),
                    ("H98(y,2)", _claim_disp(out, "H98", feasible=feasible)),
                    ("H_regime", _fmt(_sf(out, "H_regime"))),
                    ("P_LH (MW)", _fmt(_sf(out, "P_LH_MW"), 1)),
                ])
                ui.label(
                    "H_regime is reported only when couple_regime_to_confinement=True. "
                    "H98 is always vs IPB98(y,2)."
                ).classes("text-caption")
                kpi_row([
                    ("H_scaling", _fmt(_sf(out, "H_scaling"))),
                    ("τE_eff (s)", _fmt(_sf(out, "tauE_eff_s", "tauE_eff", "tauE_s"))),
                    ("H_required", _fmt(_sf(out, "H_required"))),
                    ("τIPB98 (s)", _fmt(_sf(out, "tauIPB98_s", "tauIPB", "tauE_IPB98_s"))),
                ])
                spread = _sf(out, "transport_spread_ratio_v396")
                tier = str(out.get("transport_credibility_tier_v396", "") or "")
                if (spread == spread) or tier:
                    ui.label(
                        "v396 is a multi-scaling screening envelope (not a transport solver)."
                    ).classes("text-caption text-grey q-mb-xs")
                    kpi_row([
                        ("v396 spread τE_max/τE_min", _fmt(spread, 2) if spread == spread else "—"),
                        ("v396 credibility tier", tier or "—"),
                        ("τE env min (s)", _fmt(_sf(out, "tauE_envelope_min_s_v396"))),
                        ("τE env max (s)", _fmt(_sf(out, "tauE_envelope_max_s_v396"))),
                    ])

            elif v == "Global Dominance & Regime":
                if not bool(out.get("include_authority_dominance_v402", False)):
                    ui.label("Global dominance overlay is off — enable in Configure.").classes("text-caption")
                else:
                    kpi_row([
                        ("Regime class", str(out.get("regime_class_v402", "unknown"))),
                        ("Dominant authority", str(out.get("global_dominant_authority_v402", "unknown"))),
                        ("Min margin (frac)", f"{_sf(out, 'global_min_margin_v402'):+.3f}"),
                        ("Gap to #2", f"{_sf(out, 'dominance_gap_to_second_v402'):+.3f}"),
                    ])
                    if bool(out.get("mirage_flag_v402", False)):
                        ui.label("Feasibility mirage flagged by global dominance overlay.").classes("text-warning")
                        rs = out.get("mirage_reasons_v402", [])
                        if isinstance(rs, list) and rs:
                            ui.label("Reasons: " + ", ".join(str(x) for x in rs[:10])).classes("text-caption")
                    if bool(out.get("include_structural_life_v404", False)):
                        with ui.expansion("Structural life summary", icon="engineering").classes("w-full"):
                            ui.label(
                                f"Global min margin: {_sf(out, 'struct_global_min_margin_v404'):+.3f} | "
                                f"Dominant: {out.get('struct_dominant_component_v404', '?')} / "
                                f"{out.get('struct_dominant_mode_v404', '?')}"
                            )
                            tbl = out.get("struct_margin_table_v404", [])
                            if isinstance(tbl, list):
                                _table_from_dicts(tbl, row_key=list(tbl[0].keys())[0] if tbl else "check")
                    with ui.expansion("Dominance ranking table", icon="table_chart").classes("w-full"):
                        rows = out.get("dominance_order_v402", [])
                        if isinstance(rows, list):
                            _table_from_dicts(rows, row_key=list(rows[0].keys())[0] if rows else "authority")
                    if str(out.get("plasma_regime", "")):
                        kpi_row([
                            ("Plasma regime", str(out.get("plasma_regime", "unknown"))),
                            ("Burn regime", str(out.get("burn_regime", "-"))),
                            ("Fragility", str(out.get("plasma_fragility_class", "UNKNOWN"))),
                            ("Min margin (frac)", _fmt(_sf(out, "plasma_min_margin_frac"), 3)),
                        ])
                    if str(out.get("impurity_regime", "")):
                        kpi_row([
                            ("Impurity regime", str(out.get("impurity_regime", "unknown"))),
                            ("Species", str(out.get("impurity_species", "unknown"))),
                            ("Fragility", str(out.get("impurity_fragility_class", "UNKNOWN"))),
                            ("Min margin (frac)", _fmt(_sf(out, "impurity_min_margin_frac"), 3)),
                        ])

            elif v == "Current Profile & Current Drive":
                kpi_row([
                    ("Profile regime", str(out.get("current_profile_regime", "unknown"))),
                    ("Fragility", str(out.get("current_profile_fragility_class", "UNKNOWN"))),
                    ("Min margin (frac)", _fmt(_sf(out, "current_profile_min_margin_frac"), 3)),
                    ("Top limiter", str(out.get("current_profile_top_limiter", "UNKNOWN"))),
                ])
                kpi_row([
                    ("q95 proxy", _fmt(_sf(out, "q95_proxy"))),
                    ("qmin proxy", _fmt(_sf(out, "profile_qmin_proxy"))),
                    ("f_bootstrap proxy", _fmt(_sf(out, "profile_f_bootstrap_proxy") or _sf(out, "f_bs_proxy"))),
                    ("f_NI", _fmt(_sf(out, "f_NI"))),
                ])
                _eta_cd = _sf(out, "eta_CD_A_W", "cd_eta_A_per_W")
                kpi_row([
                    ("I_cd (MA)", _fmt(_sf(out, "I_cd_MA"))),
                    ("P_cd (MW)", _fmt(_sf(out, "P_CD_MW", "P_cd_MW"), 1)),
                    ("eta_CD (A/W)", f"{_eta_cd:.3e}" if _eta_cd == _eta_cd else "n/a"),
                    ("Contract hash", str(out.get("current_profile_contract_sha256", ""))[:12]),
                ])
                with ui.expansion("Current-profile authority margins", icon="rule").classes("w-full"):
                    _table_from_dicts(_margin_rows(out, "current_profile_CP_", "current_profile_"))

            elif v == "Bootstrap–Pressure Self-Consistency Authority":
                mm = _sf(out, "bsp_min_margin_frac")
                kpi_row([
                    ("Regime", str(out.get("bsp_regime", "unknown"))),
                    ("Fragility", str(out.get("bsp_fragility_class", "UNKNOWN"))),
                    ("Min margin (frac)", "—" if mm != mm else f"{mm:+.3f}"),
                    ("Top limiter", str(out.get("bsp_top_limiter", "UNKNOWN"))),
                ])
                kpi_row([
                    ("|Δf_bs|", _fmt(_sf(out, "bsp_abs_delta_f_bootstrap"), 3)),
                    ("Tol |Δf_bs|", _fmt(_sf(out, "bsp_abs_delta_max"), 3)),
                    ("f_bs (reported)", _fmt(_sf(out, "bsp_f_bootstrap_reported"))),
                    ("f_bs (expected)", _fmt(_sf(out, "bsp_f_bootstrap_expected"))),
                ])

            elif v == "Current Drive Tech Authority":
                kpi_row([
                    ("CD tech regime", str(out.get("cd_tech_regime", "unknown"))),
                    ("Fragility", str(out.get("cd_fragility_class", "UNKNOWN"))),
                    ("Min margin (frac)", _fmt(_sf(out, "cd_min_margin_frac"), 3)),
                    ("Top limiter", str(out.get("cd_top_limiter", "UNKNOWN"))),
                ])
                rows = []
                for k, val in out.items():
                    if isinstance(k, str) and k.startswith("cd_") and "_margin_frac" in k:
                        try:
                            rows.append({"metric": k, "value": float(val)})
                        except (TypeError, ValueError):
                            pass
                rows.sort(key=lambda r: (0 if r["value"] == r["value"] else 1, r["value"]))
                with ui.expansion("CD tech margins", icon="table_chart").classes("w-full"):
                    _table_from_dicts(rows or [{"metric": "(none)", "value": float("nan")}], row_key="metric")

            elif v == "Non-Inductive Closure Authority":
                mm = _sf(out, "ni_min_margin_frac")
                kpi_row([
                    ("NI regime", str(out.get("ni_closure_regime", "unknown"))),
                    ("Fragility", str(out.get("ni_fragility_class", "UNKNOWN"))),
                    ("Min margin (frac)", "—" if mm != mm else f"{mm:+.3f}"),
                    ("Top limiter", str(out.get("ni_top_limiter", "UNKNOWN"))),
                ])
                ni_rows = []
                for k, val in out.items():
                    if isinstance(k, str) and k.startswith("ni_") and k.endswith("_margin_frac"):
                        try:
                            ni_rows.append({"margin_id": k, "margin_frac": float(val)})
                        except (TypeError, ValueError):
                            pass
                if ni_rows:
                    with ui.expansion("NI closure margins", icon="table_chart").classes("w-full"):
                        _table_from_dicts(sorted(ni_rows, key=lambda r: r["margin_frac"]), row_key="margin_id")

            elif v == "Burn & Alpha Power":
                kpi_row([
                    ("Pα (MW)", _fmt(_sf(out, "Palpha_MW"), 1)),
                    ("Ploss (MW)", _fmt(_sf(out, "Ploss_MW"), 1)),
                    ("M_ign = Pα/Ploss", _fmt(_sf(out, "M_ign"))),
                    ("M_ign_total", _fmt(_sf(out, "M_ign_total"))),
                ])

            elif v == "Impurities & Core Radiation":
                kpi_row([
                    ("Radiation enabled", "YES" if bool(out.get("include_radiation", False)) else "NO"),
                    ("Prad_core (MW)", _fmt(_sf(out, "Prad_core_MW"), 1)),
                    ("Zeff (input)", _fmt(_sf(out, "zeff"))),
                    ("Radiation model", str(out.get("radiation_model", "-"))),
                ])

            elif v == "Edge/Divertor & Exhaust Control":
                ui.label(
                    "q_div is an Eich λq / wetted-area engineering proxy — screening cliff cartography only, "
                    "not an absolute SOLPS heat-flux design margin."
                ).classes("text-caption text-grey q-mb-xs")
                kpi_row([
                    ("q_div proxy (MW/m²)", _fmt(_sf(out, "q_div_MW_m2"), 1)),
                    ("q_div limit", _fmt(_sf(out, "q_div_max_MW_m2"), 1)),
                    ("f_rad_div", _fmt(_sf(out, "f_rad_div"))),
                    ("Divertor regime", str(out.get("div_regime", "unknown"))),
                ])
                if str(out.get("exhaust_regime", "")):
                    kpi_row([
                        ("Exhaust regime", str(out.get("exhaust_regime", "unknown"))),
                        ("Fragility", str(out.get("exhaust_fragility_class", "UNKNOWN"))),
                        ("Min margin (frac)", _fmt(_sf(out, "exhaust_min_margin_frac"), 3)),
                        ("Radiation-dom", "YES" if _sf(out, "exhaust_radiation_dominated") >= 0.5 else "NO"),
                    ])
                if base is not None and bool(getattr(base, "include_sol_radiation_control", False)):
                    kpi_row([
                        ("q_target", _fmt(_sf(out, "q_div_target_MW_m2"), 1)),
                        ("f_SOL+div,req", _fmt(_sf(out, "detachment_f_sol_div_required"))),
                        ("P_rad,SOL+div req (MW)", _fmt(_sf(out, "detachment_prad_sol_div_required_MW"), 1)),
                        ("f_z,required", f"{_sf(out, 'detachment_f_z_required'):.1e}"),
                    ])
                elm_on = bool(out.get("include_elm_transient_heat_v409"))
                if elm_on:
                    elm_q = _sf(out, "elm_transient_q_parallel_MW_m2_v409")
                    ui.label(
                        "ELM v409 — transient parallel heat-flux screening proxy "
                        "(artifact overlay; not a SOLPS ELM model)."
                    ).classes("text-caption text-grey q-mb-xs")
                    q_max = _sf(out, "elm_transient_q_parallel_max_MW_m2_v409")
                    margin = float("nan")
                    if elm_q == elm_q and q_max == q_max and q_max > 0.0:
                        margin = (q_max - elm_q) / q_max
                    kpi_row([
                        ("ELM overlay", "ON"),
                        ("ELM q∥ proxy (MW/m²)", _fmt(elm_q, 1)),
                        ("ELM q∥ max", _fmt(q_max, 1)),
                        ("ELM margin (frac)", _fmt(margin, 3)),
                    ])

            elif v == "Neutronics & Nuclear Loads":
                kpi_row([
                    ("n-wall load (MW/m²)", _fmt(_sf(out, "neutron_wall_load_MW_m2"))),
                    ("TBR (proxy)", _fmt(_sf(out, "TBR"))),
                    ("HTS lifetime (yr)", _fmt(_sf(out, "hts_lifetime_yr"), 1)),
                    ("FW dpa/y", _fmt(_sf(out, "fw_dpa_per_year"))),
                ])
                ui.label(
                    f"Neutronics/Materials regime: {out.get('neutronics_materials_regime', 'unknown')} | "
                    f"Fragility: {out.get('neutronics_materials_fragility_class', 'UNKNOWN')} | "
                    f"Min margin: {_sf(out, 'neutronics_materials_min_margin_frac'):.3f}"
                ).classes("text-caption")
                if bool(out.get("include_neutronics_materials_library_v403", False)):
                    ui.label(
                        f"Nuclear materials library: tier {out.get('nm_regime_tier_v403', 'UNKNOWN')} | "
                        f"TBR proxy {_sf(out, 'tbr_proxy_v403'):.2f} | FW DPA {_sf(out, 'dpa_fw_v403'):.2f}"
                    ).classes("text-caption")
                    with ui.expansion("In-vessel materials stack ledger", icon="layers").classes("w-full"):
                        layers = out.get("nm_stack_layers_v403", [])
                        if isinstance(layers, list) and layers:
                            _table_from_dicts(layers, row_key=list(layers[0].keys())[0])
                kpi_row([
                    ("Stack attenuation", f"{_sf(out, 'neutron_attenuation_factor'):.3g}"),
                    ("P_nuc,total (MW)", _fmt(_sf(out, "P_nuc_total_MW"))),
                    ("P_nuc,TF (MW)", _fmt(_sf(out, "P_nuc_TF_MW"))),
                    ("FW life (yr)", _fmt(_sf(out, "fw_lifetime_yr"), 1)),
                ])
                tbr_val = out.get("TBR_validity")
                if isinstance(tbr_val, str) and tbr_val.strip():
                    tbr_disp = tbr_val.strip()
                else:
                    # Legacy numeric plot flag from materials authority: 0.0=proxy, 1.0=out_of_range.
                    # Never map 0.0 → "OK" — that reads as neutronics-validated, not screening proxy.
                    tv = _sf(out, "TBR_validity")
                    if tv == tv:  # finite
                        tbr_disp = "proxy" if tv < 0.5 else "out_of_range"
                    else:
                        tbr_disp = "—"
                kpi_row([
                    ("FW material", str(out.get("fw_material", "-"))),
                    ("Blanket material", str(out.get("blanket_material", "-"))),
                    ("Shield material", str(out.get("shield_material", "-"))),
                    ("TBR validity", tbr_disp),
                ])

            elif v == "Coupling Narratives":
                ui.label(
                    "Deterministic coupling narratives from authority dominance + regime labels."
                ).classes("text-caption")
                csum = str(out.get("coupling_summary", "") or "")
                if csum:
                    ui.label(csum).classes("text-body2")
                try:
                    sev_i = int(out.get("coupling_severity_max", 0))
                except (TypeError, ValueError):
                    sev_i = 0
                ui.label(f"Max severity: {sev_i}/5").classes("text-subtitle2")
                cn = out.get("coupling_narratives", {})
                items = cn.get("coupling_narratives", []) if isinstance(cn, dict) else []
                if not items:
                    ui.label("No coupling flags triggered for this evaluation.").classes("text-caption")
                else:
                    for it in items[:20]:
                        if isinstance(it, dict):
                            ui.markdown(
                                f"**{it.get('title', 'Coupling')}** (severity {it.get('severity', '?')}): "
                                f"{it.get('narrative', it.get('message', ''))}"
                            )

    view_sel.on("update:model-value", lambda: _render())
    _render()
