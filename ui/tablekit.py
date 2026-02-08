"""
SHAMS UI TableKit
-----------------
Global, law-compliant UI affordance: render all tables as collapsible/expandable blocks
to avoid scroll walls and reduce visual noise.

Author: © 2026 Afshin Arjhangmehr
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Mapping, Sequence, Tuple
import math

@dataclass(frozen=True)
class TableKitConfig:
    enabled: bool = True
    default_expanded: bool = False
    max_title_len: int = 80

def _shape_of(data: Any) -> Optional[Tuple[int, int]]:
    try:
        import pandas as pd  # type: ignore
        if isinstance(data, pd.DataFrame):
            return (int(data.shape[0]), int(data.shape[1]))
        if isinstance(data, pd.Series):
            return (int(data.shape[0]), 1)
    except Exception:
        pass
    # list of dicts
    if isinstance(data, Sequence) and (not isinstance(data, (str, bytes))):
        try:
            n = len(data)  # type: ignore
        except Exception:
            n = None
        if n is not None and n > 0 and isinstance(data[0], Mapping):  # type: ignore[index]
            # columns is union of keys (approx)
            try:
                keys = set()
                for r in data[:50]:  # type: ignore[index]
                    if isinstance(r, Mapping):
                        keys.update(r.keys())
                return (n, len(keys))
            except Exception:
                return (n, None)  # type: ignore[return-value]
        if n is not None:
            return (n, None)  # type: ignore[return-value]
    return None

def _safe_title(title: str, max_len: int) -> str:
    t = (title or "").strip()
    if not t:
        return "Table"
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"

def install_expandable_tables(st: Any, *, enabled: bool = True, default_expanded: bool = False) -> None:
    """
    Monkeypatch Streamlit's st.dataframe and st.table to render inside an expander.

    This is UI-only and does not touch physics truth. It is deterministic and reversible.
    """
    if getattr(st, "_shams_tablekit_installed", False):
        return

    orig_df: Callable[..., Any] = st.dataframe
    orig_table: Callable[..., Any] = st.table

    def _cfg() -> TableKitConfig:
        try:
            ss = getattr(st, "session_state", None)
            if ss is not None:
                return TableKitConfig(
                    enabled=bool(ss.get("ui_tablekit_enabled", enabled)),
                    default_expanded=bool(ss.get("ui_tablekit_default_expanded", default_expanded)),
                )
        except Exception:
            pass
        return TableKitConfig(enabled=enabled, default_expanded=default_expanded)

    def dataframe(data: Any = None, *args: Any, **kwargs: Any) -> Any:
        cfg = _cfg()
        if not cfg.enabled:
            return orig_df(data, *args, **kwargs)

        title = kwargs.pop("table_title", None) or kwargs.pop("title", None) or "Table"
        expanded = kwargs.pop("table_expanded", None)
        if expanded is None:
            expanded = cfg.default_expanded

        shp = _shape_of(data)
        suffix = ""
        if shp is not None and shp[0] is not None:
            if shp[1] is not None:
                suffix = f"  ({shp[0]}×{shp[1]})"
            else:
                suffix = f"  ({shp[0]} rows)"
        label = _safe_title(str(title), cfg.max_title_len) + suffix

        with st.expander(label, expanded=bool(expanded)):
            return orig_df(data, *args, **kwargs)

    def table(data: Any = None, *args: Any, **kwargs: Any) -> Any:
        cfg = _cfg()
        if not cfg.enabled:
            return orig_table(data, *args, **kwargs)

        title = kwargs.pop("table_title", None) or kwargs.pop("title", None) or "Table"
        expanded = kwargs.pop("table_expanded", None)
        if expanded is None:
            expanded = cfg.default_expanded

        shp = _shape_of(data)
        suffix = ""
        if shp is not None and shp[0] is not None:
            if shp[1] is not None:
                suffix = f"  ({shp[0]}×{shp[1]})"
            else:
                suffix = f"  ({shp[0]} rows)"
        label = _safe_title(str(title), cfg.max_title_len) + suffix

        with st.expander(label, expanded=bool(expanded)):
            return orig_table(data, *args, **kwargs)

    st.dataframe = dataframe  # type: ignore[assignment]
    st.table = table  # type: ignore[assignment]
    st._shams_tablekit_installed = True
