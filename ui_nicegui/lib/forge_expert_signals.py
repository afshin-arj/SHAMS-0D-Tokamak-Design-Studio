"""Forge expert signal helpers (ported from Streamlit workbench)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def regime_signature(cand: dict) -> List[str]:
    tags: List[str] = []
    inp = cand.get("inputs") or {}
    out = cand.get("outputs") or {}

    def _num(d: dict, k: str) -> Optional[float]:
        try:
            v = d.get(k)
            return None if v is None else float(v)
        except (TypeError, ValueError):
            return None

    r0 = _num(inp, "R0_m") or _num(out, "R0_m")
    a = _num(inp, "a_m") or _num(out, "a_m")
    ip = _num(inp, "Ip_MA") or _num(out, "Ip_MA")
    b0 = _num(inp, "B0_T") or _num(out, "B0_T") or _num(out, "Bt_T")
    pf = _num(out, "Pfus_total_MW")

    if r0 is not None:
        if r0 < 2.5:
            tags.append("compact")
        elif r0 > 6.0:
            tags.append("large-R")
    if r0 is not None and a is not None and a > 0:
        aspect = r0 / a
        if aspect < 2.2:
            tags.append("spherical")
        elif aspect > 3.2:
            tags.append("high-aspect")
    if b0 is not None:
        if b0 >= 10.0:
            tags.append("high-field")
        elif b0 <= 4.0:
            tags.append("low-field")
    if ip is not None and ip >= 12.0:
        tags.append("high-current")
    if pf is not None and r0 is not None and r0 > 0:
        if pf / (r0 ** 3) >= 20.0:
            tags.append("power-dense")
    fs = cand.get("feasibility_state")
    if fs:
        tags.append(str(fs).replace("feasible_", ""))
    return tags[:8]


def first_kill(cand: dict) -> dict:
    mb = cand.get("margin_budget") or {}
    rows = mb.get("rows") or []
    if not rows:
        return {
            "name": cand.get("first_failure") or cand.get("failure_mode") or "-",
            "signed_margin": cand.get("min_signed_margin"),
        }
    best = None
    for r in rows:
        try:
            sm = float(r.get("signed_margin"))
        except (TypeError, ValueError):
            continue
        if best is None or sm < best[0]:
            best = (sm, r)
    if best is None:
        return {"name": cand.get("first_failure") or "-", "signed_margin": cand.get("min_signed_margin")}
    rr = best[1]
    return {"name": rr.get("name") or rr.get("constraint") or "-", "signed_margin": float(best[0])}


def constraint_spend_rate(cand: dict, archive: list, run: dict) -> dict:
    pid = cand.get("parent_id") or cand.get("parent")
    if not pid:
        return {"ok": False, "reason": "no parent link"}
    parent = None
    for c in archive or []:
        if (c.get("_id") or c.get("fingerprint")) == pid:
            parent = c
            break
    if parent is None:
        return {"ok": False, "reason": "parent not found in archive"}

    obj = None
    lens = run.get("lens") or run.get("lens_contract") or {}
    objs = lens.get("objectives") if isinstance(lens, dict) else None
    if isinstance(objs, list) and objs:
        obj = objs[0].get("key") if isinstance(objs[0], dict) else None
    if not obj:
        obj = "P_e_net_MW" if "P_e_net_MW" in (cand.get("outputs") or {}) else None
    if not obj:
        return {"ok": False, "reason": "no objective key"}

    def _val(c: dict, key: str):
        try:
            return float((c.get("outputs") or {}).get(key))
        except (TypeError, ValueError):
            return None

    c_obj = _val(cand, obj)
    p_obj = _val(parent, obj)
    if c_obj is None or p_obj is None:
        return {"ok": False, "reason": "insufficient objective values"}
    d_obj = c_obj - p_obj
    try:
        d_m = float(cand.get("min_signed_margin")) - float(parent.get("min_signed_margin"))
    except (TypeError, ValueError):
        return {"ok": False, "reason": "insufficient margin delta"}
    if abs(d_obj) < 1e-12:
        return {"ok": False, "reason": "insufficient delta"}
    return {
        "ok": True,
        "objective": obj,
        "delta_objective": d_obj,
        "delta_min_margin": d_m,
        "margin_spend_per_objective": d_m / d_obj,
        "note": "Local heuristic vs parent only (descriptive).",
    }


def scan_grounding(cand: dict, scan_artifact: Optional[dict], *, intent: str) -> dict:
    try:
        art = scan_artifact or {}
        rep = (art.get("report") or {}) if isinstance(art, dict) else {}
        pts = rep.get("points") or []
        xk = rep.get("x_key")
        yk = rep.get("y_key")
        if not pts or not xk or not yk:
            return {"ok": False, "reason": "scan artifact missing points/x_key/y_key"}
        cin = cand.get("inputs") or {}
        if xk not in cin or yk not in cin:
            return {"ok": False, "reason": "candidate lacks scan axes", "x_key": xk, "y_key": yk}
        cx = float(cin.get(xk))
        cy = float(cin.get(yk))
        best = None
        best_d = None
        for p in pts:
            try:
                dx = float(p.get("x")) - cx
                dy = float(p.get("y")) - cy
                d2 = dx * dx + dy * dy
            except (TypeError, ValueError):
                continue
            if best_d is None or d2 < best_d:
                best_d = d2
                best = p
        if best is None:
            return {"ok": False, "reason": "no nearest scan point"}
        return {
            "ok": True,
            "intent": intent,
            "x_key": xk,
            "y_key": yk,
            "nearest": best,
            "distance2": best_d,
        }
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}
