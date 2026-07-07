"""Publication Benchmark Pack generator."""
from __future__ import annotations

from nicegui import run, ui

from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.pub_benchmark_extended_helpers import (
    explain_benchmark_delta,
    list_baseline_packs,
    read_pack_topology,
    read_topology_regression_report,
    run_publication_benchmark_pack,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_benchmark_pack(session: DesignSession) -> None:
    open_help = session.pub_teaching_mode and not session.pub_expert_view
    from ui_nicegui.decks.publication_benchmarks.orientation import render_pack_orientation

    render_pack_orientation(default_open=open_help)

    ui.label("Generate pack").classes("text-subtitle2 q-mt-sm")

    topo = read_topology_regression_report()
    with ui.expansion("Topology regression (robust/fragile/empty stability)", icon="schema").classes("w-full"):
        if topo is None:
            ui.label("No topology regression report found. Run verification/topology_regression.py.").classes(
                "text-caption text-grey"
            )
        else:
            ok = bool(topo.get("ok"))
            ui.label(f"Result: {'PASS' if ok else 'FAIL'}").classes("text-subtitle2")
            render_json_blob(topo)

    ack = ui.checkbox(
        "I understand this is a non-interactive, audit-grade run.",
        value=session.pub_bench_ack,
    )

    async def _generate() -> None:
        session.pub_bench_ack = bool(ack.value)
        if not session.pub_bench_ack:
            ui.notify("Acknowledge the audit-grade run first", type="warning")
            return
        session.pub_bench_running = True
        ui.notify("Benchmark pack run started…", type="info")
        try:
            rep = await run.io_bound(run_publication_benchmark_pack)
            session.pub_bench_last_outdir = rep.get("outdir")
            session.pub_bench_last_rc = rep.get("returncode")
            session.pub_bench_last_log = (rep.get("stdout") or "") + "\n" + (rep.get("stderr") or "")
            rc = int(rep.get("returncode") or 1)
            ui.notify(
                "Benchmark pack complete" if rc == 0 else f"Benchmark run failed (rc={rc})",
                type="positive" if rc == 0 else "negative",
            )
            _pack_view.refresh()
            from ui_nicegui.lib.navigation import refresh_helm

            refresh_helm()
        except Exception as exc:
            ui.notify(f"Benchmark run failed: {exc}", type="negative")
        finally:
            session.pub_bench_running = False

    ui.button(
        "Generate Publication Benchmark Pack",
        icon="play_arrow",
        on_click=_generate,
        color="primary",
    ).props("outline")

    _pack_view(session)


@ui.refreshable
def _pack_view(session: DesignSession) -> None:
    outdir = session.pub_bench_last_outdir
    rc = session.pub_bench_last_rc
    if not outdir:
        return
    ui.label(f"Last output: {outdir} (rc={rc})").classes("text-caption q-mt-sm")
    log = session.pub_bench_last_log or ""
    if log.strip():
        with ui.expansion("Runner log", icon="terminal").classes("w-full"):
            ui.code(log.strip()[:8000])
    if int(rc or 1) != 0:
        return

    topo = read_pack_topology(outdir)
    if isinstance(topo, dict):
        fr = topo.get("fractions") or {}
        kpi_row([
            ("Pass frac", f"{float(fr.get('pass', 0.0)):.2f}"),
            ("Robust frac", f"{float(fr.get('robust', 0.0)):.2f}"),
            ("Fragile frac", f"{float(fr.get('fragile', 0.0)):.2f}"),
            ("Fail frac", f"{float(fr.get('fail', 0.0)):.2f}"),
        ])
        with ui.expansion("Dominant mechanism histogram", icon="bar_chart").classes("w-full"):
            render_json_blob(topo.get("dominant_mechanism_hist") or {})

    ui.label("Explain delta vs baseline").classes("text-subtitle2 q-mt-md")
    baselines = list_baseline_packs()
    base_sel = ui.select(baselines, label="Baseline pack/folder", value=baselines[0]).classes("w-full")

    async def _delta() -> None:
        try:
            rep = await run.io_bound(
                explain_benchmark_delta,
                baseline=str(base_sel.value),
                candidate=outdir,
            )
            session.pub_bench_delta_md = rep.get("delta_md") or ""
            if int(rep.get("returncode") or 1) == 0:
                ui.notify("Delta explanation written to delta.md", type="positive")
            else:
                ui.notify(f"Delta explainer failed (rc={rep.get('returncode')})", type="negative")
            _delta_view.refresh()
        except Exception as exc:
            ui.notify(f"Delta failed: {exc}", type="negative")

    ui.button("Explain delta (baseline → last pack)", icon="difference", on_click=_delta).props("outline")
    _delta_view(session)


@ui.refreshable
def _delta_view(session: DesignSession) -> None:
    md = session.pub_bench_delta_md or ""
    if md.strip():
        with ui.expansion("delta.md", icon="description").classes("w-full"):
            ui.markdown(md[:12000])
