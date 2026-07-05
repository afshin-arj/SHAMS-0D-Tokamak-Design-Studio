"""Verdict hero strip for Point Designer (NiceGUI)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.components.verdict_banner import verdict_banner
from ui_nicegui.lib.verdict_core import verdict_summary
from ui_nicegui.session import DesignSession


def _fmt_num(x, *, digits: int = 3) -> str:
    try:
        v = float(x)
        if v != v:
            return "n/a"
        return f"{v:.{digits}g}"
    except (TypeError, ValueError):
        return "n/a"


def render_hero(session: DesignSession) -> None:
    out = session.pd_last_outputs or session.last_eval
    if not out:
        empty_state("No evaluation loaded. Click **Evaluate Point** in Configure.", kind="info")
        return
    summary = verdict_summary(out)
    art = session.pd_last_artifact if isinstance(session.pd_last_artifact, dict) else {}
    rs = art.get("run_summary") if isinstance(art.get("run_summary"), dict) else {}
    headline = rs.get("headline") if isinstance(rs.get("headline"), dict) else {}

    detail = f"Dominant: {summary['dominant']}"
    tight = rs.get("tightest_hard_constraints") or []
    if tight and isinstance(tight[0], dict):
        t0 = tight[0]
        if t0.get("name"):
            margin = _fmt_num(t0.get("margin_frac"), digits=2)
            detail += f" · Tightest hard: {t0['name']} (margin {margin})"

    verdict_banner(summary["verdict"], detail=detail)

    h98 = headline.get("H98", out.get("H98"))
    pnet = headline.get("P_net_e_MW", out.get("P_net_e_MW"))
    closure = rs.get("power_closure_MW")
    kpi_row([
        ("Performance", summary["q_label"]),
        ("H98(y,2)", _fmt_num(h98)),
        ("P_net,e", f"{_fmt_num(pnet)} MW" if pnet is not None else "n/a"),
        ("Triple product proxy", summary["nt_label"]),
    ])
    if closure == closure:
        ui.label(f"Power closure Pin−Ploss ≈ {_fmt_num(closure)} MW (diagnostic)").classes(
            "text-caption text-grey"
        )

    subs = summary.get("subsystems") or {}
    with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
        for name in ("magnets", "exhaust", "neutronics", "control", "transport", "plant"):
            status = subs.get(name, "pass")
            color = {"pass": "green", "fail": "red", "warn": "orange"}.get(status, "grey")
            ui.badge(name.replace("_", " ").title(), color=color).props("outline")
