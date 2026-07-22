"""PHYS-KPI-001 helpers for sensitivity / jacobian tables.

Local FD derivatives and base-output snapshots must not read as design
achievements when the baseline point is INFEASIBLE.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional

from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table, is_claim_kpi_key


def format_sens_value(
    output_key: str,
    value: Any,
    *,
    feasible: bool,
    digits: int = 4,
) -> str:
    """Format a sensitivity derivative (or numeric cell) with claim-KPI honesty."""
    k = str(output_key)
    if k in ("_base",):
        return "n/a"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value) if value is not None else "n/a"
    if not math.isfinite(v):
        return "n/a"
    if not feasible and is_claim_kpi_key(k):
        return f"diag·{v:.{digits}g}"
    return f"{v:.{digits}g}"


def format_sens_base_output(
    output_key: str,
    value: Any,
    *,
    feasible: bool,
    point_out: Optional[Mapping[str, Any]] = None,
    design_intent: Optional[str] = None,
    digits: int = 4,
) -> str:
    """Format pack ``base_outputs`` / FD ``_base`` snapshots (claim KPIs watermarked)."""
    return format_claim_kpi_for_table(
        output_key,
        value,
        feasible=feasible,
        point_out=point_out,
        design_intent=design_intent,
        digits=digits,
    )


def jacobian_table_rows(
    pack: Mapping[str, Any],
    knobs: List[str],
    outputs: List[str],
    *,
    feasible: bool,
) -> List[Dict[str, Any]]:
    """Control Room sensitivity-pack jacobian rows with PHYS-KPI watermarking."""
    rows: List[Dict[str, Any]] = []
    jac = pack.get("jacobian") if isinstance(pack.get("jacobian"), Mapping) else {}
    for o in outputs:
        for p in knobs:
            try:
                raw = (jac.get(o) or {}).get(p)
            except Exception:
                raw = None
            rows.append(
                {
                    "output": o,
                    "knob": p,
                    "jacobian": format_sens_value(o, raw, feasible=feasible),
                }
            )
    return rows


def base_output_table_rows(
    pack: Mapping[str, Any],
    outputs: List[str],
    *,
    feasible: bool,
    point_out: Optional[Mapping[str, Any]] = None,
    design_intent: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Rows for ``base_outputs`` snapshot from a sensitivity pack."""
    base = pack.get("base_outputs") if isinstance(pack.get("base_outputs"), Mapping) else {}
    rows: List[Dict[str, str]] = []
    for o in outputs:
        raw = base.get(o)
        rows.append(
            {
                "output": o,
                "value": format_sens_base_output(
                    o,
                    raw,
                    feasible=feasible,
                    point_out=point_out if point_out is not None else base,
                    design_intent=design_intent,
                ),
            }
        )
    return rows


def fd_sensitivity_table_rows(
    rep: Mapping[str, Any],
    *,
    feasible: bool,
    max_rows: int = 40,
) -> List[Dict[str, Any]]:
    """Systems / generic FD dict → table rows (skips ``_base`` as a fake output)."""
    rows: List[Dict[str, Any]] = []
    base_snap = rep.get("_base") if isinstance(rep.get("_base"), Mapping) else {}
    for outk, dd in rep.items():
        if outk == "_base" or not isinstance(dd, dict):
            continue
        for pk, dv in dd.items():
            rows.append(
                {
                    "output": str(outk),
                    "param": str(pk),
                    "sensitivity": format_sens_value(str(outk), dv, feasible=feasible),
                }
            )
            if len(rows) >= max_rows:
                break
        if len(rows) >= max_rows:
            break
    # Attach optional base snapshot rows at end if room (claim KPIs watermarked).
    if base_snap and len(rows) < max_rows:
        for o, v in base_snap.items():
            rows.append(
                {
                    "output": f"base:{o}",
                    "param": "(baseline)",
                    "sensitivity": format_sens_base_output(str(o), v, feasible=feasible, point_out=base_snap),
                }
            )
            if len(rows) >= max_rows:
                break
    return rows


def fd_parity_rows_watermark(
    rows: List[Dict[str, Any]],
    *,
    feasible: bool,
) -> List[Dict[str, Any]]:
    """Watermark PD ``local_fd_sensitivity_rows`` cells (dY/dX + elasticity)."""
    out: List[Dict[str, Any]] = []
    for r in rows:
        rr = dict(r)
        ok = str(rr.get("output", ""))
        if is_claim_kpi_key(ok) and not feasible:
            for col in ("dY/dX", "elasticity"):
                raw = rr.get(col)
                if raw in (None, "n/a"):
                    continue
                try:
                    v = float(str(raw).replace(",", ""))
                    if math.isfinite(v):
                        rr[col] = f"diag·{v:.4g}"
                    else:
                        rr[col] = "— (diagnostic)"
                except (TypeError, ValueError):
                    if str(raw) not in ("n/a", "— (diagnostic)") and not str(raw).startswith("diag"):
                        rr[col] = f"diag·{raw}"
        out.append(rr)
    return out
