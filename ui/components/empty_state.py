"""empty_state -- consistent empty/unavailable placeholder (UI redesign component).

Pure presentation: renders a single info/warning/error/success callout with a
uniform tone for "no data yet" / "overlay unavailable" states. No physics,
no state mutation.

Usage:
    empty_state("Run **Point Designer** first to populate System Suite diagnostics.")
    empty_state("Power closure overlay unavailable.", kind="warning")
"""
from __future__ import annotations
import streamlit as st

_FNS = {
    "info": st.info,
    "warning": st.warning,
    "error": st.error,
    "success": st.success,
}


def empty_state(message: str, kind: str = "info") -> None:
    """Render a consistent empty-state placeholder callout.

    ``kind`` is one of ``"info"`` (default), ``"warning"``, ``"error"``,
    ``"success"``. Unknown kinds fall back to ``st.info``.
    """
    fn = _FNS.get(kind, st.info)
    fn(message)
