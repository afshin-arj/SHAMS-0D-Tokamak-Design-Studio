# © 2026 Afshin Arjhangmehr
"""
DSG subset linker UI.

Purpose: allow linking a *subset* of rows from pipeline tables (Scan/Pareto/Trade/ExtOpt)
to the currently active DSG parent node, without re-running truth.

This module is Streamlit-only and must not be imported by non-UI paths.
"""
from __future__ import annotations

from typing import Optional, Sequence

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

        # Deterministic selection: sort (optional) then link Top-K or pasted ids.
        # Optional: selection-native linking (if Streamlit supports row selection)
        selected_by_ui = []
        try:
            from ui.table_select import dataframe_selected_row_indices  # type: ignore
            if st.checkbox(
                "Enable row-selection capture (if supported)",
                value=True,
                key=f"_dsg_link_selcap_{label}_{kind}",
            ):
                st.caption(
                    "If supported by your Streamlit version, select rows in the table below. "
                    "Otherwise, use Top-N or paste-list."
                )
                rows = dataframe_selected_row_indices(df=df, key=f"_dsg_link_table_{label}_{kind}")
                if rows is not None and len(rows) > 0:
                    try:
                        selected_by_ui = [
                            str(df.iloc[int(i)]["dsg_node_id"])
                            for i in rows
                            if 0 <= int(i) < len(df)
                        ]
                    except Exception:
                        selected_by_ui = []
        except Exception:
            selected_by_ui = []

        if selected_by_ui:
            st.write("Selected (row-selection):", len(selected_by_ui))
            if st.button(
                f"Link selected rows → parent ({kind})",
                use_container_width=True,
                key=f"_dsg_link_btn_rowsel_{label}_{kind}",
            ):
                try:
                    seen = set()
                    selected_u = []
                    for nid in selected_by_ui:
                        if nid and nid not in seen:
                            seen.add(nid)
                            selected_u.append(nid)
                    g.add_edges(parent_node_id, selected_u, kind=kind, note=note)  # type: ignore[attr-defined]
                    try:
                        g.save("artifacts/dsg/current_dsg.json")  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    st.success(
                        f"Linked {len(selected_u)} nodes to {parent_node_id} as '{kind}' (row-selection)."
                    )
                except Exception as e:
                    st.error(f"DSG link failed: {type(e).__name__}: {e}")
                return


        cols_all = list(getattr(df, "columns", []))
        numeric_cols = []
        for c in cols_all:
            if c == "dsg_node_id":
                continue
            try:
                s = df[c]
                # pandas-like: dtype has kind; fall back to attempting float conversion of a sample.
                kind_attr = getattr(getattr(s, "dtype", None), "kind", None)
                if kind_attr in ("i", "u", "f"):
                    numeric_cols.append(c)
                else:
                    # heuristic sample
                    _ = float(s.iloc[0]) if getattr(s, "__len__", lambda: 0)() else None
                    numeric_cols.append(c)
            except Exception:
                pass

        c1, c2 = st.columns([2, 1])
        with c1:
            sort_col = st.selectbox(
                "Optional sort column (deterministic)",
                options=["(table order)"] + sorted(set(numeric_cols)),
                index=0,
                help="If set, SHAMS will sort by this column using a stable sort before selecting Top-N.",
            )
        with c2:
            ascending = st.checkbox("Ascending", value=True)

        ordered_ids = list(node_ids)
        if sort_col and sort_col != "(table order)":
            try:
                # Stable sort for determinism.
                df2 = df[["dsg_node_id", sort_col]].copy()
                # Coerce to numeric, NaNs pushed to end.
                df2[sort_col] = df2[sort_col].apply(lambda x: float(x) if x is not None and str(x).strip() != "" else float("nan"))
                df2 = df2.sort_values(by=[sort_col, "dsg_node_id"], ascending=[ascending, True], kind="mergesort")
                ordered_ids = [str(x) for x in df2["dsg_node_id"].tolist() if str(x).strip()]
            except Exception:
                ordered_ids = list(node_ids)

        c3, c4 = st.columns([1, 1])
        with c3:
            top_n = st.number_input(
                "Top N", min_value=1, max_value=len(ordered_ids), value=min(10, len(ordered_ids)), step=1
            )
        with c4:
            st.caption("Quick links")
            q1, q2, q3 = st.columns(3)
            if q1.button("Top 5"):
                top_n = 5
            if q2.button("Top 10"):
                top_n = 10
            if q3.button("Top 25"):
                top_n = 25

        selected_top = ordered_ids[: int(min(top_n, len(ordered_ids)))]
        st.write("Selected (Top-N):", len(selected_top))

        pasted = st.text_area(
            "Or paste dsg_node_id list (one per line or comma-separated)",
            value="",
            height=80,
            help="This avoids multiselect widgets and stays deterministic. IDs not in the table will be ignored.",
        )
        selected_paste = []
        if pasted.strip():
            raw = [x.strip() for x in pasted.replace("\n", ",").split(",") if x.strip()]
            allowed = set(ordered_ids)
            selected_paste = [x for x in raw if x in allowed]
        selected = selected_paste if selected_paste else selected_top

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
