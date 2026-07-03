"""Trade Study Studio deck -- extracted from ui/app.py (UI redesign).

Pure move + cosmetic de-emoji (UI redesign). No physics, constraint,
solver, evaluator, session-state key, or routing-ID changes. The block runs
with app.py module globals injected (namespace bridge, including app.py's
__file__ so path computations resolve as before); this bridge is temporary
tech debt to be replaced with explicit imports/ctx in a later cleanup commit.
"""
from __future__ import annotations
import streamlit as st
import sys


def render_trade_study_studio(_app_module) -> None:
    # Namespace bridge: borrow app.py module globals so this extracted block
    # resolves every bare name exactly as it did inline. __file__ is injected
    # so Path(__file__).resolve().parent.parent / .parents[1] still resolve to
    # the SHAMS-0D root (app.py's location), not ui/decks/. Pure move.
    _g = globals()
    for _k, _v in vars(_app_module).items():
        if not _k.startswith('__'):
            _g[_k] = _v
    _g['__file__'] = _app_module.__file__

    # DSG: auto edge-kind tagging by active panel (exploration only)
    if bool(st.session_state.get("dsg_edge_kind_auto", True)):
        st.session_state["dsg_context_edge_kind"] = "trade"

    try:
        from ui.trade_study_studio import render_trade_study_studio
        render_trade_study_studio(st, repo_root=Path(__file__).resolve().parent.parent)
    except Exception as e:
        st.error(f"Trade Study Studio failed to load: {e}")
