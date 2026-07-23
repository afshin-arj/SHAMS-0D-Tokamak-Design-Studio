"""Target vs achieved summary for Systems Mode solve."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table, is_claim_kpi_key
from ui_nicegui.lib.systems_state_helpers import resolve_systems_problem
from ui_nicegui.session import DesignSession


def _sf(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def systems_target_rows(
    session: DesignSession,
    out: Optional[Dict[str, Any]] = None,
    *,
    feasible: Optional[bool] = None,
) -> List[Dict[str, str]]:
    """Rows for target-vs-achieved table after systems target solve.

    When ``feasible`` is False (intent-infeasible), target attainment is labeled
    ``diag`` — never ``ok`` — so experts do not read INFEASIBLE solves as PASS (PHYS-KPI-001).
    Claim KPI magnitudes are watermarked as ``— (diagnostic)`` on infeasible solves.
    """
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
    aliases = {
        "P_e_net_MW": ("P_net_e_MW", "Pe_net_MW", "P_net_MW"),
        "Pfus_DT_adj_MW": ("Pfus_total_MW", "P_fus_MW", "Pfus_MW"),
        "Q_DT_eqv": ("Q", "Q_DT"),
        "H98": ("H_IPB98y2", "H98y2"),
    }
    for tgt_key, val in targets.items():
        out_key = key_map.get(tgt_key, tgt_key)
        ach = out.get(out_key, out.get(tgt_key))
        if ach is None:
            for alt in aliases.get(tgt_key, ()):
                if out.get(alt) is not None:
                    ach = out.get(alt)
                    break
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
        # PHYS-KPI-001: never present target floors as "ok" on an intent-infeasible point.
        if feasible is False and flag == "ok":
            flag = "diag"
        label = {
            "Q_DT_eqv": "Q_DT_eqv",
            "H98": "H98(y,2)",
            "P_e_net_MW": "P_e_net [MW]",
            "Pfus_DT_adj_MW": "Pfus_DT_adj [MW]",
        }.get(tgt_key, tgt_key)
        if sense == "min" and t == t:
            target_disp = f"≥{t:.4g}"
        elif t == t:
            target_disp = f"{t:.4g}"
        else:
            target_disp = "—"
        claim_key = "Pfus_total_MW" if tgt_key == "Pfus_DT_adj_MW" else tgt_key
        if feasible is False and is_claim_kpi_key(claim_key):
            achieved_disp = format_claim_kpi_for_table(claim_key, a, feasible=False)
        else:
            achieved_disp = f"{a:.4g}" if a == a else "n/a"
        rows.append({
            "quantity": label,
            "target": target_disp,
            "achieved": achieved_disp,
            "status": flag,
        })
    return rows
