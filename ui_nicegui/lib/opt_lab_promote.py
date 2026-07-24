"""Opt Lab / ExtOpt promote-to-PD helpers (propose-only seed; clear prior KPIs)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def promote_opt_lab_best_to_point_designer(session: Any) -> Tuple[int, str]:
    """Seed PD from Certified Search best, else Pareto front[0].

    Returns ``(n_fields, source_label)``. Clears prior PD KPIs when ``n > 0``.
    """
    art = getattr(session, "v340_cert_search_last", None)
    if isinstance(art, dict) and isinstance(art.get("best"), dict):
        from ui_nicegui.decks.control_room.certified_search import (
            promote_certified_search_x_to_point_designer,
        )

        n = promote_certified_search_x_to_point_designer(session, art["best"])
        if n:
            return n, "certified_search"

    pl = getattr(session, "pareto_last", None)
    if isinstance(pl, dict):
        front = pl.get("pareto") or []
        if front and isinstance(front[0], dict):
            from ui_nicegui.lib.pareto_interpret_helpers import promote_point_inputs

            promote_point_inputs(session, front[0], getattr(session, "pareto_bounds", None) or {})
            return max(1, len([k for k in front[0] if k in (session.inputs or {})])), "pareto_front"
    return 0, ""


def _candidate_inputs_from_extopt_run_dir(run_dir: Path) -> Tuple[Optional[Dict[str, Any]], str]:
    """Prefer CCFS VERIFIED inputs; screening PASS/FEASIBLE/OK is fallback seed only.

    Returns ``(inputs, source_label)`` where source_label is
    ``extopt_ccfs_verified`` or ``extopt_screening`` (never implied VERIFIED for screening).
    """
    screening_inp: Optional[Dict[str, Any]] = None
    any_inp: Optional[Dict[str, Any]] = None
    for name in (
        "ccfs_verified.json",
        "verified_candidates.json",
        "proposed_candidates.json",
        "candidates.json",
    ):
        p = run_dir / name
        if not p.is_file():
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        cands = None
        if isinstance(obj, dict):
            for key in ("verified", "candidates", "results", "records"):
                if isinstance(obj.get(key), list):
                    cands = obj[key]
                    break
        elif isinstance(obj, list):
            cands = obj
        if not cands:
            continue
        for c in cands:
            if not isinstance(c, dict):
                continue
            status = str(c.get("status") or c.get("verdict") or "").upper()
            feas = c.get("feasible_hard")
            if feas is False:
                continue
            inp = c.get("inputs")
            if not isinstance(inp, dict) or not inp:
                continue
            if any_inp is None:
                any_inp = dict(inp)
            if status == "VERIFIED":
                return dict(inp), "extopt_ccfs_verified"
            if status in ("PASS", "FEASIBLE", "OK") or feas is True or not status:
                if screening_inp is None:
                    screening_inp = dict(inp)
    if screening_inp is not None:
        return screening_inp, "extopt_screening"
    if any_inp is not None:
        return any_inp, "extopt_screening"
    return None, ""


def promote_extopt_first_feasible_to_point_designer(session: Any) -> Tuple[int, str]:
    """Seed PD from ExtOpt suite ``run_dir`` first VERIFIED (else screening) candidate."""
    last = getattr(session, "extopt_last_run", None)
    if not isinstance(last, dict):
        return 0, ""
    run_dir_s = last.get("run_dir")
    if not run_dir_s:
        return 0, ""
    run_dir = Path(str(run_dir_s))
    if not run_dir.is_dir():
        return 0, ""
    inp, source = _candidate_inputs_from_extopt_run_dir(run_dir)
    if not inp:
        return 0, ""
    n = 0
    for k, v in inp.items():
        if k not in session.inputs:
            continue
        try:
            session.inputs[k] = float(v) if isinstance(v, (int, float)) else v
            n += 1
        except (TypeError, ValueError):
            session.inputs[k] = v
            n += 1
    if n:
        from ui_nicegui.lib.pd_handoff import invalidate_point_designer_after_seed

        invalidate_point_designer_after_seed(session)
    return n, (source if n else "")
