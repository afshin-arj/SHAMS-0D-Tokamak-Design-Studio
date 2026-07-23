"""Post-solve diagnostics — KPIs, constraints, plots, plant authority, cockpit."""

from __future__ import annotations

import base64
import os
import tempfile

from nicegui import run, ui

from ui_nicegui.decks.systems_mode.post_solve_authority_ui import render_post_solve_authority
from ui_nicegui.lib.systems_artifact import extract_constraints, fetch_systems_artifact, fmt
from ui_nicegui.lib.systems_cockpit import build_compact_cockpit_markdown
from ui_nicegui.session import DesignSession


def render_post_solve_diagnostics(session: DesignSession, *, on_refresh=None) -> None:
    art = fetch_systems_artifact(session)
    if not isinstance(art, dict):
        ui.label("Run target solve to populate post-solve diagnostics.").classes("text-grey")
        return
    out = art.get("outputs") if isinstance(art.get("outputs"), dict) else {}
    ins = art.get("inputs") if isinstance(art.get("inputs"), dict) else session.inputs
    if not out:
        ui.label("No outputs in artifact.").classes("text-grey")
        return
    _render_core(session, art, out, ins, on_refresh=on_refresh)


def render_post_solve_diagnostics_sync(session: DesignSession, *, on_refresh=None) -> None:
    art = fetch_systems_artifact(session)
    if not isinstance(art, dict):
        ui.label("Run target solve to populate post-solve diagnostics.").classes("text-grey")
        return
    out = art.get("outputs") if isinstance(art.get("outputs"), dict) else {}
    ins = art.get("inputs") if isinstance(art.get("inputs"), dict) else session.inputs
    if not out:
        return
    _render_core(session, art, out, ins, on_refresh=on_refresh)


def _render_core(session, art, out, ins, *, on_refresh=None) -> None:
    src = str(art.get("source") or "")
    from ui_nicegui.lib.systems_artifact import is_systems_result_source

    if not is_systems_result_source(src):
        ui.badge("NOT A SYSTEMS SOLVE", color="orange").props("outline").classes("q-mb-xs")
        ui.label(
            "Showing Point Designer baseline / Apply re-eval KPIs — run target solve for post-solve diagnostics."
        ).classes("text-caption text-orange q-mb-sm")

    md = build_compact_cockpit_markdown(session, art)
    with ui.expansion("Copy-ready cockpit summary", icon="summarize").classes("w-full q-mb-sm"):
        ui.markdown(f"```markdown\n{md}\n```")
        ui.button(
            "Download cockpit summary (.md)",
            on_click=lambda: ui.download(md.encode("utf-8"), "systems_cockpit_summary.md"),
        ).props("flat dense")

    title = "Key results (last solve)" if is_systems_result_source(src) else "Key results (Point Designer baseline)"
    ui.label(title).classes("text-subtitle2 q-mt-sm")
    from ui_nicegui.lib.plant_kpi_honesty_ui import pe_net_display
    from ui_nicegui.lib.verdict_core import verdict_summary

    feas = bool(verdict_summary(out).get("feasible")) if isinstance(out, dict) and out else False
    if not feas:
        if is_systems_result_source(src):
            ui.label(
                "PHYS-KPI-001: Q / H98 / performance KPIs below are diagnostic residue on an INFEASIBLE solve — not design claims."
            ).classes("text-caption text-orange q-mb-xs")
        else:
            ui.label(
                "PHYS-KPI-001: Q / H98 / performance KPIs below are diagnostic residue on an INFEASIBLE "
                "Point Designer baseline — not a Systems Mode solve claim."
            ).classes("text-caption text-orange q-mb-xs")

    with ui.row().classes("gap-2 flex-wrap"):
        for label, key in (
            ("Q", "Q_DT_eqv"),
            ("H98", "H98"),
            ("Pe_net [MW]", "P_e_net_MW"),
            ("q_div", "q_div_MW_m2"),
            ("β_N", "beta_N"),
            ("q95 (cyl. proxy)", "q95_proxy"),
        ):
            with ui.card().classes("p-2"):
                ui.label(label).classes("text-caption text-grey")
                if key == "P_e_net_MW":
                    ui.label(pe_net_display(out, artifact=art)).classes("text-body1")
                elif not feas and key in ("Q_DT_eqv", "H98"):
                    ui.label("— (diagnostic)").classes("text-body1 text-orange")
                else:
                    val = out.get(key)
                    if key == "q95_proxy" and val is None:
                        val = out.get("q95")
                    if key == "beta_N" and val is None:
                        val = out.get("betaN_proxy", out.get("betaN"))
                    ui.label(fmt(val)).classes("text-body1")

    _render_constraints_dashboard(out)
    render_post_solve_authority(session, out, ins if isinstance(ins, dict) else {}, on_refresh=on_refresh)

    ui.separator().classes("q-my-sm")
    ui.label("Engineering visuals").classes("text-subtitle2")
    sankey_slot = ui.column().classes("w-full")
    plot_slot = ui.column().classes("w-full")

    async def _sankey() -> None:
        def _build():
            try:
                from shams_io.sankey import build_power_balance_sankey
            except ImportError:
                from src.shams_io.sankey import build_power_balance_sankey  # type: ignore
            import plotly.graph_objects as go

            kwargs = build_power_balance_sankey(art)
            fig = go.Figure(data=[go.Sankey(**kwargs)])
            fig.update_layout(
                title="Plant power balance",
                margin=dict(l=20, r=20, t=40, b=20),
                height=420,
                font=dict(size=11),
            )
            return fig

        try:
            fig = await run.io_bound(_build)
            sankey_slot.clear()
            with sankey_slot:
                ui.plotly(fig).classes("w-full")
        except Exception as exc:
            ui.notify(f"Power balance diagram unavailable: {exc}", type="warning")

    ui.button("Show power balance diagram", icon="account_tree", on_click=_sankey).props("outline dense")

    if session.systems_expert_view:
        async def _radial() -> None:
            def _run():
                try:
                    from shams_io.plotting import plot_radial_build_from_artifact
                except ImportError:
                    from src.shams_io.plotting import plot_radial_build_from_artifact  # type: ignore
                tmp = os.path.join(tempfile.gettempdir(), "shams_systems_radial.png")
                plot_radial_build_from_artifact(art, tmp)
                with open(tmp, "rb") as f:
                    return f.read()

            try:
                data = await run.io_bound(_run)
                plot_slot.clear()
                with plot_slot:
                    ui.image(data).classes("max-w-lg")
            except Exception as exc:
                ui.notify(f"Radial build plot unavailable: {exc}", type="warning")

        ui.button("Render radial build", on_click=_radial).props("flat dense q-ml-sm")
        _render_corner_table_sync(session, art, out)


def _render_constraints_dashboard(out: dict) -> None:
    try:
        try:
            from constraints.constraints import evaluate_constraints
        except ImportError:
            from src.constraints.constraints import evaluate_constraints  # type: ignore
        cons = evaluate_constraints(out)
    except Exception:
        cons = []

    rows = []
    for c in cons:
        try:
            margin = float(getattr(c, "margin", float("nan")))
        except (TypeError, ValueError):
            margin = float("nan")
        rows.append({
            "constraint": str(getattr(c, "name", "")),
            "passed": bool(getattr(c, "passed", False)),
            "margin": fmt(margin) if margin == margin else "-",
            "severity": str(getattr(c, "severity", "hard")),
        })

    if rows:
        ui.label("All constraints & margins").classes("text-subtitle2 q-mt-md")
        ui.table(
            columns=[
                {"name": "constraint", "label": "Constraint", "field": "constraint", "align": "left"},
                {"name": "passed", "label": "Pass", "field": "passed"},
                {"name": "margin", "label": "Margin", "field": "margin"},
                {"name": "severity", "label": "Severity", "field": "severity"},
            ],
            rows=rows[:60],
            row_key="constraint",
        ).classes("w-full")


def _render_corner_table_sync(session: DesignSession, art: dict, out: dict) -> None:
    ui.label("Target feasibility at (I_p, f_G) corners").classes("text-subtitle2 q-mt-md")
    from ui_nicegui.lib.systems_state_helpers import resolve_systems_problem

    base, targets, variables = resolve_systems_problem(session)
    if "Ip_MA" not in variables or "fG" not in variables:
        ui.label("Enable I_p and f_G iteration variables to view corner table.").classes("text-caption")
        return

    async def _run():
        from ui_nicegui.lib.navigation import refresh_helm, refresh_status
        from ui_nicegui.lib.run_lock import (
            acquire as runlock_acquire,
            release as runlock_release,
            status as runlock_status,
            current_lease,
            lease_valid,
        )

        locked, task, is_owner = runlock_status("SystemsMode")
        if locked:
            ui.notify(
                f"Busy: {task} — wait or force-clear from Helm."
                if not is_owner
                else "Systems Mode already holds the run lock.",
                type="warning",
            )
            return
        if not runlock_acquire("Systems Mode: Corner diagnostics", "SystemsMode"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        lease = current_lease()
        refresh_status()
        refresh_helm()

        def _corners():
            try:
                from src.solvers.constraint_solver import evaluate_targets_at_corners
            except ImportError:
                from solvers.constraint_solver import evaluate_targets_at_corners  # type: ignore
            t = {}
            if "H98" in targets:
                t["H98"] = float(targets["H98"])
            if "Q_DT_eqv" in targets:
                t["Q_DT_eqv"] = float(targets["Q_DT_eqv"])
            lo0, hi0 = float(variables["Ip_MA"][1]), float(variables["Ip_MA"][2])
            lo1, hi1 = float(variables["fG"][1]), float(variables["fG"][2])
            return evaluate_targets_at_corners(base, t, ("Ip_MA", lo0, hi0), ("fG", lo1, hi1))

        try:
            rows = await run.io_bound(_corners)
            if not lease_valid(lease):
                ui.notify("Run was force-cleared — discarding results.", type="warning")
                return
            if isinstance(rows, list) and rows:
                display_rows = []
                for r in rows:
                    if not isinstance(r, dict):
                        continue
                    nr: dict = {}
                    for k, v in r.items():
                        if str(k).startswith("ach_"):
                            nr[f"eval_{str(k)[4:]}"] = v
                        else:
                            nr[k] = v
                    try:
                        rn = float(r.get("res_norm", float("nan")))
                        nr["floors"] = "met" if rn == rn and rn < 1e-2 else "miss"
                    except (TypeError, ValueError):
                        nr["floors"] = "n/a"
                    display_rows.append(nr)
                cols = list(display_rows[0].keys()) if display_rows else []
                ui.label(
                    "Corner values are evaluated diagnostic snapshots (eval_* columns) — "
                    "``floors=met`` is residual-only, not intent feasibility (PHYS-KPI-001)."
                ).classes("text-caption text-orange q-mb-xs")
                ui.table(
                    columns=[{"name": c, "label": c, "field": c} for c in cols],
                    rows=display_rows,
                    row_key=cols[0] if cols else "corner",
                ).classes("w-full")
        except Exception as exc:
            ui.label(f"Corner table unavailable: {exc}").classes("text-caption")
        finally:
            if lease_valid(lease):
                runlock_release("SystemsMode", lease)
                refresh_status()
                refresh_helm()

    ui.button("Compute corner table", on_click=_run).props("flat dense")
