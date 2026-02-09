"""DSG Panel — user-facing selector, bindings, and pipeline edge capture.

Exploration-layer only. Must not modify physics truth.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from typing import Any, List

import streamlit as st


def _short(s: str, n: int = 12) -> str:
    s = str(s)
    return s if len(s) <= n else (s[: n // 2] + "…" + s[-(n // 2) :])


def build_active_node_markdown(*, g: Any, node_id: str) -> str:
    node_id = str(node_id)
    n = getattr(g, "nodes", {}).get(node_id)
    if n is None:
        return f"# Active Design Node\n\nNode not found: `{node_id}`\n"

    ok = "OK" if bool(getattr(n, "ok", True)) else "FAIL"
    origin = str(getattr(n, "origin", ""))
    msg = str(getattr(n, "message", ""))
    parents = list(getattr(n, "parents", []) or [])
    tags = list(getattr(n, "tags", []) or [])

    lines = [
        "# Active Design Node",
        "",
        f"- node_id: `{getattr(n,'node_id','')}`",
        f"- seq: `{getattr(n,'seq',0)}`",
        f"- status: **{ok}**",
        f"- origin: `{origin}`",
        f"- inputs_sha256: `{getattr(n,'inputs_sha256','')}`",
        f"- outputs_sha256: `{getattr(n,'outputs_sha256','')}`",
        f"- elapsed_s: `{getattr(n,'elapsed_s',0.0)}`",
    ]
    if parents:
        lines.append(f"- parents: {', '.join(f'`{p}`' for p in parents)}")
    if tags:
        lines.append(f"- tags: {', '.join(f'`{t}`' for t in tags)}")
    if msg:
        lines += ["", "## Message", "", msg]
    return "\n".join(lines) + "\n"


def _add_edges_best_effort(*, g: Any, src: str, dsts: List[str], kind: str, note: str) -> int:
    try:
        if hasattr(g, "add_edges"):
            return int(g.add_edges(src=src, dst_list=list(dsts), kind=kind, note=note))
        # Fallback: add individually
        n0 = len(getattr(g, "edges", []) or [])
        for d in dsts:
            try:
                g.add_edge(src=src, dst=str(d), kind=kind, note=note)
            except Exception:
                pass
        return int(len(getattr(g, "edges", []) or []) - n0)
    except Exception:
        return 0


def render_dsg_sidebar(g: Any) -> None:
    if g is None or getattr(g, "nodes", None) is None:
        return

    with st.sidebar.expander("🧬 Design State Graph", expanded=False):
        st.caption("Inter-panel continuity ledger (exploration only).")

        nodes = list(getattr(g, "nodes", {}).values())
        nodes.sort(key=lambda n: (getattr(n, "seq", 0), getattr(n, "node_id", "")))
        if not nodes:
            st.info("No recorded design nodes yet. Run an evaluation to populate DSG.")
            return

        def _label(n: Any) -> str:
            ok = "✅" if bool(getattr(n, "ok", True)) else "❌"
            origin = str(getattr(n, "origin", ""))
            return f"{ok} #{getattr(n,'seq',0):04d}  {_short(getattr(n,'node_id',''), 14)}  ·  {origin}"

        default_id = (
            st.session_state.get("dsg_selected_node_id")
            or getattr(g, "active_node_id", None)
            or nodes[-1].node_id
        )
        options = [n.node_id for n in nodes]
        if default_id not in options:
            default_id = options[-1]

        sel = st.selectbox(
            "Active design node",
            options=options,
            index=options.index(default_id),
            format_func=lambda nid: _label(getattr(g, "nodes", {}).get(nid)),
        )
        st.session_state["dsg_selected_node_id"] = sel
        try:
            g.set_active(sel)
        except Exception:
            pass

        auto_kind = st.checkbox(
            "Auto-set edge kind by active panel",
            value=bool(st.session_state.get("dsg_edge_kind_auto", True)),
            key="dsg_edge_kind_auto",
        )
        edge_kind = st.selectbox(
            "Lineage edge kind for new evaluations",
            options=["derived", "systems_eval", "scan", "pareto", "trade", "extopt", "repair"],
            index=0,
            disabled=auto_kind,
            key="dsg_context_edge_kind_manual",
        )
        st.session_state["dsg_context_edge_kind"] = edge_kind

        n = getattr(g, "nodes", {}).get(sel)
        if n is None:
            return

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Node seq", int(getattr(n, "seq", 0)))
        with c2:
            st.metric("Parents", len(getattr(n, "parents", []) or []))

        # Lineage breadcrumb (deterministic)
        try:
            chain = g.lineage(sel, max_hops=10)
        except Exception:
            chain = [sel]
        st.markdown("**Lineage**")
        st.code(" -> ".join(_short(x, 10) for x in chain), language="text")

        # Bindings
        st.markdown("**Bindings**")
        st.caption("Adopt active node inputs into panel widgets (UI-only).")
        if st.button("Adopt active node into Point Designer", use_container_width=True):
            try:
                from ui.dsg_bindings import adopt_active_node_into_point_designer

                ok = bool(adopt_active_node_into_point_designer(g=g, node_id=sel))
            except Exception:
                ok = False
            if ok:
                st.success("Adopted: Point Designer + Systems baseline updated from active DSG node.")
                st.rerun()
            else:
                st.warning("Could not adopt node inputs into Point Designer (node missing or incompatible).")

        # Pipeline edge capture (for batch pipelines that didn't call DSG.record)
        st.markdown("**Pipeline edge capture**")
        st.caption("Attach lineage edges for sets produced by scans/frontiers/trade/extopt.")

        scan_ids = st.session_state.get("scan_last_node_ids") or []
        scan_parent = st.session_state.get("scan_last_parent_node_id") or ""
        if scan_ids and scan_parent:
            if st.button("Link last Scan set", use_container_width=True):
                added = _add_edges_best_effort(g=g, src=str(scan_parent), dsts=list(scan_ids), kind="scan", note="pipeline:auto")
                st.info(f"Added {added} DSG edges for Scan set.")

        pareto_ids = st.session_state.get("pareto_last_node_ids") or []
        pareto_parent = st.session_state.get("pareto_last_parent_node_id") or ""
        if pareto_ids and pareto_parent:
            if st.button("Link last Pareto set", use_container_width=True):
                added = _add_edges_best_effort(g=g, src=str(pareto_parent), dsts=list(pareto_ids), kind="pareto", note="pipeline:auto")
                st.info(f"Added {added} DSG edges for Pareto set.")

        trade_ids = st.session_state.get("trade_last_node_ids") or []
        trade_parent = st.session_state.get("trade_last_parent_node_id") or ""
        if trade_ids and trade_parent:
            if st.button("Link last Trade subset", use_container_width=True):
                added = _add_edges_best_effort(g=g, src=str(trade_parent), dsts=list(trade_ids), kind="trade", note="pipeline:auto")
                st.info(f"Added {added} DSG edges for Trade subset.")

        ext_ids = st.session_state.get("extopt_last_node_ids") or []
        ext_parent = st.session_state.get("extopt_last_parent_node_id") or ""
        if ext_ids and ext_parent:
            if st.button("Link last ExtOpt proposals", use_container_width=True):
                added = _add_edges_best_effort(g=g, src=str(ext_parent), dsts=list(ext_ids), kind="extopt", note="pipeline:auto")
                st.info(f"Added {added} DSG edges for ExtOpt proposals.")

        # Export
        if st.button("Export active node summary", use_container_width=True):
            md = build_active_node_markdown(g=g, node_id=sel)
            st.download_button(
                "Download ACTIVE_NODE.md",
                data=md.encode("utf-8"),
                file_name="ACTIVE_NODE.md",
                mime="text/markdown",
                use_container_width=True,
            )
