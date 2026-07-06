"""Scan Lab orientation — contract, freeze, golden scans, restore hints."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.scan_archive_helpers import freeze_statement_text
from ui_nicegui.lib.scan_helpers import SCAN_VAR_KEYS, SCAN_VAR_LABELS
from ui_nicegui.lib.scan_labels import INTENT_HELP, PROJECTION_CAVEAT
from ui_nicegui.session import DesignSession


def render_orientation_panel(session: DesignSession, *, default_open: bool = False) -> None:
    with ui.expansion("Scan Lab contract & teaching", icon="school", value=default_open).classes("w-full"):
        ui.markdown(
            "**What this mode does**\n"
            "- Maps frozen Point Designer truth across a chosen 2D parameter plane\n"
            "- Reveals dominant constraints, cliffs, intent splits, and robustness categories\n"
            "- Exports replayable scan artifacts and atlases\n\n"
            "**What this mode does not do**\n"
            "- Optimize, relax constraints, or recommend a best design\n"
            "- Apply changes to your base point automatically\n"
            "- Redefine physics or hide empty regions"
        )
        ui.markdown(INTENT_HELP).classes("text-caption q-mt-sm")
        ui.markdown(PROJECTION_CAVEAT).classes("text-caption text-orange q-mt-xs")
        ui.markdown(
            "Legacy nested grid (Ti/H98/a/Q/g_conf) is available below in NiceGUI for expert workflows — "
            "solver-assisted screening, not frozen cartography."
        ).classes("text-caption text-grey q-mt-xs")
        ui.markdown(
            "**One-scan benchmark** (Streamlit legacy self-check) is not in NiceGUI — use golden scans + freeze QA on Export."
        ).classes("text-caption text-grey q-mt-xs")

        with ui.expansion("One-scan learning check", icon="psychology_alt").classes("w-full"):
            ui.label(
                "After your first map: did you learn what fundamentally limits this slice? "
                "Capture it here for your design journal."
            ).classes("text-caption q-mb-sm")
            ui.checkbox(
                "I learned something fundamental about what limits this design space",
                value=bool(session.scan_benchmark_learned),
                on_change=lambda e: setattr(session, "scan_benchmark_learned", bool(e.value)),
            )
            ui.textarea(
                "What did you learn? (optional)",
                value=session.scan_benchmark_note or "",
                on_change=lambda e: setattr(session, "scan_benchmark_note", str(e.value or "")),
            ).classes("w-full")

        with ui.expansion("How to think with Scan Lab", icon="psychology").classes("w-full"):
            ui.markdown(
                "Scan Lab is a **microscope**, not an engine.\n\n"
                "- It maps the frozen Point Designer truth across a space.\n"
                "- It does not search for 'best' designs.\n"
                "- If a region is empty, nature (given assumptions) said *no*.\n\n"
                "Use it to answer: *What limits me? Where are the cliffs? Which direction helps most?*"
            )

        with ui.expansion("Freeze statement", icon="gavel").classes("w-full"):
            text = freeze_statement_text()
            ui.button(
                "Download freeze statement",
                icon="download",
                on_click=lambda: ui.download(text.encode("utf-8"), "SCANLAB_FREEZE.md"),
            ).props("outline flat")
            ui.markdown(text[:2000] + ("…" if len(text) > 2000 else "")).classes("text-caption")

        with ui.expansion("Cartography parameter guide", icon="table_chart").classes("w-full"):
            rows = [
                {
                    "key": k,
                    "label": SCAN_VAR_LABELS.get(k, k),
                    "meaning": _param_meaning(k),
                }
                for k in SCAN_VAR_KEYS
            ]
            ui.table(
                columns=[
                    {"name": "key", "label": "Key", "field": "key"},
                    {"name": "label", "label": "Label", "field": "label", "align": "left"},
                    {"name": "meaning", "label": "Meaning", "field": "meaning", "align": "left"},
                ],
                rows=rows,
                row_key="key",
            ).classes("w-full")

        with ui.expansion("Scan Lab contract", icon="description").classes("w-full"):
            try:
                from tools.scan_expert_features import SCAN_LAB_CONTRACT
                from tools.scan_visual_identity import VISUAL_IDENTITY

                ui.markdown(SCAN_LAB_CONTRACT)
                ui.label(f"Visual semantics: {getattr(VISUAL_IDENTITY, 'version', 'frozen')}").classes(
                    "text-caption text-grey"
                )
            except ImportError:
                ui.label("Contract module unavailable.").classes("text-caption text-grey")

        _render_physics_mapping()
        _render_canonical_questions(session)
        _render_golden_presets_full(session)
        from ui_nicegui.decks.scan_lab.legacy_nested_ui import render_legacy_nested_panel

        render_legacy_nested_panel(session)


def _render_physics_mapping() -> None:
    rows = [
        {"parameter": "R0_m", "blocks": "Geometry, magnets, exhaust"},
        {"parameter": "a_m", "blocks": "Geometry, Greenwald, exhaust"},
        {"parameter": "Bt_T", "blocks": "Magnets, confinement, fusion power"},
        {"parameter": "Ip_MA", "blocks": "Plasma, q95, exhaust, confinement"},
        {"parameter": "fG", "blocks": "Greenwald, density limits"},
        {"parameter": "Paux_MW", "blocks": "Heating, H-mode, Q, exhaust"},
        {"parameter": "kappa", "blocks": "Geometry, exhaust, stability proxies"},
        {"parameter": "Ti_keV", "blocks": "Plasma performance, confinement"},
    ]
    with ui.expansion("Physics block mapping (cartography axes)", icon="account_tree").classes("w-full"):
        ui.table(
            columns=[
                {"name": "parameter", "label": "Parameter", "field": "parameter"},
                {"name": "blocks", "label": "Physics blocks", "field": "blocks", "align": "left"},
            ],
            rows=rows,
            row_key="parameter",
        ).classes("w-full")


def _param_meaning(key: str) -> str:
    return {
        "R0_m": "Major radius",
        "a_m": "Minor radius",
        "Bt_T": "Toroidal field on axis",
        "Ip_MA": "Plasma current",
        "fG": "Greenwald fraction",
        "Paux_MW": "Auxiliary heating power",
        "kappa": "Elongation",
        "Ti_keV": "Ion temperature (axis)",
    }.get(key, "PointInputs scalar")


def _render_canonical_questions(session: DesignSession) -> None:
    try:
        from tools.canonical_questions import build_canonical_questions
    except ImportError:
        return
    try:
        qs = build_canonical_questions()
    except Exception:
        return
    if not qs:
        return
    with ui.expansion("Canonical questions (teaching)", icon="quiz").classes("w-full"):
        labels = [str(q.get("question") or "question") for q in qs]
        pick = ui.select(labels, label="Pick a question", value=labels[0]).classes("w-full")
        q = qs[labels.index(pick.value) if pick.value in labels else 0]
        ui.markdown(f"**Hint:** {q.get('hint', '')}").classes("text-caption")
        if q.get("suggested_golden_label"):
            ui.label(f"Suggested golden scan: {q.get('suggested_golden_label')}").classes(
                "text-caption text-grey"
            )


def _render_golden_presets_full(session: DesignSession) -> None:
    try:
        from tools.golden_scans import build_golden_scan_presets
    except ImportError:
        return
    base = session.build_point_inputs()
    try:
        presets = build_golden_scan_presets(base_inputs=base)
    except Exception:
        return
    if not presets:
        return
    labels = [str(p.get("label") or p.get("id") or "preset") for p in presets]
    with ui.expansion("Golden scans (teaching + QA)", icon="star").classes("w-full"):
        pick = ui.select(labels, label="Preset", value=labels[0]).classes("w-full")

        def _show_note() -> None:
            idx = labels.index(pick.value) if pick.value in labels else 0
            gp = presets[idx]
            ui.notify(str(gp.get("note") or "Golden scan preset"), type="info")

        def _load() -> None:
            idx = labels.index(pick.value) if pick.value in labels else 0
            gp = presets[idx]
            session.scan_cart_x_key = str(gp.get("x_key") or session.scan_cart_x_key)
            session.scan_cart_y_key = str(gp.get("y_key") or session.scan_cart_y_key)
            session.scan_cart_intents = list(gp.get("intents") or ["Reactor"])
            xr = gp.get("x_range") or []
            yr = gp.get("y_range") or []
            if len(xr) >= 2:
                session.scan_cart_x_lo = float(xr[0])
                session.scan_cart_x_hi = float(xr[1])
            if len(yr) >= 2:
                session.scan_cart_y_lo = float(yr[0])
                session.scan_cart_y_hi = float(yr[1])
            session.scan_cart_nx = int(gp.get("n_x") or session.scan_cart_nx)
            session.scan_cart_ny = int(gp.get("n_y") or session.scan_cart_ny)
            bi = gp.get("base_inputs")
            if bi is not None:
                try:
                    from dataclasses import asdict

                    session.scan_cart_base_override = asdict(bi)
                except Exception:
                    session.scan_cart_base_override = None
            else:
                session.scan_cart_base_override = None
            ui.notify("Loaded golden scan settings — switch to Setup & Run to review.", type="positive")

        with ui.row().classes("gap-2"):
            ui.button("Show preset note", icon="info", on_click=_show_note).props("flat outline")
            ui.button("Load golden scan", icon="upload", on_click=_load).props("outline")

        if session.scan_cart_base_override:
            ui.badge("Baseline override active (from golden scan)", color="orange").props("outline")
