"""Tokamak Constitutional Atlas panel (Batch 9)."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.decks.publication_benchmarks import verdict
from ui_nicegui.lib.benchmark_helpers import (
    atlas_evidence_json,
    atlas_result_to_dict,
    build_preset_buckets,
    constitution_diff_rows,
    evaluate_atlas,
    run_fragility_scan,
    summarize_atlas_result,
)
from ui_nicegui.session import DesignSession


def render_constitutional_atlas(
    session: DesignSession,
    *,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    buckets = build_preset_buckets()
    bucket_names = list(buckets.keys())
    if not bucket_names:
        ui.label("Reference catalog unavailable.").classes("text-negative")
        return

    if not session.pub_atlas_bucket or session.pub_atlas_bucket not in bucket_names:
        session.pub_atlas_bucket = bucket_names[0]
    opts = buckets.get(session.pub_atlas_bucket) or []
    if opts and (not session.pub_atlas_preset_key or session.pub_atlas_preset_key not in [o[0] for o in opts]):
        session.pub_atlas_preset_key = opts[0][0]

    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-1"):
            ui.label("Preset").classes("text-subtitle2")
            ui.select(
                bucket_names,
                label="Category",
                value=session.pub_atlas_bucket,
                on_change=lambda e: _on_bucket_change(session, buckets, str(e.value)),
            ).classes("w-full")
            labels = [o[1] for o in opts]
            keys = [o[0] for o in opts]
            if labels:
                cur = session.pub_atlas_preset_key if session.pub_atlas_preset_key in keys else keys[0]
                ui.select(
                    labels,
                    label="Tokamak",
                    value=labels[keys.index(cur)] if cur in keys else labels[0],
                    on_change=lambda e: setattr(
                        session,
                        "pub_atlas_preset_key",
                        keys[labels.index(str(e.value))],
                    ),
                ).classes("w-full")
            ui.toggle(
                ["Research", "Reactor"],
                value=session.pub_atlas_intent,
                on_change=lambda e: setattr(session, "pub_atlas_intent", str(e.value)),
            ).classes("q-mt-sm")
            ui.label(f"Preset key: {session.pub_atlas_preset_key}").classes("text-caption text-grey")
        with ui.column().classes("flex-[2]"):
            _render_atlas_verdict_section(session)
            _render_atlas_actions(session, on_complete=on_complete)
            _render_atlas_detail(session)


def _on_bucket_change(session: DesignSession, buckets: dict, bucket: str) -> None:
    session.pub_atlas_bucket = bucket
    opts = buckets.get(bucket) or []
    if opts:
        session.pub_atlas_preset_key = opts[0][0]


@ui.refreshable
def _render_atlas_verdict_section(session: DesignSession) -> None:
    summary = None
    if isinstance(session.pub_atlas_last, dict):
        summary = summarize_atlas_result(session.pub_atlas_last)
    verdict.render_atlas_verdict(summary)


def _render_atlas_actions(session: DesignSession, *, on_complete: Optional[Callable[[], None]] = None) -> None:
    if session.pub_atlas_running:
        ui.linear_progress(show_value=False).props("indeterminate").classes("w-full q-my-sm")

    async def _evaluate() -> None:
        if session.pub_atlas_running:
            return
        key = session.pub_atlas_preset_key
        if not key:
            ui.notify("Select a preset", type="warning")
            return
        session.pub_atlas_running = True
        ui.notify("Evaluating preset…", type="info")
        try:
            res = await run.io_bound(evaluate_atlas, key, session.pub_atlas_intent)
            session.pub_atlas_last = atlas_result_to_dict(res)
            session.pub_atlas_fragility = None
            ui.notify(f"Verdict: {(session.pub_atlas_last.get('run') or {}).get('verdict', 'done')}", type="positive")
            _render_atlas_verdict_section.refresh()
            _render_atlas_detail.refresh()
            if on_complete:
                on_complete()
        except Exception as exc:
            session.last_error = str(exc)
            ui.notify(f"Atlas evaluation failed: {exc}", type="negative")
        finally:
            session.pub_atlas_running = False

    async def _fragility() -> None:
        if session.pub_atlas_fragility_running:
            return
        key = session.pub_atlas_preset_key
        if not key:
            return
        session.pub_atlas_fragility_running = True
        try:
            scan = await run.io_bound(run_fragility_scan, key, session.pub_atlas_intent)
            session.pub_atlas_fragility = scan
            _render_atlas_detail.refresh()
            ui.notify("Fragility scan complete", type="positive")
        except Exception as exc:
            ui.notify(f"Fragility scan failed: {exc}", type="negative")
        finally:
            session.pub_atlas_fragility_running = False

    with ui.row().classes("gap-2 q-mt-sm"):
        ui.button("Evaluate preset", icon="play_arrow", on_click=_evaluate).props("color=primary")
        ui.button("Local fragility scan", icon="grid_on", on_click=_fragility).props("outline")


@ui.refreshable
def _render_atlas_detail(session: DesignSession) -> None:
    res = session.pub_atlas_last
    if not isinstance(res, dict):
        return

    with ui.tabs().classes("w-full q-mt-md") as tabs:
        t1 = ui.tab("Constitution diff")
        t2 = ui.tab("Fragility")
        t3 = ui.tab("Evidence")

    with ui.tab_panels(tabs, value=t1).classes("w-full"):
        with ui.tab_panel(t1):
            diff_rows = constitution_diff_rows(res)
            if not diff_rows:
                ui.label("No constitutional differences (selected intent matches native semantics).").classes(
                    "text-positive"
                )
            else:
                ui.table(
                    columns=[
                        {"name": "clause", "label": "Clause", "field": "clause", "align": "left"},
                        {"name": "selected", "label": "Selected", "field": "selected"},
                        {"name": "native", "label": "Native", "field": "native"},
                    ],
                    rows=diff_rows,
                    row_key="clause",
                ).classes("w-full")
            with ui.expansion("Constitution JSON", icon="code").classes("w-full"):
                ui.json(res.get("constitution_selected") or {})

        with ui.tab_panel(t2):
            scan = session.pub_atlas_fragility
            if not isinstance(scan, dict):
                ui.label("Run local fragility scan to classify robustness/fragility.").classes("text-caption")
            else:
                ui.markdown(
                    f"**Pass fraction:** {float(scan.get('pass_fraction', 0)):.2f} · "
                    f"**Mechanism stable:** {'Yes' if scan.get('mechanism_stable', True) else 'No'}"
                )
                wm = scan.get("worst_margin_min")
                if isinstance(wm, (int, float)):
                    ui.markdown(f"**Worst margin (min):** {float(wm):.3f}")
                ui.json(scan)

        with ui.tab_panel(t3):
            data = atlas_evidence_json(res)
            ui.button(
                "Download Atlas Evidence (JSON)",
                icon="download",
                on_click=lambda: ui.download(
                    data,
                    f"atlas_{str(res.get('selected_intent', 'intent')).lower()}_{str(res.get('preset_key', 'preset')).replace('|', '_')}.json",
                ),
            ).props("outline")
