"""Streamlit alert helpers (avoid invalid/empty emoji icons)."""
from __future__ import annotations
import streamlit as st
from typing import Optional, Callable

def _clean_icon(icon: Optional[str]) -> Optional[str]:
    if icon is None:
        return None
    if not isinstance(icon, str):
        return None
    icon = icon.strip()
    if not icon:
        return None
    # Streamlit requires a single emoji char (no shortcodes). We do not validate fully here;
    # we only prevent empty/whitespace.
    return icon

def info(msg: str, *, icon: Optional[str] = None):
    ic = _clean_icon(icon)
    if ic is None:
        st.info(msg)
    else:
        st.info(msg, icon=ic)

def warning(msg: str, *, icon: Optional[str] = None):
    ic = _clean_icon(icon)
    if ic is None:
        st.warning(msg)
    else:
        st.warning(msg, icon=ic)

def error(msg: str, *, icon: Optional[str] = None):
    ic = _clean_icon(icon)
    if ic is None:
        st.error(msg)
    else:
        st.error(msg, icon=ic)

def success(msg: str, *, icon: Optional[str] = None):
    ic = _clean_icon(icon)
    if ic is None:
        st.success(msg)
    else:
        st.success(msg, icon=ic)
