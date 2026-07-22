"""Control Room — 2-knob trade-space grid explorer."""
from __future__ import annotations

from dataclasses import replace

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.control_room_helpers import report_to_json_bytes
from ui_nicegui.lib.cr_artifacts_helpers import collect_session_artifacts
from ui_nicegui.lib.cr_chronicle_helpers import evaluate_knob_trade_grid, point_inputs_from_artifact
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table
from ui_nicegui.session import DesignSession


_KNOBS = ["Ip_MA", "fG", "Bt_T", "R0_m", "Paux_MW", "Ti_keV", "a_m", "kappa"]
_CLAIM_COLS = ("Q", "H98", "Pfus_total_MW", "P_e_net_MW")


def render_knob_trade_space(session: DesignSession) -> None:
    ui.label("Knob Trade-Space Explorer").classes("text-subtitle1")
    ui.label(
        "Explore a 2-knob trade-space by evaluating a small grid around the active point "
        "(no optimization; feasibility-first)."
    ).classes("text-caption q-mb-sm")

    base = None
    if isinstance(session.cr_selected_artifact, dict):
        try:
            base = point_inputs_from_artifact(session.cr_selected_artifact)
        except Exception:
            base = None
    if base is None:
        arts = collect_session_artifacts(session)
        for a in reversed(arts):
            try:
                base = point_inputs_from_artifact(a["artifact"])
                break
            except Exception:
                continue
    if base is None:
        try:
            base = session.build_point_inputs()
        except Exception:
            base = None

    if base is None:
        empty_state("Load an artifact or run **Point Designer** to initialize a base point.", kind="info")
        ui.button("Open Point Designer", icon="open_in_new", on_click=lambda: switch_deck("Point Designer")).props(
            "flat outline q-mt-sm"
        )
        return

    with ui.row().classes("w-full gap-md flex-wrap"):
        r0 = ui.number("R0 (m)", value=float(base.R0_m), step=0.01)
        a_m = ui.number("a (m)", value=float(base.a_m), step=0.01)
        kappa = ui.number("kappa", value=float(base.kappa), step=0.05)
        bt = ui.number("Bt (T)", value=float(base.Bt_T), step=0.1)
        ip = ui.number("Ip (MA)", value=float(base.Ip_MA), step=0.1)
        fg = ui.number("fG", value=float(base.fG), step=0.01)
        ti = ui.number("Ti (keV)", value=float(base.Ti_keV), step=0.5)
        paux = ui.number("Paux (MW)", value=float(base.Paux_MW), step=1.0)
        tite = ui.number("Ti/Te", value=float(getattr(base, "Ti_over_Te", 2.0)), step=0.1)
    fuel = ui.select(["DT", "DD"], label="fuel_mode", value=str(getattr(base, "fuel_mode", "DT") or "DT"))

    kx = ui.select(_KNOBS, label="Knob X", value="Ip_MA").classes("w-full")
    ky = ui.select(_KNOBS, label="Knob Y", value="fG").classes("w-full")
    x_span = ui.number("X span (+/-)", value=max(0.1, 0.1 * abs(float(base.Ip_MA))), step=0.01)
    y_span = ui.number("Y span (+/-)", value=max(0.01, 0.1 * abs(float(base.fG))), step=0.01)
    nx = ui.number("X grid points", value=7, min=3, max=15, step=1)
    ny = ui.number("Y grid points", value=7, min=3, max=15, step=1)

    async def _run() -> None:
        from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

        locked, task, is_owner = runlock_status("ControlRoom")
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Control Room: Knob trade grid", "ControlRoom"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        try:
            patch = {
                "R0_m": float(r0.value),
                "a_m": float(a_m.value),
                "kappa": float(kappa.value),
                "Bt_T": float(bt.value),
                "Ip_MA": float(ip.value),
                "fG": float(fg.value),
                "Ti_keV": float(ti.value),
                "Paux_MW": float(paux.value),
                "Ti_over_Te": float(tite.value),
                "fuel_mode": str(fuel.value or "DT"),
            }
            pi = session.build_point_inputs()
            pi = replace(
                pi,
                **{k: v for k, v in patch.items() if hasattr(pi, k)},
            )
            rows = await run.io_bound(
                evaluate_knob_trade_grid,
                pi,
                kx=str(kx.value),
                ky=str(ky.value),
                x_span=float(x_span.value or 0.1),
                y_span=float(y_span.value or 0.1),
                nx=int(nx.value or 7),
                ny=int(ny.value or 7),
                patch=patch,
            )
            session.cr_knob_grid_last = {"rows": rows, "kx": str(kx.value), "ky": str(ky.value)}
            ui.notify(f"Grid evaluated ({len(rows)} points)", type="positive")
            _grid_view.refresh()
        except Exception as exc:
            ui.notify(f"Grid failed: {exc}", type="negative")
        finally:
            runlock_release("ControlRoom")

    ui.button("Evaluate grid", icon="grid_on", on_click=_run).props("color=primary outline")
    _grid_view(session)


def watermark_knob_grid_rows(rows: list, *, kx: str, ky: str) -> list[dict]:
    """PHYS-KPI-001: suppress claim KPIs on infeasible grid cells (shared for UI + tests)."""
    cols = [kx, ky, "feasible", "top_blocker", *_CLAIM_COLS]
    display_rows: list[dict] = []
    for r in rows:
        feas = bool(r.get("feasible"))
        row = {c: r.get(c) for c in cols}
        for col in _CLAIM_COLS:
            key = "Q_DT_eqv" if col == "Q" else col
            row[col] = format_claim_kpi_for_table(key, r.get(col), feasible=feas)
        display_rows.append(row)
    return display_rows


@ui.refreshable
def _grid_view(session: DesignSession) -> None:
    payload = session.cr_knob_grid_last if isinstance(session.cr_knob_grid_last, dict) else None
    if not payload:
        return
    rows = payload.get("rows") or []
    kx = str(payload.get("kx", "x"))
    ky = str(payload.get("ky", "y"))
    if not rows:
        return
    n_feas = sum(1 for r in rows if r.get("feasible"))
    kpi_row([("Points", str(len(rows))), ("Feasible", str(n_feas)), ("X", kx), ("Y", ky)])
    if n_feas < len(rows):
        ui.label(
            "PHYS-KPI-001: Q / H98 / Pfus / P_net on infeasible grid rows are "
            "— (diagnostic) — not design claims."
        ).classes("text-caption text-orange q-mb-xs")
    cols = [kx, ky, "feasible", "top_blocker", *_CLAIM_COLS]
    display_rows = watermark_knob_grid_rows(rows, kx=kx, ky=ky)
    ui.table(
        columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
        rows=display_rows,
        row_key=kx,
    ).classes("w-full q-mb-sm")
    ui.button(
        "Download grid JSON",
        icon="download",
        on_click=lambda: ui.download(report_to_json_bytes(payload), "knob_trade_grid.json"),
    ).props("flat outline")
