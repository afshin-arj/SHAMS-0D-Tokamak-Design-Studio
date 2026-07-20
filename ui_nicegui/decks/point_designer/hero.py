"""Verdict hero strip for Point Designer (NiceGUI)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.components.verdict_banner import verdict_banner
from ui_nicegui.lib.pd_hero_kpis import hero_diagnostic_notes, hero_kpi_cells
from ui_nicegui.lib.session_store import get_cached_no_solution_atlas, get_cached_verdict_summary
from ui_nicegui.session import DesignSession


def _fmt_num(x, *, digits: int = 3) -> str:
    try:
        v = float(x)
        if v != v:
            return "n/a"
        return f"{v:.{digits}g}"
    except (TypeError, ValueError):
        return "n/a"


def _constraint_headroom(out: dict, names: list[str]) -> str:
    """Format margin_frac from constraint ledger when present (presentation only)."""
    cons = out.get("constraints") or []
    if not isinstance(cons, list):
        return ""
    want = {n.lower() for n in names}
    for c in cons:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name") or "").lower()
        if name not in want:
            continue
        m = c.get("margin_frac", c.get("margin"))
        limit = c.get("limit", c.get("threshold"))
        try:
            if m is not None and float(m) == float(m):
                lim = f", lim {_fmt_num(limit)}" if limit is not None else ""
                return f" (m={_fmt_num(m, digits=2)}{lim})"
        except (TypeError, ValueError):
            pass
    return ""


def render_hero(session: DesignSession) -> None:
    out = session.pd_last_outputs or session.last_eval
    if not out:
        empty_state("No evaluation loaded. Click **Evaluate Point** in Configure.", kind="info")
        return
    from ui_nicegui.lib.pd_solver_helpers import inputs_stale

    stale = bool(session.pd_last_run_ts and inputs_stale(session))
    if stale:
        ui.label(
            "STALE — inputs changed since this evaluation. Re-run Evaluate Point before trusting KPIs."
        ).classes("text-negative text-weight-medium q-mb-sm")
    summary = get_cached_verdict_summary(session, out)
    art = session.pd_last_artifact if isinstance(session.pd_last_artifact, dict) else {}
    rs = art.get("run_summary") if isinstance(art.get("run_summary"), dict) else {}
    headline = rs.get("headline") if isinstance(rs.get("headline"), dict) else {}

    detail = f"Dominant: {summary['dominant']}"
    if stale:
        detail = "STALE · " + detail
    tight = rs.get("tightest_hard_constraints") or []
    if tight and isinstance(tight[0], dict):
        t0 = tight[0]
        if t0.get("name"):
            margin = _fmt_num(t0.get("margin_frac"), digits=2)
            detail += f" · Tightest hard: {t0['name']} (margin {margin})"

    verdict_banner(summary["verdict"], detail=detail)

    if bool(out.get("mirage_flag_v402")):
        ui.badge("MIRAGE / credibility-fragile", color="orange").props("outline").classes("q-mb-xs")

    if not summary.get("feasible"):
        atlas = get_cached_no_solution_atlas(session, out)
        ui.label(
            f"NO-SOLUTION · Mechanism: {atlas.get('dominant_mechanism', '-')} · "
            f"Constraint: {atlas.get('dominant_constraint', '-')}"
        ).classes("text-caption text-orange q-mb-xs")

    fuel_mode = str(session.inputs.get("fuel_mode", "DT"))
    cells = hero_kpi_cells(
        out,
        summary,
        design_intent=str(session.design_intent),
        fuel_mode=fuel_mode,
        headline=headline,
    )
    kpi_row([(c.label, c.display) for c in cells])

    beta = out.get("betaN", out.get("beta_N"))
    fg = out.get("fG", out.get("greenwald_fraction"))
    # L0 writes q95_proxy (cylindrical screening), not a plain "q95" key.
    q95 = out.get("q95", out.get("q95_proxy"))
    kpi_row([
        ("β_N", _fmt_num(beta) + _constraint_headroom(out, ["betaN", "beta_n", "betaN_proxy"])),
        ("f_G", _fmt_num(fg) + _constraint_headroom(out, ["fG", "fg", "greenwald"])),
        ("q95 (cyl. proxy)", _fmt_num(q95) + _constraint_headroom(out, ["q95", "q95_min"])),
    ])
    ui.label(
        "Q uses Pfus / P_aux (auxiliary heating only). q95 is a cylindrical proxy, not an equilibrium solve."
    ).classes("text-caption text-grey q-mb-xs")

    for note in hero_diagnostic_notes(
        out,
        summary,
        design_intent=str(session.design_intent),
        fuel_mode=fuel_mode,
        headline=headline,
    ):
        # Notes may carry **bold** emphasis (e.g. suppressed-KPI banner) — render markdown.
        ui.markdown(note).classes("text-caption text-orange q-mt-xs")

    suppressed = [c for c in cells if c.suppressed and c.raw_value is not None]
    if suppressed:
        with ui.expansion("Raw headline diagnostics (infeasible closure)", icon="science").classes(
            "w-full q-mt-xs"
        ):
            for c in suppressed:
                ui.label(f"{c.label}: {_fmt_num(c.raw_value)}").classes("text-caption text-grey")

    closure = rs.get("power_closure_MW")
    if closure == closure:
        ui.label(f"Power closure Pin−Ploss ≈ {_fmt_num(closure)} MW (diagnostic)").classes(
            "text-caption text-grey"
        )

    mode = str(getattr(session, "pd_eval_mode", "direct"))
    if mode in ("solver", "envelope") and isinstance(out, dict):
        h98_t = session.pd_h98_target
        q_t = session.pd_q_target
        h98_a = out.get("H98")
        q_a = out.get("Q_DT_eqv", out.get("Q"))
        clamped = bool(out.get("_solver_clamped")) or bool(out.get("_solver_clamped_Q"))
        if clamped:
            ui.label(
                "Solver clamped to bounds — targets may not be fully met. See Configure target table."
            ).classes("text-caption text-orange q-mt-xs")
        elif h98_a is not None and q_a is not None and summary.get("feasible"):
            ui.label(
                f"Solver targets: H98={_fmt_num(h98_t)} → {_fmt_num(h98_a)}, "
                f"Q={_fmt_num(q_t)} → {_fmt_num(q_a)}"
            ).classes("text-caption text-grey q-mt-xs")

    subs = summary.get("subsystems") or {}
    with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
        for name in ("magnets", "exhaust", "neutronics", "control", "transport", "plant"):
            status = subs.get(name, "pass")
            color = {"pass": "green", "fail": "red", "warn": "orange"}.get(status, "grey")
            ui.badge(name.replace("_", " ").title(), color=color).props("outline")
