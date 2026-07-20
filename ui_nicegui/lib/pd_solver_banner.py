"""Solver target vs achieved summary for Point Designer Configure."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ui_nicegui.session import DesignSession


def _sf(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def solver_target_rows(session: DesignSession, out: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """Rows for a compact target-vs-achieved table after solver/envelope runs."""
    mode = str(session.pd_eval_mode)
    if mode == "direct":
        return []
    out = out or session.pd_last_outputs or session.last_eval or {}
    if not isinstance(out, dict) or not out:
        return []

    from ui_nicegui.lib.verdict_core import verdict_summary

    feasible = bool(verdict_summary(out).get("feasible"))

    rows: List[Dict[str, str]] = []
    pairs = [
        ("Q_DT_eqv", session.pd_q_target, out.get("Q_DT_eqv", out.get("Q"))),
        ("H98(y,2)", session.pd_h98_target, out.get("H98")),
    ]
    if mode == "envelope":
        pfus = float(session.pd_pfus_target)
        pnet = float(session.pd_pnet_target)
        if pfus > 0:
            pairs.append(("Pfus_DT_adj (MW)", pfus, out.get("Pfus_DT_adj_MW", out.get("Pfus_MW"))))
        if pnet > 0:
            pairs.append(("P_e_net (MW)", pnet, out.get("P_e_net_MW")))

    for name, tgt, ach in pairs:
        t = _sf(tgt)
        a = _sf(ach)
        if t == t and a == a:
            rel = abs(a - t) / max(abs(t), 1e-9)
            flag = "ok" if rel <= max(float(session.pd_solver_tol), 1e-3) * 10 else "miss"
        else:
            flag = "n/a"
        if not feasible and flag == "ok":
            flag = "diag"
        rows.append({
            "quantity": name,
            "target": f"{t:.4g}" if t == t else "—",
            "achieved": f"{a:.4g}" if a == a else "n/a",
            "status": flag,
        })
    return rows
