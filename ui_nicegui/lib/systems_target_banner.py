"""Target vs achieved summary for Systems Mode solve."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ui_nicegui.lib.systems_state_helpers import resolve_systems_problem
from ui_nicegui.session import DesignSession


def _sf(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def systems_target_rows(session: DesignSession, out: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """Rows for target-vs-achieved table after systems target solve."""
    _, targets, _ = resolve_systems_problem(session)
    if not targets:
        return []
    out = out or {}
    if not isinstance(out, dict):
        out = {}
    tol = float(getattr(session, "systems_tol", 1e-3))
    rows: List[Dict[str, str]] = []
    key_map = {
        "Q_DT_eqv": "Q_DT_eqv",
        "H98": "H98",
        "P_e_net_MW": "P_e_net_MW",
        "Pfus_DT_adj_MW": "Pfus_DT_adj_MW",
    }
    for tgt_key, val in targets.items():
        out_key = key_map.get(tgt_key, tgt_key)
        ach = out.get(out_key, out.get(tgt_key))
        t = _sf(val)
        a = _sf(ach)
        sense = "min" if tgt_key in ("Q_DT_eqv", "H98", "P_e_net_MW", "Pfus_DT_adj_MW") else "eq"
        if t == t and a == a:
            if sense == "min":
                flag = "ok" if a + max(tol, 1e-3) * max(abs(t), 1e-9) >= t else "miss"
            else:
                rel = abs(a - t) / max(abs(t), 1e-9)
                flag = "ok" if rel <= max(tol, 1e-3) * 10 else "miss"
        else:
            flag = "n/a"
        label = {
            "Q_DT_eqv": "Q_DT_eqv",
            "H98": "H98(y,2)",
            "P_e_net_MW": "P_e_net [MW]",
            "Pfus_DT_adj_MW": "Pfus_DT_adj [MW]",
        }.get(tgt_key, tgt_key)
        rows.append({
            "quantity": label,
            "target": f"{t:.4g}" if t == t else "—",
            "achieved": f"{a:.4g}" if a == a else "n/a",
            "status": flag,
        })
    return rows
