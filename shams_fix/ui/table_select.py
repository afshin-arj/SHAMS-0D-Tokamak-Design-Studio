# © 2026 Afshin Arjhangmehr
"""UI table selection helpers (Streamlit).

Goal: provide a single wrapper for row selection that is:
- Streamlit-only (UI layer)
- deterministic in how selections are interpreted (stable order)
- compatible with Streamlit versions that may or may not support dataframe row selection.

This module must not be imported from truth / evaluator paths.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def dataframe_selected_row_indices(*, df: Any, key: str, dataframe_kwargs: Optional[Dict[str, Any]] = None) -> Optional[List[int]]:
    """Render a dataframe and return selected row indices if Streamlit supports selection.

    Returns
    -------
    None
        If selection is not supported by the installed Streamlit.
    []
        If selection is supported but nothing is selected.
    [i, j, ...]
        Row indices selected by the user.

    Notes
    -----
    - This function always renders a table (either selectable or plain).
    - Determinism: selection order is normalized to increasing row index.
    """
    try:
        import streamlit as st  # type: ignore
    except Exception:
        return None

    kwargs = dict(dataframe_kwargs or {})
    # Try modern Streamlit selection API: st.dataframe(on_select=..., selection_mode=...)
    try:
        import inspect

        sig = inspect.signature(st.dataframe)
        if "on_select" in sig.parameters and "selection_mode" in sig.parameters:
            event = st.dataframe(df, key=key, on_select="rerun", selection_mode="multi-row", **kwargs)
            # Streamlit selection event shape can vary; be defensive.
            try:
                rows = event.selection.rows  # type: ignore[attr-defined]
            except Exception:
                rows = []
            rows = sorted(int(i) for i in (rows or []))
            return rows
    except Exception:
        pass

    # Fallback: non-selectable table
    st.dataframe(df, key=key, **kwargs)
    return None


def render_dataframe_with_selection(
    *,
    df: Any,
    key: str,
    id_column: str = "dsg_node_id",
    store_key: Optional[str] = None,
    dataframe_kwargs: Optional[Dict[str, Any]] = None,
) -> Optional[List[str]]:
    """Render a dataframe and (if supported) capture selected ids from an `id_column`.

    Parameters
    ----------
    df:
        DataFrame-like object with row access via `.iloc[i]` and column access.
    key:
        Streamlit widget key.
    id_column:
        Column containing stable ids (default: `dsg_node_id`).
    store_key:
        If provided and Streamlit is available, store selected ids to `st.session_state[store_key]`.
    dataframe_kwargs:
        Passed through to Streamlit's dataframe renderer.

    Returns
    -------
    None if selection unsupported; otherwise list of selected id strings (possibly empty).
    """
    idxs = dataframe_selected_row_indices(df=df, key=key, dataframe_kwargs=dataframe_kwargs)
    if idxs is None:
        return None

    ids: List[str] = []
    try:
        for i in idxs:
            row = df.iloc[int(i)]
            val = row.get(id_column) if hasattr(row, "get") else row[id_column]
            if val is None:
                continue
            s = str(val).strip()
            if s:
                ids.append(s)
    except Exception:
        ids = []

    if store_key is not None:
        try:
            import streamlit as st  # type: ignore

            st.session_state[store_key] = ids
        except Exception:
            pass

    return ids
