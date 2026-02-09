from __future__ import annotations

"""UI-only DSG actions.

Small deterministic helpers to attach lineage edges in the Design State Graph
(DSG). This is exploration-layer only; it must not alter frozen truth.

Author: © 2026 Afshin Arjhangmehr
"""

from typing import Iterable, Optional


def link_selected_to_parent(
    *,
    selected_node_ids: Iterable[str],
    kind: str,
    note: str,
    parent_node_id: Optional[str] = None,
    snapshot_path: str = "artifacts/dsg/current_dsg.json",
) -> int:
    """Attach DSG lineage edges from a parent node to a selected set.

    Returns number of edges added.

    This is UI/exploration-only.
    """

    try:
        import streamlit as st
    except Exception:
        return 0

    g = st.session_state.get("_shams_dsg")
    if g is None:
        return 0

    parent = parent_node_id or st.session_state.get("active_design_node_id") or getattr(g, "active_node_id", None)
    if not parent:
        return 0

    ids = [str(x).strip() for x in selected_node_ids if str(x).strip()]
    ids = [i for i in ids if i != parent]
    if not ids:
        return 0

    n = 0
    try:
        if hasattr(g, "add_edges"):
            n = int(g.add_edges(src=str(parent), dst_list=ids, kind=str(kind), note=str(note)) or 0)
        else:
            for dst in ids:
                try:
                    g.add_edge(src=str(parent), dst=str(dst), kind=str(kind), note=str(note))
                    n += 1
                except Exception:
                    continue
    except Exception:
        return 0

    try:
        st.session_state["active_design_node_id"] = str(parent)
        try:
            setattr(g, "active_node_id", str(parent))
        except Exception:
            pass
        try:
            g.save(snapshot_path)
        except Exception:
            pass
    except Exception:
        pass

    return n
