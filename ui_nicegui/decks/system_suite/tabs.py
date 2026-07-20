"""System Suite tab bodies — 5-tab workflow, expert-friendly sections."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.suite_labels import ENVELOPE_ROUTER
from ui_nicegui.lib.suite_overlay_helpers import stamp_label
from ui_nicegui.lib.suite_helpers import (
    SUITE_RUNLOCK_OWNER,
    envelope_posture_summary,
    lifetime_binding_summary,
    release_suite_lock,
    render_authority_ledger,
    render_export_bar,
    render_impurity_radiation_panel,
    render_suite_handoffs,
    render_tab_summary_strip,
    try_acquire_suite_lock,
)
from ui_nicegui.lib.helm_helpers import log_ui_event
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


@dataclass
class SuiteContext:
    session: DesignSession
    artifact: Optional[dict[str, Any]]
    point_inp: Optional[dict[str, Any]]
    point_out: dict[str, Any]
    overlays: dict[str, Any]


def _fin(v: Any, fmt: str = ".2f") -> str:
    try:
        f = float(v)
        if not math.isfinite(f):
            return "-"
        return format(f, fmt)
    except (TypeError, ValueError):
        return "-"


def _plot_lines(x, series: dict[str, list], *, height: int = 220, title: str = "") -> None:
    import plotly.graph_objects as go

    fig = go.Figure()
    for name, y in series.items():
        fig.add_trace(go.Scatter(x=list(x), y=list(y), mode="lines", name=name))
    fig.update_layout(
        margin=dict(l=20, r=20, t=30 if title else 20, b=20),
        height=height,
        showlegend=True,
        title=title or None,
    )
    ui.plotly(fig).classes("w-full")


def _expansion_defaults(session: DesignSession, *, panel_id: str, default_open: bool) -> bool:
    if session.suite_expert_view:
        return False
    if not session.suite_teaching_mode:
        return default_open
    focus = {
        "ops_duty": session.suite_workflow_step == "2 · Operations & Thermal",
        "ops_thermal": session.suite_workflow_step == "2 · Operations & Thermal",
        "ops_traj": session.suite_workflow_step == "2 · Operations & Thermal",
        "ops_impurity": session.suite_workflow_step == "2 · Operations & Thermal",
        "life_budgets": session.suite_workflow_step == "3 · Lifetime & Regimes",
        "life_regime": session.suite_workflow_step == "3 · Lifetime & Regimes",
        "env_phase": session.suite_workflow_step == "4 · Envelope Robustness",
        "env_profile": session.suite_workflow_step == "4 · Envelope Robustness",
        "env_uq": session.suite_workflow_step == "4 · Envelope Robustness",
        "scen_library": session.suite_workflow_step == "5 · Scenarios & Exports",
        "scen_campaign": session.suite_workflow_step == "5 · Scenarios & Exports",
        "scen_parity": session.suite_workflow_step == "5 · Scenarios & Exports",
    }
    return focus.get(panel_id, default_open)


# ---------------------------------------------------------------------------
# Tab 1 · Plant & Power
# ---------------------------------------------------------------------------


def render_tab_plant_power(ctx: SuiteContext) -> None:
    from ui_nicegui.lib.plant_kpi_honesty_ui import (
        pe_net_display,
        plant_kpi_honesty_for_point,
        render_plant_kpi_watermark_banner,
    )

    fn = ctx.overlays.get("power_closure_overlay")
    if fn is None:
        empty_state("Power closure overlay unavailable.", kind="warn")
        return
    rep = fn(ctx.point_out, ctx.point_inp)
    honesty = plant_kpi_honesty_for_point(
        ctx.point_out,
        artifact=ctx.artifact,
        design_intent=str(getattr(ctx.session, "design_intent", "") or ""),
    )
    pe_disp = pe_net_display(
        ctx.point_out,
        artifact=ctx.artifact,
        design_intent=str(getattr(ctx.session, "design_intent", "") or ""),
    )
    banner = render_plant_kpi_watermark_banner(
        ctx.point_out,
        artifact=ctx.artifact,
        design_intent=str(getattr(ctx.session, "design_intent", "") or ""),
    )
    if banner:
        ui.badge(banner, color="orange").props("outline").classes("q-mb-xs")
        ui.label(str(honesty.get("message") or "")).classes("text-caption text-orange q-mb-sm")
    render_tab_summary_strip(
        "PLANT CLOSURE",
        detail="Gross, recirculating, and net electric from plant overlay.",
        kpis=[
            ("Gross electric (MW)", _fin(rep.Pe_gross_MW)),
            ("Recirc (MW)", _fin(rep.Precirc_MW)),
            ("Net electric (MW)", pe_disp),
            ("Recirc fraction", f"{100.0 * rep.recirc_frac:.1f}%" if math.isfinite(rep.recirc_frac) else "-"),
        ],
    )
    ui.label("Power closure ledger").classes("text-subtitle1 q-mt-sm")
    ui.label("Gross, recirculating, and net electric power from the plant overlay.").classes(
        "text-caption q-mb-sm"
    )
    kpi_row([
        ("Gross electric (MW)", _fin(rep.Pe_gross_MW)),
        ("Recirc (MW)", _fin(rep.Precirc_MW)),
        ("Net electric (MW)", pe_disp),
        ("Recirc fraction", f"{100.0 * rep.recirc_frac:.1f}%" if math.isfinite(rep.recirc_frac) else "-"),
    ])
    if not honesty.get("claim_allowed"):
        with ui.expansion("Raw Pe_net bookkeeping (diagnostic)", icon="science").classes("w-full"):
            ui.label(
                f"Raw Pe_net={_fin(rep.Pe_net_MW)} MW — not a certified net-electric claim "
                f"(watermark={honesty.get('watermark')})."
            ).classes("text-caption")
    stamp_label(rep.stamp_sha256)
    with ui.expansion("Breakdown (diagnostic)", icon="data_object").classes("w-full"):
        ui.code(json.dumps(rep.breakdown, indent=2, sort_keys=True), language="json")
    with ui.expansion(
        "Authority ledger",
        icon="account_balance",
        value=not ctx.session.suite_expert_view,
    ).classes("w-full q-mt-sm"):
        render_authority_ledger(
            ctx.point_out,
            expert=ctx.session.suite_expert_view,
            artifact=ctx.artifact,
            design_intent=str(getattr(ctx.session, "design_intent", "") or ""),
        )


# ---------------------------------------------------------------------------
# Tab 2 · Operations & Thermal
# ---------------------------------------------------------------------------


@ui.refreshable
def _render_duty_panel(ctx: SuiteContext) -> None:
    from ui_nicegui.lib.plant_kpi_honesty_ui import (
        plant_kpi_honesty_for_point,
        render_plant_kpi_watermark_banner,
    )

    fn = ctx.overlays.get("ops_availability_overlay")
    if fn is None:
        empty_state("Operations overlay unavailable.", kind="warn")
        return
    rep = fn(
        ctx.point_out,
        ctx.point_inp,
        availability=float(ctx.session.suite_availability),
    )
    honesty = plant_kpi_honesty_for_point(
        ctx.point_out,
        artifact=ctx.artifact,
        design_intent=str(getattr(ctx.session, "design_intent", "") or ""),
    )
    banner = render_plant_kpi_watermark_banner(
        ctx.point_out,
        artifact=ctx.artifact,
        design_intent=str(getattr(ctx.session, "design_intent", "") or ""),
    )
    if banner:
        ui.badge(banner, color="orange").props("outline").classes("q-mb-xs")
    # Independence 1.2: do not show healthy delivered energy on hard-infeasible points.
    if honesty.get("claim_allowed"):
        avg_disp = _fin(rep.avg_delivered_MW)
        ann_disp = _fin(rep.annual_energy_GWh, ".1f")
    else:
        avg_disp = "— (diagnostic)"
        ann_disp = "— (diagnostic)"
    kpi_row([
        ("Duty cycle", f"{100.0 * rep.duty_cycle:.1f}%"),
        ("Availability", f"{100.0 * rep.availability:.1f}%"),
        ("Avg delivered (MW)", avg_disp),
        ("Annual energy (GWh)", ann_disp),
    ])
    stamp_label(rep.stamp_sha256)
    with ui.expansion("Breakdown (diagnostic)", icon="data_object").classes("w-full"):
        ui.code(json.dumps(rep.breakdown, indent=2, sort_keys=True), language="json")


def render_tab_ops_thermal(ctx: SuiteContext) -> None:
    fn_duty = ctx.overlays.get("ops_availability_overlay")
    fn_thermal = ctx.overlays.get("thermal_network_diagnostics_client")
    fn_traj = ctx.overlays.get("trajectory_diagnostics_client")
    duty_rep = fn_duty(ctx.point_out, ctx.point_inp, availability=float(ctx.session.suite_availability)) if fn_duty else None
    thermal_rep = fn_thermal(ctx.point_out, ctx.point_inp) if fn_thermal else None
    traj_rep = fn_traj(ctx.point_out, ctx.point_inp) if fn_traj else None
    n_therm_v = len(thermal_rep.violations) if thermal_rep and thermal_rep.violations else 0
    n_traj_v = len(traj_rep.violations) if traj_rep and traj_rep.violations else 0
    traj_incomplete = bool(getattr(traj_rep, "meta", {}) or {}).get("power_incomplete") if traj_rep else False

    def _has_thermal_limit(d: dict, key: str) -> bool:
        try:
            return math.isfinite(float(d.get(key)))
        except (TypeError, ValueError):
            return False

    _inp = ctx.point_inp or {}
    _out = ctx.point_out or {}
    thermal_limits_configured = any(
        _has_thermal_limit(_inp, k) or _has_thermal_limit(_out, k) for k in ("T_fw_max_K", "T_div_max_K")
    )
    if traj_incomplete or n_therm_v > 0 or n_traj_v > 0:
        thermal_posture = "OPS / THERMAL REVIEW"
    elif not thermal_limits_configured:
        thermal_posture = "THERMAL LIMITS N/A"
    else:
        thermal_posture = "THERMAL PASS"
    render_tab_summary_strip(
        thermal_posture,
        detail=(
            f"Thermal violations: {n_therm_v} · Trajectory violations: {n_traj_v}"
            + (" · Net power incomplete on point" if traj_incomplete else "")
            + ("" if thermal_limits_configured else " · No T_fw/T_div limits configured")
        ),
        kpis=[
            ("Availability", f"{100.0 * ctx.session.suite_availability:.0f}%"),
            ("Avg delivered (MW)", _fin(duty_rep.avg_delivered_MW) if duty_rep else "-"),
            ("Annual energy (GWh)", _fin(duty_rep.annual_energy_GWh, ".1f") if duty_rep else "-"),
        ] if duty_rep else None,
    )

    open_duty = _expansion_defaults(ctx.session, panel_id="ops_duty", default_open=True)

    with ui.expansion("Plant availability sensitivity", icon="schedule", value=open_duty).classes("w-full"):
        ui.badge("Sensitivity probe", color="blue").props("outline q-mb-xs")
        ui.label(
            "Scales delivered energy from the frozen point — does not re-run plasma physics."
        ).classes("text-caption q-mb-sm")
        ui.slider(
            min=0.0,
            max=1.0,
            step=0.01,
            value=ctx.session.suite_availability,
            on_change=lambda e: (
                setattr(ctx.session, "suite_availability", float(e.value)),
                _render_duty_panel.refresh(),
            ),
        ).props('label="Availability (0–1 fraction; KPIs show %)"')
        _render_duty_panel(ctx)

    with ui.expansion(
        "Thermal network trace",
        icon="thermostat",
        value=_expansion_defaults(ctx.session, panel_id="ops_thermal", default_open=False),
    ).classes("w-full q-mt-sm"):
        ui.label("Node temperatures vs time; flags limit violations when limits exist.").classes(
            "text-caption q-mb-sm"
        )
        fn = ctx.overlays.get("thermal_network_diagnostics_client")
        if fn is None:
            empty_state("Thermal diagnostics unavailable.", kind="warn")
        else:
            tr = fn(ctx.point_out, ctx.point_inp)
            stamp_label(tr.stamp_sha256)
            series = {f"T_{k}_K": v for k, v in tr.nodes_K.items()}
            _plot_lines(tr.t_s, series, title="Thermal nodes")
            if tr.violations:
                ui.label("Thermal violations detected.").classes("text-negative text-subtitle2")
                ui.table(
                    columns=[
                        {"name": k, "label": k, "field": k, "align": "left"}
                        for k in tr.violations[0].keys()
                    ]
                    if tr.violations
                    else [],
                    rows=tr.violations,
                ).classes("w-full")
            else:
                inp = ctx.point_inp or {}
                out = ctx.point_out or {}

                def _has_limit(d: dict, key: str) -> bool:
                    try:
                        return math.isfinite(float(d.get(key)))
                    except (TypeError, ValueError):
                        return False

                limits_configured = any(
                    _has_limit(inp, k) or _has_limit(out, k) for k in ("T_fw_max_K", "T_div_max_K")
                )
                ui.label(
                    "No thermal violations (within configured limits)."
                    if limits_configured
                    else "No thermal limits configured — pass is not asserted."
                ).classes("text-caption")
            with ui.expansion("Thermal metadata", icon="info").classes("w-full"):
                render_json_blob(getattr(tr, "meta", {}) or {})

    with ui.expansion(
        "Pulse power trajectory",
        icon="show_chart",
        value=_expansion_defaults(ctx.session, panel_id="ops_traj", default_open=False),
    ).classes("w-full q-mt-sm"):
        ui.label("Deterministic pulse envelope — not a control solver.").classes("text-caption q-mb-sm")
        fn = ctx.overlays.get("trajectory_diagnostics_client")
        if fn is None:
            empty_state("Trajectory diagnostics unavailable.", kind="warn")
        else:
            tr = fn(ctx.point_out, ctx.point_inp)
            if tr.meta.get("power_incomplete"):
                empty_state(
                    "Net electric power unavailable on this point — trajectory trace not meaningful.",
                    kind="warn",
                )
            else:
                kpi_row([
                    ("Net peak (MW)", _fin(tr.meta.get("Pnet_peak_MW", 0.0))),
                    ("Net avg (MW)", _fin(tr.meta.get("Pnet_avg_MW", 0.0))),
                    ("Recirc peak (MW)", _fin(tr.meta.get("Precirc_peak_MW", 0.0))),
                    ("Recirc energy (MJ)", _fin(tr.meta.get("Erecirc_MJ", 0.0), ".1f")),
                ])
                stamp_label(tr.stamp_sha256)
                _plot_lines(tr.t_s, {"P_net_MW": tr.Pe_net_MW, "P_recirc_MW": tr.Precirc_MW}, title="Pulse power")
                if tr.violations:
                    ui.label("Trajectory violations detected.").classes("text-negative")
                    ui.table(
                        columns=[
                            {"name": k, "label": k, "field": k, "align": "left"}
                            for k in tr.violations[0].keys()
                        ]
                        if tr.violations
                        else [],
                        rows=tr.violations,
                    ).classes("w-full")
                else:
                    ui.label("No trajectory violations.").classes("text-positive text-caption")
            ui.label(
                "Recirc peak proxies P_aux wallplug when split unavailable — diagnostic only."
            ).classes("text-caption text-grey q-mt-xs")

    with ui.expansion(
        "Impurity & Radiation (SOL / prad / detachment)",
        icon="opacity",
        value=_expansion_defaults(ctx.session, panel_id="ops_impurity", default_open=False),
    ).classes("w-full q-mt-sm"):
        render_impurity_radiation_panel(ctx.point_out, expert=ctx.session.suite_expert_view)


# ---------------------------------------------------------------------------
# Tab 3 · Lifetime & Regimes
# ---------------------------------------------------------------------------


def render_tab_lifetime_regimes(ctx: SuiteContext) -> None:
    fn = ctx.overlays.get("lifetime_and_fuel_overlay")
    lr = fn(ctx.point_out, ctx.point_inp) if fn else None
    if lr:
        bind = lifetime_binding_summary(lr)
        if bind["binding"]:
            detail = f"Worst margin: {bind['worst_name']} ({bind['worst_margin']:.3f})"
        elif bind.get("unknown"):
            detail = (
                "Some lifetime margins unavailable — not certified within budget. "
                "TBR is a screening proxy, not neutron-transport certified."
            )
        else:
            detail = (
                "FW dpa, cycles, and TBR (proxy) within configured budgets — "
                "TBR is screening-level, not neutron-transport certified."
            )
        render_tab_summary_strip(
            bind["posture"],
            detail=detail,
            kpis=[
                ("FW dpa margin", _fin(lr.fw_dpa_margin)),
                ("Cycle margin (yr proxy)", _fin(lr.cycles_margin)),
                ("TBR margin (proxy)", _fin(lr.tbr_margin, ".3f")),
            ],
        )

    with ui.expansion(
        "Lifetime & tritium budgets",
        icon="shield",
        value=_expansion_defaults(ctx.session, panel_id="life_budgets", default_open=True),
    ).classes("w-full"):
        ui.label("First-wall dpa, pulsed cycle limits, and tritium breeding ratio margins.").classes(
            "text-caption q-mb-sm"
        )
        fn = ctx.overlays.get("lifetime_and_fuel_overlay")
        if fn is None:
            empty_state("Lifetime/fuel overlay unavailable.", kind="warn")
        else:
            lr = fn(ctx.point_out, ctx.point_inp)
            kpi_row([
                ("FW dpa/yr", _fin(lr.fw_dpa_per_year)),
                ("FW dpa max", _fin(lr.fw_dpa_max_per_year)),
                ("FW margin", _fin(lr.fw_dpa_margin)),
            ])
            kpi_row([
                ("Cycles/yr", _fin(lr.cycles_per_year, ".0f")),
                ("Cycles max", _fin(lr.cycles_max, ".0f")),
                ("Cycle margin (yr proxy)", _fin(lr.cycles_margin)),
            ])
            kpi_row([
                ("TBR (proxy)", _fin(lr.tbr, ".3f")),
                ("TBR min", _fin(lr.tbr_min, ".3f")),
                ("TBR margin", _fin(lr.tbr_margin, ".3f")),
            ])
            ui.label(
                "TBR is a screening-level breeding-ratio proxy — no certified neutron-transport TBR in L0."
            ).classes("text-caption text-grey q-mb-xs")
            bind = lifetime_binding_summary(lr)
            if bind["binding"]:
                ui.label(f"Binding: {', '.join(bind['binding'])}").classes("text-negative text-caption")
            stamp_label(lr.stamp_sha256)
            with ui.expansion("Overlay JSON", icon="data_object").classes("w-full"):
                render_json_blob({
                    "fw": {
                        "dpa_per_year": lr.fw_dpa_per_year,
                        "dpa_max": lr.fw_dpa_max_per_year,
                        "margin": lr.fw_dpa_margin,
                    },
                    "cycles": {
                        "per_year": lr.cycles_per_year,
                        "max": lr.cycles_max,
                        "margin": lr.cycles_margin,
                    },
                    "tbr": {"tbr": lr.tbr, "min": lr.tbr_min, "margin": lr.tbr_margin},
                    "stamp": lr.stamp_sha256,
                })

    with ui.expansion(
        "Operating regime labels",
        icon="hub",
        value=_expansion_defaults(ctx.session, panel_id="life_regime", default_open=False),
    ).classes("w-full q-mt-sm"):
        ui.label("Confinement, exhaust, magnet, Greenwald, and βN state from the last point.").classes(
            "text-caption q-mb-sm"
        )
        rt = None
        source = "computed now"
        if isinstance(ctx.artifact, dict) and isinstance(ctx.artifact.get("regime_transitions"), dict):
            rt = ctx.artifact["regime_transitions"]
            source = "cached on Point Designer artifact"
        if not isinstance(rt, dict):
            try:
                try:
                    from src.analysis.regime_transition_detector_v353 import evaluate_regime_transitions
                except Exception:
                    from analysis.regime_transition_detector_v353 import evaluate_regime_transitions  # type: ignore
                rt = evaluate_regime_transitions(
                    inputs=ctx.point_inp or {},
                    outputs=ctx.point_out,
                )
                source = "computed now"
            except Exception:
                rt = None
        if not isinstance(rt, dict):
            empty_state("Regime transition detector unavailable.", kind="warn")
        else:
            ui.label(f"Source: {source}").classes("text-caption text-grey q-mb-xs")
            summary = str(rt.get("regime_summary", "") or "")
            if summary:
                ui.markdown(summary)
            labels = rt.get("labels", {}) if isinstance(rt.get("labels"), dict) else {}
            kpi_row([
                ("Confinement", str(labels.get("confinement_regime", "-"))),
                ("Exhaust", str(labels.get("exhaust_regime", "-"))),
                ("Magnet", str(labels.get("magnet_regime", "-"))),
                ("Greenwald", str(labels.get("greenwald_state", "-"))),
                ("βN", str(labels.get("betaN_state", "-"))),
            ])
            with ui.expansion("Near-boundary flags", icon="warning").classes("w-full"):
                ui.code(json.dumps(rt.get("near_boundaries", []), indent=2), language="json")
            with ui.expansion("Detector context", icon="info").classes("w-full"):
                render_json_blob(rt.get("context", {}) or {})


# ---------------------------------------------------------------------------
# Tab 4 · Envelope Robustness
# ---------------------------------------------------------------------------


def _render_profile_corners(ctx: SuiteContext) -> None:
    if not isinstance(ctx.point_inp, dict):
        empty_state("Point Designer inputs required.", kind="info")
        return
    try:
        try:
            from src.analysis.profile_contracts_v362 import evaluate_profile_contracts_v362
        except Exception:
            from analysis.profile_contracts_v362 import evaluate_profile_contracts_v362  # type: ignore
    except Exception:
        empty_state("Profile corner module unavailable.", kind="error")
        return
    try:
        from src.models.inputs import PointInputs
    except Exception:
        from models.inputs import PointInputs  # type: ignore

    with ui.row().classes("gap-4 flex-wrap"):
        preset = ui.select(["C8", "C16", "C32"], label="Corner preset", value="C8").classes("w-32")
        tier = ui.select(["both", "optimistic", "robust"], label="Contract tier", value="both").classes("w-36")
        force_lib = ui.checkbox("Include extended profile library", value=False)

    if ctx.session.suite_teaching_mode:
        ui.label(
            "Robust pass = envelope-certified; optimistic pass with robust fail = certification gap only."
        ).classes("text-caption q-mb-sm")
    else:
        ui.label(
            "Tip: robust-feasible implies envelope-certified; optimistic-only pass is a certification gap (not envelope-certified)."
        ).classes("text-caption text-grey q-mb-sm")

    async def _run() -> None:
        if not try_acquire_suite_lock(ctx.session, "System Suite: Profile corners"):
            return
        log_ui_event(ctx.session, SUITE_RUNLOCK_OWNER, "ProfileCornersStart", {"preset": str(preset.value)})
        try:
            d = dict(ctx.point_inp or {})
            if force_lib.value:
                d["include_profile_family_v358"] = True
            inp = PointInputs.from_dict(d)
            rep = await run.io_bound(
                evaluate_profile_contracts_v362,
                inp,
                preset=str(preset.value),
                tier=str(tier.value),
            )
            ctx.session.profile_contracts_v362_last = rep.to_dict()
            log_ui_event(
                ctx.session,
                SUITE_RUNLOCK_OWNER,
                "ProfileCornersComplete",
                {"robust": bool(rep.to_dict().get("robust_feasible"))},
            )
            _pc_results.refresh()
        except Exception as exc:
            ui.notify(f"Profile corners failed: {exc}", type="negative")
        finally:
            release_suite_lock(ctx.session)

    ui.button("Run profile corners", on_click=_run, color="primary").props("q-mb-sm")

    @ui.refreshable
    def _pc_results() -> None:
        rep_d = ctx.session.profile_contracts_v362_last
        if not isinstance(rep_d, dict):
            empty_state("Run profile corners to evaluate C8/C16/C32 certification.", kind="info")
            return
        v_rob = bool(rep_d.get("robust_feasible"))
        v_opt = bool(rep_d.get("optimistic_feasible"))
        gap = bool(rep_d.get("mirage"))
        kpi_row([
            ("Optimistic feasible", "YES" if v_opt else "NO"),
            ("Robust feasible", "YES" if v_rob else "NO"),
            ("Certification gap", "YES" if gap else "NO"),
            ("Corners", str(rep_d.get("corner_count", "-"))),
        ])
        sha = str(rep_d.get("contract_sha256", ""))
        fp = str(rep_d.get("run_fingerprint_sha256", ""))
        ui.label(f"Contract fingerprint: {sha[:12]}… | Run: {fp[:12]}…").classes("text-caption")
        with ui.expansion("Summary", icon="summarize").classes("w-full"):
            render_json_blob(rep_d.get("summary", {}))
        rows = []
        for c in rep_d.get("corners", []) or []:
            if not isinstance(c, dict):
                continue
            row = {
                "tier": c.get("tier"),
                "corner": c.get("corner_index"),
                "hard_feasible": c.get("hard_feasible"),
                "min_margin_frac": c.get("min_margin_frac"),
            }
            for k, v in (c.get("axes") or {}).items():
                row[f"ax_{k}"] = v
            rows.append(row)
        if rows:
            cols = list(rows[0].keys())
            with ui.expansion("Corner table", icon="table_chart").classes("w-full"):
                ui.table(
                    columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
                    rows=rows,
                    row_key="corner",
                ).classes("w-full")
        with ui.expansion("Full report JSON", icon="data_object").classes("w-full"):
            render_json_blob(rep_d)

        async def _export_zip() -> None:
            try:
                from tools.profile_contracts_v362 import export_profile_contracts_zip
            except ImportError:
                ui.notify("Export module unavailable", type="negative")
                return
            td = Path(__import__("tempfile").gettempdir()) / "shams_profile_contracts"
            td.mkdir(parents=True, exist_ok=True)
            out_zip = td / "profile_corners_report.zip"

            def _run():
                export_profile_contracts_zip(rep_d, out_zip)
                return out_zip.read_bytes()

            data = await run.io_bound(_run)
            ui.download(data, "profile_corners_report.zip")
            ui.notify("Profile corners ZIP ready", type="positive")

        ui.button("Export profile corners ZIP", icon="archive", on_click=_export_zip).props("outline q-mt-sm")

    _pc_results()


def render_tab_envelope_robustness(ctx: SuiteContext) -> None:
    render_tab_summary_strip(
        "ENVELOPE ROBUSTNESS",
        detail=envelope_posture_summary(ctx.session),
    )
    ui.markdown(ENVELOPE_ROUTER).classes("text-caption q-mb-md")

    with ui.expansion(
        "Quasi-static phase envelope",
        icon="timeline",
        value=_expansion_defaults(ctx.session, panel_id="env_phase", default_open=True),
    ).classes("w-full"):
        from ui_nicegui.decks.point_designer.phase_envelopes import render_phase_envelopes

        render_phase_envelopes(ctx.session, ui_key_prefix="suite_phase_env", embedded=True)

    with ui.expansion(
        "Profile & transport corner contracts",
        icon="grid_view",
        value=_expansion_defaults(ctx.session, panel_id="env_profile", default_open=False),
    ).classes("w-full q-mt-sm"):
        from ui_nicegui.components.mode_scope import render_mode_scope

        render_mode_scope("profile_contracts", default_open=False)
        ui.label(
            "Finite corner set over certified profile/transport envelopes — optimistic vs robust tiers."
        ).classes("text-caption q-mb-sm")
        _render_profile_corners(ctx)

    with ui.expansion(
        "Input uncertainty intervals",
        icon="tune",
        value=_expansion_defaults(ctx.session, panel_id="env_uq", default_open=False),
    ).classes("w-full q-mt-sm"):
        from ui_nicegui.decks.point_designer.uncertainty_contracts import render_uncertainty_contracts

        render_uncertainty_contracts(ctx.session, ui_key_prefix="suite_uq", embedded=True)


# ---------------------------------------------------------------------------
# Tab 5 · Scenarios & Exports (campaign + parity helpers below)
# ---------------------------------------------------------------------------


def _fidelity_badge(out: dict) -> None:
    try:
        from src.provenance.authority import authority_snapshot_from_outputs
        from src.provenance.fidelity_tiers import global_fidelity_from_registry
    except ImportError:
        try:
            from provenance.authority import authority_snapshot_from_outputs  # type: ignore
            from provenance.fidelity_tiers import global_fidelity_from_registry  # type: ignore
        except Exception:
            return
    try:
        snap = authority_snapshot_from_outputs(out if isinstance(out, dict) else {})
        tier = global_fidelity_from_registry(snap)
        ui.badge(f"Model fidelity: {tier}", color="grey").props("outline q-mb-sm")
    except Exception:
        pass


def render_campaign_pack(ctx: SuiteContext) -> None:
    from ui_nicegui.components.mode_scope import render_mode_scope
    from ui_nicegui.lib.suite_extended_helpers import (
        default_campaign_template,
        evaluate_campaign_batch,
        export_campaign_zip,
        generate_campaign_candidates,
        parse_campaign_spec,
    )

    ui.label(
        "Generate candidate sets and export firewalled packs for external optimizers."
    ).classes("text-caption q-mb-sm")
    render_mode_scope("campaign_pack", default_open=False)
    _fidelity_badge(ctx.point_out)

    if not ctx.session.suite_campaign_spec_json:
        ctx.session.suite_campaign_spec_json = json.dumps(
            default_campaign_template(ctx.point_inp),
            indent=2,
            sort_keys=True,
        )

    spec_area = ui.textarea(
        "Campaign specification (JSON)",
        value=ctx.session.suite_campaign_spec_json,
    ).classes("w-full").props("rows=12")
    ui.markdown(
        "Default generator.n is 16 (QA-safe). Edit generator.n before **Run batch locally** "
        "if you need a larger campaign — each candidate is re-evaluated by the frozen evaluator."
    ).classes("text-caption text-grey q-mb-sm")

    def _sync_spec() -> None:
        ctx.session.suite_campaign_spec_json = str(spec_area.value or "")

    spec_area.on("update:model-value", lambda: _sync_spec())

    async def _generate() -> None:
        if not try_acquire_suite_lock(ctx.session, "System Suite: Generate candidates"):
            return
        _sync_spec()
        log_ui_event(ctx.session, SUITE_RUNLOCK_OWNER, "CampaignGenerateStart", {})
        try:
            spec = await run.io_bound(parse_campaign_spec, ctx.session.suite_campaign_spec_json)
            cands = await run.io_bound(generate_campaign_candidates, spec)
            ctx.session.suite_campaign_candidates = cands
            ui.notify(f"Generated {len(cands)} candidates", type="positive")
            _camp_preview.refresh()
        except Exception as exc:
            ui.notify(f"Generate failed: {exc}", type="negative")
        finally:
            release_suite_lock(ctx.session)

    async def _export() -> None:
        if not try_acquire_suite_lock(ctx.session, "System Suite: Export campaign ZIP"):
            return
        _sync_spec()
        log_ui_event(ctx.session, SUITE_RUNLOCK_OWNER, "CampaignExportStart", {})
        try:
            spec = await run.io_bound(parse_campaign_spec, ctx.session.suite_campaign_spec_json)
            data = await run.io_bound(export_campaign_zip, spec)
            ui.download(data, f"{spec.name}_campaign_bundle.zip")
            ui.notify("Campaign ZIP ready", type="positive")
        except Exception as exc:
            ui.notify(f"Export failed: {exc}", type="negative")
        finally:
            release_suite_lock(ctx.session)

    async def _run_local() -> None:
        if not try_acquire_suite_lock(ctx.session, "System Suite: Campaign batch"):
            return
        _sync_spec()
        log_ui_event(ctx.session, SUITE_RUNLOCK_OWNER, "CampaignBatchStart", {})
        try:
            spec = await run.io_bound(parse_campaign_spec, ctx.session.suite_campaign_spec_json)
            cands = ctx.session.suite_campaign_candidates
            if not isinstance(cands, list):
                cands = await run.io_bound(generate_campaign_candidates, spec)
            summary, rows, jsonl = await run.io_bound(evaluate_campaign_batch, spec, cands)
            ctx.session.suite_campaign_summary = summary
            ctx.session.suite_campaign_results_preview = rows[:200]
            ctx.session.suite_campaign_jsonl_bytes = jsonl
            log_ui_event(
                ctx.session,
                SUITE_RUNLOCK_OWNER,
                "CampaignBatchComplete",
                {"n_feasible": summary.get("n_feasible"), "n_total": summary.get("n_total")},
            )
            ui.notify(
                f"Batch complete: {summary.get('n_feasible', '?')}/{summary.get('n_total', '?')} feasible",
                type="positive",
            )
            _camp_results.refresh()
        except Exception as exc:
            ui.notify(f"Batch eval failed: {exc}", type="negative")
        finally:
            release_suite_lock(ctx.session)

    with ui.row().classes("gap-2 q-mb-sm"):
        ui.button("Generate candidates", icon="play_arrow", on_click=_generate).props("outline")
        ui.button("Export campaign ZIP", icon="archive", on_click=_export).props("outline")
        ui.button("Run batch locally", icon="bolt", on_click=_run_local).props("color=primary outline")

    @ui.refreshable
    def _camp_preview() -> None:
        cands = ctx.session.suite_campaign_candidates
        if not isinstance(cands, list) or not cands:
            return
        ui.label(f"Candidates preview ({min(len(cands), 50)} shown)").classes("text-caption")
        cols = sorted(cands[0].keys())[:8] if isinstance(cands[0], dict) else []
        ui.table(
            columns=[{"name": k, "label": k, "field": k} for k in cols],
            rows=[{"_idx": i, **{k: r.get(k) for k in cols}} for i, r in enumerate(cands[:50]) if isinstance(r, dict)],
            row_key="_idx",
        ).classes("w-full")

    @ui.refreshable
    def _camp_results() -> None:
        summary = ctx.session.suite_campaign_summary
        if not isinstance(summary, dict):
            return
        kpi_row([
            ("N", str(summary.get("n_total", "-"))),
            ("Feasible", str(summary.get("n_feasible", "-"))),
            ("Pass rate", f"{100.0 * float(summary.get('pass_rate', 0.0)):.1f}%"),
        ])
        with ui.expansion("Summary JSON", icon="summarize").classes("w-full"):
            render_json_blob(summary)
        preview = ctx.session.suite_campaign_results_preview
        if isinstance(preview, list) and preview:
            cols = list(preview[0].keys())[:10] if isinstance(preview[0], dict) else []
            with ui.expansion(f"Results preview ({len(preview)} rows)", icon="table_chart").classes("w-full"):
                ui.table(
                    columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
                    rows=[{c: r.get(c) for c in cols} for r in preview if isinstance(r, dict)],
                    row_key=cols[0] if cols else "case",
                ).classes("w-full")
        data = ctx.session.suite_campaign_jsonl_bytes
        if isinstance(data, (bytes, bytearray)):
            ui.button(
                "Download results.jsonl",
                icon="download",
                on_click=lambda: ui.download(bytes(data), "campaign_results.jsonl"),
            ).props("flat outline")

    _camp_preview()
    _camp_results()


def render_benchmark_parity(ctx: SuiteContext) -> None:
    from ui_nicegui.components.mode_scope import render_mode_scope
    from ui_nicegui.lib.suite_extended_helpers import (
        list_parity_cases,
        load_parity_case,
        parity_zip_bytes,
        run_parity_suite,
    )

    ui.label(
        "Run frozen-evaluator benchmark cases; optional PROCESS reference upload."
    ).classes("text-caption q-mb-sm")
    render_mode_scope("parity_harness", default_open=False)

    if not ctx.session.suite_parity_suite:
        ctx.session.suite_parity_suite = "v364"
    suite_in = ui.input(
        "Benchmark suite name",
        value=ctx.session.suite_parity_suite,
        on_change=lambda e: setattr(ctx.session, "suite_parity_suite", str(e.value or "v364")),
    ).classes("w-full")
    ui.label("Internal suite key selects case files under repository benchmarks (e.g. standard parity pack).").classes("text-caption")
    suite_internal = str(ctx.session.suite_parity_suite or "v364")
    preset = ui.select(["C8", "C16", "C32"], label="Profile preset", value=ctx.session.suite_parity_preset or "C8")
    tier = ui.select(["optimistic", "robust", "both"], label="Profile tier", value=ctx.session.suite_parity_tier or "both")

    cases = list_parity_cases(suite_internal)
    if not cases:
        empty_state("No benchmark cases found for this suite.", kind="warn")
        return

    case_ids = [c[0] for c in cases]
    if ctx.session.suite_parity_case not in case_ids:
        ctx.session.suite_parity_case = case_ids[0]
    case_sel = ui.select(case_ids, label="Case", value=ctx.session.suite_parity_case).classes("w-full")

    with ui.expansion("Case JSON", icon="data_object").classes("w-full"):
        path_map = {c[0]: c[1] for c in cases}
        try:
            ui.code(json.dumps(load_parity_case(path_map[str(case_sel.value)]), indent=2), language="json")
        except Exception as exc:
            ui.label(str(exc)).classes("text-negative")

    process_blob: dict = {}

    async def _on_process_upload(e) -> None:
        try:
            process_blob.clear()
            process_blob.update(json.loads(e.content.read().decode("utf-8")))
            ui.notify("PROCESS outputs loaded (session-only)", type="info")
        except Exception as exc:
            ui.notify(f"Upload failed: {exc}", type="negative")

    ui.upload(on_upload=_on_process_upload).props('accept=".json" auto-upload label="Optional PROCESS outputs JSON"')

    async def _run_one() -> None:
        if not try_acquire_suite_lock(ctx.session, "System Suite: Parity case"):
            return
        ctx.session.suite_parity_preset = str(preset.value)
        ctx.session.suite_parity_tier = str(tier.value)
        ctx.session.suite_parity_case = str(case_sel.value)
        path_map = {c[0]: c[1] for c in list_parity_cases(suite_internal)}
        p = path_map.get(ctx.session.suite_parity_case)
        if not p:
            ui.notify("Case not found", type="negative")
            release_suite_lock(ctx.session)
            return
        proc = {ctx.session.suite_parity_case: process_blob} if process_blob else {}
        ui.notify("Running benchmark case…", type="info")
        log_ui_event(ctx.session, SUITE_RUNLOCK_OWNER, "ParityCaseStart", {"case": ctx.session.suite_parity_case})
        try:
            rep = await run.io_bound(
                run_parity_suite,
                suite=suite_internal,
                case_paths=[p],
                preset=ctx.session.suite_parity_preset,
                tier=ctx.session.suite_parity_tier,
                process_outputs_by_case=proc,
            )
            ctx.session.suite_parity_last_report = rep
            log_ui_event(ctx.session, SUITE_RUNLOCK_OWNER, "ParityCaseComplete", {"n_cases": rep.get("n_cases", 1)})
            ui.notify("Case complete", type="positive")
            _parity_results.refresh()
        except Exception as exc:
            ui.notify(f"Parity run failed: {exc}", type="negative")
        finally:
            release_suite_lock(ctx.session)

    async def _run_all() -> None:
        if not try_acquire_suite_lock(ctx.session, "System Suite: Parity suite"):
            return
        ctx.session.suite_parity_preset = str(preset.value)
        ctx.session.suite_parity_tier = str(tier.value)
        paths = [c[1] for c in list_parity_cases(suite_internal)]
        ui.notify("Running full benchmark suite…", type="info")
        log_ui_event(ctx.session, SUITE_RUNLOCK_OWNER, "ParitySuiteStart", {"suite": suite_internal, "n": len(paths)})
        try:
            rep = await run.io_bound(
                run_parity_suite,
                suite=suite_internal,
                case_paths=paths,
                preset=str(preset.value),
                tier=str(tier.value),
            )
            ctx.session.suite_parity_last_report = rep
            log_ui_event(ctx.session, SUITE_RUNLOCK_OWNER, "ParitySuiteComplete", {"n_cases": rep.get("n_cases", len(paths))})
            ui.notify(f"Completed {rep.get('n_cases', len(paths))} case(s)", type="positive")
            _parity_results.refresh()
        except Exception as exc:
            ui.notify(f"Suite run failed: {exc}", type="negative")
        finally:
            release_suite_lock(ctx.session)

    with ui.row().classes("gap-2"):
        ui.button("Run selected case", icon="play_arrow", on_click=_run_one).props("color=primary")
        ui.button("Run full suite", icon="playlist_play", on_click=_run_all).props("outline")

    @ui.refreshable
    def _parity_results() -> None:
        rep = ctx.session.suite_parity_last_report
        if not isinstance(rep, dict):
            return
        rows = rep.get("summary_rows") or []
        n_fail = sum(1 for r in rows if isinstance(r, dict) and str(r.get("status", "")).upper() in ("FAIL", "WARN"))
        render_tab_summary_strip(
            "PARITY PASS" if rows and n_fail == 0 else "PARITY REVIEW",
            detail=f"{len(rows)} case(s) · {n_fail} need review",
        )
        if rows:
            cols = list(rows[0].keys()) if isinstance(rows[0], dict) else []
            ui.table(
                columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
                rows=rows,
                row_key=cols[0] if cols else "case",
            ).classes("w-full")
        with ui.expansion("Artifacts JSON", icon="description").classes("w-full"):
            render_json_blob(rep.get("cases") or {})
        ui.button(
            "Download reviewer pack ZIP",
            icon="download",
            on_click=lambda: ui.download(
                parity_zip_bytes(rep),
                "SHAMS_benchmark_parity_pack.zip",
            ),
        ).props("outline q-mt-sm")

    _parity_results()


def render_tab_scenarios_exports(ctx: SuiteContext) -> None:
    summary = ctx.session.suite_campaign_summary if isinstance(ctx.session.suite_campaign_summary, dict) else {}
    render_tab_summary_strip(
        "SCENARIOS & EXPORTS",
        detail="Campaign packs, scenario presets, and benchmark parity for external optimizers.",
        kpis=[
            ("Campaign feasible", f"{summary.get('n_feasible', '-')}/{summary.get('n_total', '-')}"),
            ("Pass rate", f"{100.0 * float(summary.get('pass_rate', 0.0)):.1f}%" if summary else "-"),
        ] if summary else None,
    )
    render_export_bar(ctx.session)
    with ui.expansion("Cross-deck handoffs", icon="share", value=True).classes("w-full q-mb-sm"):
        render_suite_handoffs(ctx.session, ctx.point_out)

    with ui.expansion(
        "Scenario library",
        icon="library_books",
        value=_expansion_defaults(ctx.session, panel_id="scen_library", default_open=True),
    ).classes("w-full"):
        ui.label(
            "Versioned authority presets for robustness screening — stamped, never silent."
        ).classes("text-caption q-mb-sm")
        try:
            from tools.scenario_library import get_preset, preset_names

            presets = preset_names()
            sel = ui.select(["(select)"] + presets, label="Scenario preset", value="(select)")

            @ui.refreshable
            def _preset_view() -> None:
                if sel.value and sel.value != "(select)":
                    ui.code(
                        json.dumps(get_preset(str(sel.value)), indent=2, sort_keys=True),
                        language="json",
                    )

            sel.on("update:model-value", lambda: _preset_view.refresh())
            _preset_view()

            def _copy_to_campaign() -> None:
                if not sel.value or sel.value == "(select)":
                    ui.notify("Select a scenario preset first.", type="warning")
                    return
                preset_d = get_preset(str(sel.value))
                ctx.session.suite_campaign_spec_json = json.dumps(
                    {"name": str(sel.value), "scenario_preset": preset_d},
                    indent=2,
                    sort_keys=True,
                )
                ui.notify("Preset copied to campaign spec — open Campaign bundle.", type="positive")

            ui.button("Copy preset → campaign spec", icon="content_copy", on_click=_copy_to_campaign).props(
                "flat outline q-mt-sm"
            )
        except Exception as exc:
            ui.label(f"Scenario library unavailable: {exc}").classes("text-warning")
        with ui.expansion("Authority ladder (policy)", icon="policy").classes("w-full q-mt-sm"):
            ui.markdown(
                "- **Proxy** → conservative screening models\n"
                "- **Parametric** → regression closures\n"
                "- **External (hashed)** → imported authoritative results\n\n"
                "Authority changes never modify L0 feasibility silently."
            )

    with ui.expansion(
        "Campaign bundle",
        icon="campaign",
        value=_expansion_defaults(ctx.session, panel_id="scen_campaign", default_open=False),
    ).classes("w-full q-mt-sm"):
        ui.label("SHAMS evaluates candidates; optimizers propose inputs only.").classes("text-caption q-mb-sm")
        render_campaign_pack(ctx)

    with ui.expansion(
        "Benchmark parity",
        icon="fact_check",
        value=_expansion_defaults(ctx.session, panel_id="scen_parity", default_open=False),
    ).classes("w-full q-mt-sm"):
        render_benchmark_parity(ctx)
