"""Uncertainty Contracts sub-deck — NiceGUI Phase 11."""
from __future__ import annotations

from pathlib import Path

from nicegui import run, ui

from ui_nicegui.bootstrap import repo_root
from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.lib.pd_outer_loop_helpers import (
    VAR_GROUPS,
    build_uq_spec,
    filter_fields_by_group,
    make_point_inputs,
    numeric_point_fields,
)
from ui_nicegui.session import DesignSession

try:
    from src.uq_contracts import run_uncertainty_contract_for_point
    from tools.uncertainty_contracts import export_uncertainty_contract_zip
except ImportError:
    from uq_contracts import run_uncertainty_contract_for_point  # type: ignore
    from tools.uncertainty_contracts import export_uncertainty_contract_zip  # type: ignore


def render_uncertainty_contracts(session: DesignSession, *, ui_key_prefix: str = "pd_uq", embedded: bool = False) -> None:
    if not embedded:
        ui.label("Uncertainty Contracts").classes("text-h6")
        ui.label(
            "Declare interval uncertainty on selected inputs. SHAMS enumerates all corners "
            "deterministically (2^N). Verdict: ROBUST_PASS / FRAGILE / FAIL. No probability."
        ).classes("text-caption q-mb-sm")
    else:
        ui.label(
            "Deterministic corner enumeration on selected inputs — no Monte Carlo."
        ).classes("text-caption q-mb-sm")

    art, point_inp, _ = get_point_artifact_triple(session)
    if not isinstance(point_inp, dict):
        empty_state("Run **Point Designer → Truth Console → Evaluate Point** first.", kind="info")
        return

    base_inputs = make_point_inputs(point_inp)
    numeric_fields, _ = numeric_point_fields(point_inp)

    ui.label("Contract builder").classes("text-subtitle2")
    with ui.row().classes("w-full gap-4 flex-wrap"):
        ui.input(
            "Contract name",
            value=session.uq_contract_name,
            on_change=lambda e: setattr(session, "uq_contract_name", str(e.value)),
        ).classes("min-w-[200px]")
        ui.select(
            VAR_GROUPS,
            label="Variable group",
            value=session.uq_contract_group,
            on_change=lambda e: setattr(session, "uq_contract_group", str(e.value)),
        ).classes("min-w-[160px]")
        ui.select(
            ["±% around baseline", "absolute [lo,hi]"],
            label="Interval mode",
            value=session.uq_contract_mode,
            on_change=lambda e: setattr(session, "uq_contract_mode", str(e.value)),
        ).classes("min-w-[180px]")

    opts = filter_fields_by_group(numeric_fields, session.uq_contract_group)
    ui.select(
        opts,
        label="Uncertain variables",
        value=session.uq_contract_dims,
        multiple=True,
        on_change=lambda e: setattr(session, "uq_contract_dims", list(e.value or [])),
    ).classes("w-full")

    with ui.row().classes("w-full gap-4 items-center"):
        ui.slider(min=0, max=30, step=0.5, value=session.uq_contract_pct).bind_value(session, "uq_contract_pct")
        ui.label().bind_text_from(session, "uq_contract_pct", lambda v: f"± {v:.1f} %")
        ui.number(
            "Max dims",
            value=session.uq_contract_max_dims,
            min=1,
            max=20,
            on_change=lambda e: setattr(session, "uq_contract_max_dims", int(e.value or 12)),
        ).classes("w-24")
        n = len(session.uq_contract_dims or [])
        ui.label(f"Corners: {2 ** n:,}" if n else "Corners: 0").classes("text-caption")
        if n >= 16:
            ui.label("High N — corner count may be unwieldy.").classes("text-orange text-caption")

    async def _run() -> None:
        session.uq_contract_running = True
        ui.notify("Running uncertainty contract…", type="info")
        try:
            spec = build_uq_spec(
                name=session.uq_contract_name,
                base_inp=point_inp,
                dims=list(session.uq_contract_dims or []),
                mode=session.uq_contract_mode,
                pct=float(session.uq_contract_pct),
            )
            con = await run.io_bound(
                run_uncertainty_contract_for_point,
                base_inputs,
                spec,
                label_prefix="uq",
                max_dims=int(session.uq_contract_max_dims),
            )
            session.uq_contract_last = con
            ui.notify("Uncertainty contract complete.", type="positive")
            _results.refresh()
        except Exception as exc:
            ui.notify(f"Uncertainty contract failed: {exc}", type="negative")
        finally:
            session.uq_contract_running = False

    ui.button("Run Uncertainty Contract", icon="play_arrow", on_click=_run).props("color=primary q-mt-sm")

    _results(session)


@ui.refreshable
def _results(session: DesignSession) -> None:
    con = session.uq_contract_last
    if not isinstance(con, dict):
        return

    summ = con.get("summary") if isinstance(con.get("summary"), dict) else {}
    ui.label("Contract verdict").classes("text-subtitle2 q-mt-md")
    kpi_row([
        ("Verdict", str(summ.get("verdict", "UNKNOWN"))),
        ("Dims", str(summ.get("n_dims", ""))),
        ("Corners", str(summ.get("n_corners", ""))),
        ("Feasible", str(summ.get("n_feasible", ""))),
    ])
    with ui.expansion("Contract summary (JSON)").classes("w-full"):
        ui.json(summ)

    async def _export_zip() -> None:
        try:
            out_dir = Path(repo_root()) / "ui_runs" / "uncertainty_contracts"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_zip = out_dir / "uncertainty_contracts.zip"
            await run.io_bound(export_uncertainty_contract_zip, con, out_zip)
            ui.download(out_zip.read_bytes(), out_zip.name)
            ui.notify("Uncertainty contract ZIP ready.", type="positive")
        except Exception as exc:
            ui.notify(f"Export failed: {exc}", type="negative")

    ui.button("Export Uncertainty Contract ZIP", icon="archive", on_click=_export_zip).props("outline q-mt-sm")
