from __future__ import annotations

"""Cross-panel handoff helpers (UI-layer only).

Panels may propose candidate PointInputs for the 🧭 Point Designer.
This module provides deterministic, audit-safe staging that also propagates
DSG node ids without requiring evaluator execution.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import fields
from typing import Any, Dict, Iterable, Optional

import streamlit as st  # type: ignore

try:
    from evaluator.cache_key import sha256_cache_key
except Exception:  # pragma: no cover
    # fallback import path
    from src.evaluator.cache_key import sha256_cache_key  # type: ignore

try:
    from src.models.inputs import PointInputs
except Exception:  # pragma: no cover
    from models.inputs import PointInputs  # type: ignore


_POINT_FIELDS = {f.name for f in fields(PointInputs)}


def filter_point_inputs_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Filter any dict down to supported PointInputs fields."""
    return {k: d[k] for k in d.keys() if k in _POINT_FIELDS}


def compute_dsg_node_id_from_candidate(cand: Dict[str, Any]) -> str:
    """Deterministic node id from canonical PointInputs dict."""
    return sha256_cache_key(filter_point_inputs_dict(dict(cand)))


def maybe_add_dsg_node_id_column(df):
    """If df looks like it contains PointInputs columns, add dsg_node_id."""
    try:
        import pandas as pd  # type: ignore
    except Exception:  # pragma: no cover
        return df
    if df is None or not hasattr(df, "columns"):
        return df
    if "dsg_node_id" in df.columns:
        return df
    cols = set(map(str, list(df.columns)))
    overlap = len(cols & _POINT_FIELDS)
    # Require some overlap to avoid polluting arbitrary tables
    if overlap < 3:
        return df
    def _nid(row) -> str:
        try:
            d = {k: row[k] for k in _POINT_FIELDS if k in row}
            return sha256_cache_key(d)
        except Exception:
            return ""
    try:
        df2 = df.copy()
        df2["dsg_node_id"] = df2.apply(lambda r: _nid(r), axis=1)
        return df2
    except Exception:
        return df


def stage_pd_candidate_apply(
    cand: Dict[str, Any],
    source: str,
    note: Optional[str] = None,
    dsg_node_id: Optional[str] = None,
) -> None:
    """Stage a candidate for 🧭 Point Designer and propagate DSG metadata."""
    if not isinstance(cand, dict) or not cand:
        return
    filtered = filter_point_inputs_dict(dict(cand))
    st.session_state["pd_candidate_apply"] = dict(filtered)

    try:
        nid = str(dsg_node_id) if dsg_node_id else compute_dsg_node_id_from_candidate(filtered)
        st.session_state["pd_candidate_dsg_node_id"] = nid
        src = str(source or "")
        parent = st.session_state.get("dsg_selected_node_id") or st.session_state.get("active_design_node_id")
        if "scan" in src.lower():
            st.session_state["scan_last_parent_node_id"] = str(parent) if parent else ""
            st.session_state["scan_last_node_ids"] = [nid]
        elif "pareto" in src.lower():
            st.session_state["pareto_last_parent_node_id"] = str(parent) if parent else ""
            st.session_state["pareto_last_node_ids"] = [nid]
        elif "trade" in src.lower():
            st.session_state["trade_last_parent_node_id"] = str(parent) if parent else ""
            st.session_state["trade_last_node_ids"] = [nid]
        elif "extopt" in src.lower() or "optimizer" in src.lower():
            st.session_state["extopt_last_parent_node_id"] = str(parent) if parent else ""
            st.session_state["extopt_last_node_ids"] = [nid]
    except Exception:
        pass

    from datetime import datetime
    st.session_state["last_promotion_event"] = {
        "source": str(source),
        "note": str(note) if note is not None else "",
        "ts": datetime.now().isoformat(timespec="seconds"),
    }


def render_subset_linker_best_effort(*, df: "object", label: str, kind: str, note: str = "") -> None:
    """Best-effort renderer for DSG subset linking.

    This function is UI-only. If Streamlit isn't available, or df lacks `dsg_node_id`, it is a no-op.
    """
    try:
        from ui.dsg_subset_linker import render_subset_linker  # type: ignore
        render_subset_linker(df=df, label=label, kind=kind, note=note)
    except Exception:
        return
