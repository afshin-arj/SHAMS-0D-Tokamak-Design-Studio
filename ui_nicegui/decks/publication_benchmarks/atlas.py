"""Tokamak Constitutional Atlas panel."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.lib.benchmark_helpers import (
    atlas_evidence_json,
    atlas_result_to_dict,
    build_preset_buckets,
    constitution_diff_rows,
    evaluate_atlas,
    run_fragility_scan,
)
from ui_nicegui.lib.helm_helpers import log_ui_event
from ui_nicegui.lib.pub_helpers import (
    PUB_RUNLOCK_OWNER,
    promote_atlas_inputs_to_point_designer,
    release_pub_lock,
    try_acquire_pub_lock,
)
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


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
            _preset_controls(session, buckets)
            ui.toggle(
                ["Research", "Reactor"],
                value=session.pub_atlas_intent,
                on_change=lambda e: setattr(session, "pub_atlas_intent", str(e.value)),
            ).props("data-testid=pb-atlas-intent").classes("q-mt-sm")
            _preset_key_caption(session)
        with ui.column().classes("flex-[2]"):
            _render_atlas_actions(session, on_complete=on_complete)
            _render_atlas_detail(session)


@ui.refreshable
def _preset_controls(session: DesignSession, buckets: dict) -> None:
    """Category + Tokamak selects — dict options + testids for stable automation."""
    bucket_names = list(buckets.keys())
    if not session.pub_atlas_bucket or session.pub_atlas_bucket not in bucket_names:
        session.pub_atlas_bucket = bucket_names[0]

    def _on_category(e) -> None:
        _on_bucket_change(session, buckets, str(e.value))
        _preset_controls.refresh()
        _preset_key_caption.refresh()

    cat = ui.select(
        {name: name for name in bucket_names},
        label="Category",
        value=session.pub_atlas_bucket,
        on_change=_on_category,
    ).classes("w-full")
    cat.props("dense options-dense data-testid=pb-atlas-category")

    opts = buckets.get(session.pub_atlas_bucket) or []
    if not opts:
        ui.label("No presets in this category.").classes("text-caption text-grey")
        return

    key_to_label = {o[0]: o[1] for o in opts}
    keys = list(key_to_label.keys())
    cur = session.pub_atlas_preset_key if session.pub_atlas_preset_key in keys else keys[0]
    session.pub_atlas_preset_key = cur

    def _on_tokamak(e) -> None:
        session.pub_atlas_preset_key = str(e.value)
        _preset_key_caption.refresh()

    tok = ui.select(
        key_to_label,
        label="Tokamak",
        value=cur,
        on_change=_on_tokamak,
    ).classes("w-full")
    # use-input: type-to-filter (ITER/SPARC); dict options bind preset key as value
    tok.props("dense options-dense use-input data-testid=pb-atlas-tokamak")


@ui.refreshable
def _preset_key_caption(session: DesignSession) -> None:
    ui.label(f"Preset key: {session.pub_atlas_preset_key}").classes("text-caption text-grey")


def _on_bucket_change(session: DesignSession, buckets: dict, bucket: str) -> None:
    session.pub_atlas_bucket = bucket
    opts = buckets.get(bucket) or []
    if opts:
        session.pub_atlas_preset_key = opts[0][0]


@ui.refreshable
def _render_atlas_actions(session: DesignSession, *, on_complete: Optional[Callable[[], None]] = None) -> None:
    if session.pub_atlas_running or session.pub_atlas_fragility_running or session.pub_running:
        ui.linear_progress(show_value=False).props("indeterminate").classes("w-full q-my-sm")
        ui.label("Atlas job running — other evaluations locked.").classes("text-caption text-orange")

    async def _evaluate() -> None:
        if session.pub_atlas_running:
            return
        key = session.pub_atlas_preset_key
        if not key:
            ui.notify("Select a preset", type="warning")
            return
        if not try_acquire_pub_lock(session, "Publication Benchmarks: Atlas evaluate"):
            return
        session.pub_atlas_running = True
        _render_atlas_actions.refresh()
        log_ui_event(session, PUB_RUNLOCK_OWNER, "AtlasEvaluateStart", {"preset": key, "intent": session.pub_atlas_intent})
        ui.notify("Evaluating preset…", type="info")
        try:
            res = await run.io_bound(evaluate_atlas, key, session.pub_atlas_intent)
            session.pub_atlas_last = atlas_result_to_dict(res)
            session.pub_atlas_fragility = None
            verdict = (session.pub_atlas_last.get("run") or {}).get("verdict", "done")
            log_ui_event(session, PUB_RUNLOCK_OWNER, "AtlasEvaluateComplete", {"verdict": verdict})
            ui.notify(f"Verdict: {verdict}", type="positive" if verdict != "FAIL" else "warning")
            _render_atlas_detail.refresh()
        except Exception as exc:
            session.last_error = str(exc)
            ui.notify(f"Atlas evaluation failed: {exc}", type="negative")
        finally:
            release_pub_lock(session)
            _render_atlas_actions.refresh()
            # Status remount after flags clear — avoid stuck "Running…".
            if on_complete:
                on_complete()

    async def _fragility() -> None:
        if session.pub_atlas_fragility_running:
            return
        key = session.pub_atlas_preset_key
        if not key:
            return
        if not try_acquire_pub_lock(session, "Publication Benchmarks: Fragility scan"):
            return
        session.pub_atlas_fragility_running = True
        _render_atlas_actions.refresh()
        log_ui_event(session, PUB_RUNLOCK_OWNER, "AtlasFragilityStart", {"preset": key})
        try:
            scan = await run.io_bound(run_fragility_scan, key, session.pub_atlas_intent)
            session.pub_atlas_fragility = scan
            _render_atlas_detail.refresh()
            ui.notify("Fragility scan complete", type="positive")
        except Exception as exc:
            ui.notify(f"Fragility scan failed: {exc}", type="negative")
        finally:
            release_pub_lock(session)
            _render_atlas_actions.refresh()

    def _promote() -> None:
        try:
            n = promote_atlas_inputs_to_point_designer(session)
            from ui_nicegui.lib.pd_handoff import navigate_to_point_designer

            navigate_to_point_designer(session)
            ui.notify(f"Promoted {n} inputs → Point Designer — KPIs STALE until Evaluate Point.", type="warning")
        except Exception as exc:
            ui.notify(str(exc), type="warning")

    with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
        ui.button("Evaluate preset", icon="play_arrow", on_click=_evaluate).props(
            "color=primary data-testid=pb-atlas-evaluate"
        )
        ui.button("Local fragility scan", icon="grid_on", on_click=_fragility).props(
            "outline data-testid=pb-atlas-fragility"
        )
        if isinstance(session.pub_atlas_last, dict):
            ui.button("Load inputs → Point Designer", icon="upload", on_click=_promote).props(
                "flat outline data-testid=pb-atlas-promote"
            )


@ui.refreshable
def _render_atlas_detail(session: DesignSession) -> None:
    res = session.pub_atlas_last
    if not isinstance(res, dict):
        from ui_nicegui.components.empty_state import empty_state

        empty_state(
            "Select category → tokamak → Research/Reactor → **Evaluate preset**.",
            kind="info",
        )
        return

    expert = bool(getattr(session, "pub_expert_view", False))

    def _constitution_block() -> None:
        ui.label("Constitution diff (documentation semantics)").classes("text-subtitle2")
        ui.label(
            "Clause maps describe Research vs Reactor policy language — blocking feasibility uses the intent hard-set."
        ).classes("text-caption text-grey q-mb-xs")
        diff_rows = constitution_diff_rows(res)
        if not diff_rows:
            ui.label("No constitutional differences (selected intent matches native semantics).").classes(
                "text-positive text-caption"
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
            render_json_blob(res.get("constitution_selected") or {})

    def _fragility_block() -> None:
        ui.label("Local fragility scan").classes("text-subtitle2 q-mt-md")
        scan = session.pub_atlas_fragility
        if not isinstance(scan, dict):
            ui.markdown("Run **Local fragility scan** to classify robustness in a small input neighborhood.").classes(
                "text-caption text-grey"
            )
        else:
            ui.markdown(
                f"**Pass fraction:** {float(scan.get('pass_fraction', 0)):.2f} · "
                f"**Mechanism stable:** {'Yes' if scan.get('mechanism_stable', True) else 'No'}"
            )
            wm = scan.get("worst_margin_min")
            if isinstance(wm, (int, float)):
                ui.markdown(f"**Worst margin (min):** {float(wm):.3f}")
            if expert:
                render_json_blob(scan)

    def _evidence_block() -> None:
        ui.label("Evidence export").classes("text-subtitle2 q-mt-md")
        data = atlas_evidence_json(res)
        ui.button(
            "Download Atlas Evidence (JSON)",
            icon="download",
            on_click=lambda: ui.download(
                data,
                f"atlas_{str(res.get('selected_intent', 'intent')).lower()}_{str(res.get('preset_key', 'preset')).replace('|', '_')}.json",
            ),
        ).props("outline")
        ui.label(
            "Deterministic single-case capsule: inputs, outputs, ledger, constitution semantics, SHA-256 stamp. "
            "PHYS-KPI-001: claim KPIs on FAIL runs are watermarked as diagnostic in the download."
        ).classes("text-caption text-grey")

    if expert:
        with ui.tabs().classes("w-full q-mt-md") as tabs:
            t1 = ui.tab("Constitution diff")
            t2 = ui.tab("Fragility")
            t3 = ui.tab("Evidence")
        with ui.tab_panels(tabs, value=t1).classes("w-full"):
            with ui.tab_panel(t1):
                _constitution_block()
            with ui.tab_panel(t2):
                _fragility_block()
            with ui.tab_panel(t3):
                _evidence_block()
    else:
        ui.separator().classes("q-my-md")
        _constitution_block()
        _fragility_block()
        _evidence_block()
