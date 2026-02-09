# © 2026 Afshin Arjhangmehr
"""
DSG subset linker UI.

Purpose: allow linking a *subset* of rows from pipeline tables (Scan/Pareto/Trade/ExtOpt)
to the currently active DSG parent node, without re-running truth.

This module is Streamlit-only and must not be imported by non-UI paths.
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence

def render_subset_linker(
    *,
    df: "object",
    label: str,
    kind: str,
    note: str = "",
    parent_node_id: Optional[str] = None,
    expander_label: Optional[str] = None,
) -> None:
    """Render a deterministic subset-link UI for any table with a `dsg_node_id` column.

    Parameters
    ----------
    df:
        A pandas-like DataFrame that may contain a `dsg_node_id` column.
    label:
        UI label prefix for this table context.
    kind:
        Edge kind to use when linking nodes (e.g. "pareto_select", "trade_select").
    note:
        Optional note stored on edges.
    parent_node_id:
        Parent node id; if not provided, inferred from Streamlit session_state.
    expander_label:
        Optional expander title.
    """
    try:
        import streamlit as st
    except Exception:
        return

    # Soft import to avoid hard dependency in UI tests that don't load pandas.
    try:
        cols = list(getattr(df, "columns", []))
    except Exception:
        cols = []

    if "dsg_node_id" not in cols:
        return

    try:
        node_ids: Sequence[str] = [str(x) for x in df["dsg_node_id"].tolist() if str(x).strip()]
    except Exception:
        return
    if not node_ids:
        return

    g = st.session_state.get("_shams_dsg")
    if g is None:
        return

    # Infer parent
    if parent_node_id is None:
        parent_node_id = (
            st.session_state.get("dsg_selected_node_id")
            or st.session_state.get("active_design_node_id")
            or st.session_state.get("_dsg_last_parent_node_id")
        )

    if expander_label is None:
        expander_label = f"🔗 DSG subset link — {label}"

    with st.expander(expander_label, expanded=False):
        st.caption(
            "Link selected rows to the active DSG node *without* re-running truth. "
            "This only adds lineage edges in the exploration-layer Design State Graph."
        )

        st.write("**Parent node**:", parent_node_id or "(none)")
        if parent_node_id is None:
            st.warning("No parent node is active/selected. Select a node in the 🧬 DSG panel first.")
            return

        # Deterministic quick-pick: top-N in current table order.
        c1, c2 = st.columns([1, 2])
        with c1:
            top_n = st.number_input("Top N (table order)", min_value=1, max_value=len(node_ids), value=min(10, len(node_ids)), step=1)
        with c2:
            picked_mode = st.radio("Pick mode", ["Top N", "Manual"], horizontal=True)

        if picked_mode == "Top N":
            selected = node_ids[: int(top_n)]
        else:
            selected = st.multiselect("Select node ids", options=node_ids, default=node_ids[: min(5, len(node_ids))])

        selected = [str(x) for x in selected if str(x).strip()]
        st.write("Selected:", len(selected))

        if st.button(f"Link selected → parent ({kind})", use_container_width=True):
            try:
                # Deduplicate while preserving order
                seen = set()
                selected_u = []
                for nid in selected:
                    if nid not in seen:
                        seen.add(nid)
                        selected_u.append(nid)

                g.add_edges(parent_node_id, selected_u, kind=kind, note=note)  # type: ignore[attr-defined]
                # Persist best-effort (do not fail UI)
                try:
                    path = "artifacts/dsg/current_dsg.json"
                    g.save(path)  # type: ignore[attr-defined]
                except Exception:
                    pass
                st.success(f"Linked {len(selected_u)} nodes to {parent_node_id} as '{kind}'.")
            except Exception as e:
                st.error(f"DSG link failed: {type(e).__name__}: {e}")
