"""Read Point Designer artifacts from DesignSession (System Suite / Compare handoff)."""
from __future__ import annotations

from typing import Any, Optional, Tuple

from ui_nicegui.session import DesignSession


def get_point_artifact_triple(
    session: DesignSession,
) -> Tuple[Optional[dict[str, Any]], Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    """Return (artifact, inputs, outputs) from session."""
    art = session.pd_last_artifact
    if not isinstance(art, dict):
        art = None

    point_inp: Optional[dict[str, Any]] = None
    point_out: Optional[dict[str, Any]] = None
    if isinstance(art, dict):
        point_inp = art.get("inputs") if isinstance(art.get("inputs"), dict) else None
        point_out = art.get("outputs") if isinstance(art.get("outputs"), dict) else None

    if not isinstance(point_out, dict):
        out = session.pd_last_outputs or session.last_eval
        point_out = dict(out) if isinstance(out, dict) else None
    if not isinstance(point_inp, dict):
        point_inp = dict(session.inputs) if session.inputs else None

    return art, point_inp, point_out
