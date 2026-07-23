"""Publication Benchmark Pack generator."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.helm_helpers import log_ui_event
from ui_nicegui.lib.pub_benchmark_extended_helpers import (
    explain_benchmark_delta,
    list_baseline_packs,
    publication_case_set_options,
    read_pack_topology,
    read_topology_regression_report,
    run_publication_benchmark_pack,
)
from ui_nicegui.lib.pub_helpers import (
    PUB_RUNLOCK_OWNER,
    pack_summary_from_outdir,
    release_pub_lock,
    try_acquire_pub_lock,
    zip_pack_outdir,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_benchmark_pack(
    session: DesignSession,
    *,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    open_help = session.pub_teaching_mode and not session.pub_expert_view
    from ui_nicegui.decks.publication_benchmarks.orientation import render_pack_orientation

    render_pack_orientation(default_open=open_help)

    ui.label("Generate pack").classes("text-subtitle2 q-mt-sm")
    ui.label(
        "In-process batch over frozen Point Designer cases → CSV/JSON under benchmarks/publication/out_ui/. "
        "Use **Literature only** for paper claims; **Inspired only** for qualitative screening."
    ).classes("text-caption text-grey q-mb-sm")

    if session.pub_expert_view:
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

    opts = publication_case_set_options()
    labels = [o[0] for o in opts]
    file_by_label = {o[0]: o[1] for o in opts}
    label_by_file = {o[1]: o[0] for o in opts}
    cur_file = session.pub_bench_cases_file or "cases_point_designer.json"
    if cur_file not in label_by_file:
        cur_file = "cases_point_designer.json"
        session.pub_bench_cases_file = cur_file
    case_sel = ui.select(
        labels,
        label="Case set",
        value=label_by_file[cur_file],
    ).classes("w-full")
    ui.label(
        "Literature = cited geometry tables (STEP/DEMO/…). Inspired = qualitative envelopes (ITER/JET/…). "
        "Combined = both."
    ).classes("text-caption text-grey q-mb-sm")

    ack = ui.checkbox(
        "I understand this is a non-interactive, audit-grade run.",
        value=session.pub_bench_ack,
    )

    if session.pub_bench_running or session.pub_running:
        ui.label("Pack generate running — other evaluations locked.").classes("text-caption text-orange")

    async def _generate() -> None:
        session.pub_bench_ack = bool(ack.value)
        if not session.pub_bench_ack:
            ui.notify("Acknowledge the audit-grade run first", type="warning")
            return
        if session.pub_bench_running:
            return
        if not try_acquire_pub_lock(session, "Publication Benchmarks: Pack generate"):
            return
        session.pub_bench_running = True
        session.pub_bench_cases_file = file_by_label.get(str(case_sel.value), "cases_point_designer.json")
        session.pub_bench_progress = "Starting…"
        _pack_busy.refresh()
        log_ui_event(
            session,
            PUB_RUNLOCK_OWNER,
            "PackGenerateStart",
            {"cases_file": session.pub_bench_cases_file},
        )
        ui.notify("Benchmark pack run started (in-process)…", type="info")
        from ui_nicegui.lib.navigation import refresh_helm

        refresh_helm()

        def _progress(case_id: str, i: int, n: int) -> None:
            session.pub_bench_progress = f"{i}/{n} {case_id}"

        timer = ui.timer(0.4, lambda: _pack_busy.refresh(), active=True)
        try:
            rep = await run.io_bound(
                run_publication_benchmark_pack,
                also_opposite_intent=True,
                cases_file=session.pub_bench_cases_file,
                progress_cb=_progress,
            )
            session.pub_bench_last_outdir = rep.get("outdir")
            session.pub_bench_last_rc = rep.get("returncode")
            session.pub_bench_last_log = (rep.get("stdout") or "") + "\n" + (rep.get("stderr") or "")
            session.pub_bench_progress = ""
            rc = int(rep.get("returncode") or 1)
            summ = pack_summary_from_outdir(session.pub_bench_last_outdir)
            log_ui_event(
                session,
                PUB_RUNLOCK_OWNER,
                "PackGenerateComplete",
                {
                    "rc": rc,
                    "n_pass": summ.get("n_pass"),
                    "n_fail": summ.get("n_fail"),
                    "cases_file": session.pub_bench_cases_file,
                    "n_cases": rep.get("n_cases"),
                },
            )
            ui.notify(
                "Benchmark pack complete" if rc == 0 else f"Benchmark run finished with failures (rc={rc})",
                type="positive" if rc == 0 else "warning",
            )
            _pack_view.refresh()
            refresh_helm()
        except Exception as exc:
            ui.notify(f"Benchmark run failed: {exc}", type="negative")
        finally:
            timer.deactivate()
            release_pub_lock(session)
            session.pub_bench_progress = ""
            _pack_busy.refresh()
            # Status remount after flags clear — avoid stuck "Running…".
            if on_complete:
                on_complete()

    @ui.refreshable
    def _pack_busy() -> None:
        if session.pub_bench_running or session.pub_running:
            ui.linear_progress(show_value=False).props("indeterminate").classes("w-full q-my-sm")
            prog = session.pub_bench_progress or "Running cases…"
            ui.label(f"Progress: {prog}").classes("text-caption text-orange")

    _pack_busy()
    gen_btn = ui.button(
        "Generate Publication Benchmark Pack",
        icon="play_arrow",
        on_click=_generate,
        color="primary",
    )
    if session.pub_bench_running or session.pub_running:
        gen_btn.props("disable loading")

    _pack_view(session)


@ui.refreshable
def _pack_view(session: DesignSession) -> None:
    outdir = session.pub_bench_last_outdir
    rc = session.pub_bench_last_rc
    if not outdir:
        empty_state(
            "Pick a case set → Acknowledge → **Generate pack** → inspect blocking pass/fail → download CSV/ZIP.",
            kind="info",
        )
        return
    ui.label(f"Last output: {outdir} (rc={rc}) · cases={session.pub_bench_cases_file}").classes(
        "text-caption q-mt-sm"
    )
    log = session.pub_bench_last_log or ""
    if log.strip():
        with ui.expansion("Runner log (per-case progress)", icon="terminal").classes("w-full"):
            ui.code(log.strip()[:8000])
    if int(rc or 1) != 0:
        empty_state(
            f"Pack runner reported failures (rc={rc}). Open the runner log above; "
            "blocking fails are valid NO-SOLUTION outcomes — check case errors vs intent policy.",
            kind="warn",
        )
        # Still show KPIs if summary exists
    summ = pack_summary_from_outdir(outdir)
    if summ.get("loaded"):
        kpi_row([
            ("Pass frac", f"{100.0 * summ['pass_frac']:.0f}%"),
            ("Robust frac", f"{100.0 * summ['robust_frac']:.0f}%"),
            ("Fragile frac", f"{100.0 * summ['fragile_frac']:.0f}%"),
            ("Fail frac", f"{100.0 * summ['fail_frac']:.0f}%"),
        ])

    if int(rc or 1) != 0 and not summ.get("loaded"):
        return

    topo = read_pack_topology(outdir)
    if isinstance(topo, dict):
        with ui.expansion("Dominant mechanism histogram", icon="bar_chart").classes("w-full"):
            render_json_blob(topo.get("dominant_mechanism_hist") or {})

    async def _zip() -> None:
        try:
            data = await run.io_bound(zip_pack_outdir, outdir)
            ui.download(data, "publication_benchmark_pack.zip")
            ui.notify("Pack ZIP ready", type="positive")
        except Exception as exc:
            ui.notify(f"ZIP failed: {exc}", type="negative")

    with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
        ui.button("Download pack ZIP", icon="archive", on_click=_zip).props("color=primary outline")
        csv_path = summ.get("csv") if summ.get("loaded") else None
        if csv_path:
            from pathlib import Path

            p = Path(str(csv_path))
            if p.is_file():
                ui.button(
                    "Download CSV table",
                    icon="table_view",
                    on_click=lambda: ui.download(p.read_bytes(), "point_designer_benchmark_table.csv"),
                ).props("outline")
                ui.label(
                    "PHYS-KPI-001: claim columns (Q / H98 / Pfus / P_net) on FAIL rows are "
                    "— (diagnostic) in the CSV — not paper achievements."
                ).classes("text-caption text-grey")

    ui.label("Explain delta vs baseline").classes("text-subtitle2 q-mt-md")
    baselines = list_baseline_packs()
    if not baselines or (len(baselines) == 1 and not _baseline_usable(baselines[0])):
        ui.label("No baseline packs found under benchmarks/publication/baselines/.").classes("text-caption text-grey")
        return
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


def _baseline_usable(p: str) -> bool:
    from pathlib import Path

    path = Path(p)
    return path.is_dir() and any(path.iterdir()) if path.exists() else False


@ui.refreshable
def _delta_view(session: DesignSession) -> None:
    md = session.pub_bench_delta_md or ""
    if md.strip():
        with ui.expansion("delta.md", icon="description").classes("w-full"):
            if "PHYS-KPI-001" in md or "diagnostic" in md.lower():
                ui.label(
                    "PHYS-KPI-001: claim KPI deltas involving FAIL rows are diagnostic — not design achievements."
                ).classes("text-caption text-orange q-mb-xs")
            ui.markdown(md[:12000])
