"""Canonical session-state API for cross-deck handoffs (UI Phase C)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

_POINT_KEYS = (
    "pd_last_outputs",
    "pd_last_artifact",
    "pd_last_inputs_hash",
    "pd_last_run_ts",
    "last_point_out",
    "last_point_inp",
    "last_point_artifact",
)

_NAV_KEYS = ("nav_deck_index", "nav_deck_label")


def get_point_outputs(session_state: Any) -> Optional[Dict[str, Any]]:
    out = session_state.get("pd_last_outputs")
    return dict(out) if isinstance(out, dict) else None


def get_point_artifact(session_state: Any) -> Optional[Dict[str, Any]]:
    art = session_state.get("pd_last_artifact") or session_state.get("last_point_artifact")
    return dict(art) if isinstance(art, dict) else None


def set_point_evaluation(
    session_state: Any,
    *,
    outputs: Dict[str, Any],
    inputs: Optional[Dict[str, Any]] = None,
    constraints: Optional[List[Any]] = None,
    run_ts: Optional[float] = None,
) -> None:
    session_state["pd_last_outputs"] = dict(outputs)
    session_state["last_point_out"] = dict(outputs)
    if inputs is not None:
        session_state["last_point_inp"] = dict(inputs)
    artifact = {
        "inputs": dict(inputs or session_state.get("last_point_inp") or {}),
        "outputs": dict(outputs),
        "constraints": list(constraints or []),
    }
    session_state["pd_last_artifact"] = artifact
    session_state["last_point_artifact"] = artifact
    if run_ts is not None:
        session_state["pd_last_run_ts"] = float(run_ts)


def set_nav_deck(session_state: Any, deck_label: str, deck_labels: List[str]) -> None:
    if deck_label in deck_labels:
        session_state["nav_deck_label"] = deck_label
        session_state["nav_deck_index"] = deck_labels.index(deck_label)


def snapshot_keys(session_state: Any) -> Dict[str, Any]:
    snap: Dict[str, Any] = {}
    for k in _POINT_KEYS + _NAV_KEYS:
        if k in session_state:
            snap[k] = session_state[k]
    return snap
