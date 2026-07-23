"""Design State Graph sidebar — NiceGUI port of ui/dsg_panel.render_dsg_sidebar."""
from __future__ import annotations

from typing import Any

from nicegui import ui

from ui.dsg_panel import build_active_node_markdown, _short
from ui_nicegui.components.helm_theme import helm_dark_props
from ui_nicegui.lib.deck_dsg_hooks import normalize_edge_kind
from ui_nicegui.lib.dsg_session import ensure_dsg, save_dsg_best_effort
from ui_nicegui.lib.helm_helpers import log_ui_event
from ui_nicegui.session import DesignSession

_EDGE_KINDS = ["derived", "systems_eval", "scan", "pareto", "trade", "extopt", "repair", "forge"]


def render_dsg_sidebar(session: DesignSession) -> None:
    g = ensure_dsg(session)
    if g is None or getattr(g, "nodes", None) is None:
        return

    with ui.expansion("Design lineage graph (DSG)", icon="account_tree").classes("w-full overflow-hidden"):
        ui.label(
            "Exploration-only continuity ledger — links evaluations across decks. Does not change frozen physics."
        ).classes("text-caption q-mb-sm")
        _dsg_body(session)


@ui.refreshable
def _dsg_body(session: DesignSession) -> None:
    """Node detail + adopt/download — refreshes when Active design node changes."""
    g = ensure_dsg(session)
    if g is None or getattr(g, "nodes", None) is None:
        return

    nodes = list(getattr(g, "nodes", {}).values())
    nodes.sort(key=lambda n: (getattr(n, "seq", 0), getattr(n, "node_id", "")))
    if not nodes:
        ui.label("No design nodes yet. Evaluate a point to populate the graph.").classes("text-caption")
        return

    def _label(n: Any) -> str:
        ok = "OK" if bool(getattr(n, "ok", True)) else "FAIL"
        origin = str(getattr(n, "origin", ""))
        return f"{ok} #{getattr(n, 'seq', 0):04d}  {_short(getattr(n, 'node_id', ''), 14)}  ·  {origin}"

    options = [n.node_id for n in nodes]
    default_id = (
        session.dsg_selected_node_id
        or getattr(g, "active_node_id", None)
        or options[-1]
    )
    if default_id not in options:
        default_id = options[-1]

    def _select_node(e) -> None:
        session.dsg_selected_node_id = str(e.value)
        try:
            g.set_active(str(e.value))
        except Exception:
            pass
        save_dsg_best_effort(session)
        _dsg_body.refresh()

    ui.select(
        options,
        label="Active design node",
        value=default_id,
        on_change=_select_node,
    ).props(helm_dark_props()).classes("w-full")
    _sel_preview = getattr(g, "nodes", {}).get(default_id)
    if _sel_preview is not None:
        ui.label(_label(_sel_preview)).classes("text-caption text-grey q-mb-xs")

    ui.checkbox(
        "Auto-set edge kind from active deck",
        value=bool(session.dsg_edge_kind_auto),
        on_change=lambda e: setattr(session, "dsg_edge_kind_auto", bool(e.value)),
    )
    edge_kind = normalize_edge_kind(session.dsg_context_edge_kind)
    if edge_kind != session.dsg_context_edge_kind:
        session.dsg_context_edge_kind = edge_kind
    ui.select(
        _EDGE_KINDS,
        label="Lineage edge kind for new evaluations",
        value=edge_kind,
        on_change=lambda e: setattr(
            session, "dsg_context_edge_kind", normalize_edge_kind(str(e.value))
        ),
    ).props(helm_dark_props("disable" if session.dsg_edge_kind_auto else "")).classes("w-full")

    sel = session.dsg_selected_node_id or default_id
    n = getattr(g, "nodes", {}).get(sel)
    if n is None:
        return

    with ui.row().classes("gap-4"):
        ui.label(f"Seq: {int(getattr(n, 'seq', 0))}").classes("text-caption")
        ui.label(f"Parents: {len(getattr(n, 'parents', []) or [])}").classes("text-caption")

    try:
        chain = g.lineage(sel, max_hops=10)
    except Exception:
        chain = [sel]
    ui.label("Lineage").classes("text-caption text-weight-bold q-mt-xs")
    ui.code(" -> ".join(_short(x, 10) for x in chain), language="text").classes(
        "text-caption w-full"
    ).style("max-width: 100%; overflow-x: auto; white-space: pre-wrap; word-break: break-all;")

    async def _adopt() -> None:
        try:
            from ui.dsg_bindings import adopt_active_node_into_point_designer

            ok = bool(adopt_active_node_into_point_designer(g=g, node_id=sel))
        except Exception:
            ok = False
        if ok:
            log_ui_event(session, "UI", "DSGAdopt", {"node_id": sel})
            from ui_nicegui.lib.pd_handoff import (
                invalidate_point_designer_after_seed,
                navigate_to_point_designer,
            )

            invalidate_point_designer_after_seed(session)
            navigate_to_point_designer(session)
            ui.notify(
                "Adopted active node — prior KPIs cleared; Evaluate Point to re-certify.",
                type="warning",
            )
        else:
            ui.notify("Could not adopt node (missing or incompatible inputs).", type="warning")

    ui.button("Adopt node → Point Designer inputs", on_click=_adopt).props("outline dense").classes(
        "w-full q-mt-sm"
    )

    ui.label("Pipeline edge capture").classes("text-caption text-weight-bold q-mt-sm")
    _link_pipeline(session, g, sel, "scan_last_node_ids", "scan_last_parent_node_id", "scan", "Link last Scan set")
    _link_pipeline(session, g, sel, "pareto_last_node_ids", "pareto_last_parent_node_id", "pareto", "Link last Pareto set")
    _link_pipeline(session, g, sel, "trade_last_node_ids", "trade_last_parent_node_id", "trade", "Link last Trade subset")
    _link_pipeline(session, g, sel, "extopt_last_node_ids", "extopt_last_parent_node_id", "extopt", "Link last ExtOpt proposals")

    md = build_active_node_markdown(g=g, node_id=sel)

    ui.button(
        "Download active node summary (MD)",
        on_click=lambda m=md.encode("utf-8"): ui.download(m, "ACTIVE_NODE.md"),
    ).props("outline dense").classes("w-full q-mt-xs")


def _link_pipeline(
    session: DesignSession,
    g: Any,
    sel: str,
    ids_key: str,
    parent_key: str,
    kind: str,
    label: str,
) -> None:
    ids = getattr(session, ids_key, None) or []
    parent = getattr(session, parent_key, None) or ""
    if not ids or not parent:
        return

    def _link() -> None:
        from ui.dsg_panel import _add_edges_best_effort

        added = _add_edges_best_effort(g=g, src=str(parent), dsts=list(ids), kind=kind, note="pipeline:auto")
        save_dsg_best_effort(session)
        ui.notify(f"Added {added} DSG edge(s) for {kind}.", type="info")

    ui.button(label, on_click=_link).props("flat dense").classes("w-full")
