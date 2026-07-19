"""Baseline point-evaluation caption for PD-gated study decks."""
from __future__ import annotations

from typing import Any, Mapping, Optional


def baseline_kpi_caption(
    point_out: Optional[dict[str, Any]],
    *,
    prefix: str = "Point evaluation loaded",
    max_bits: int = 6,
    artifact: Optional[Mapping[str, Any]] = None,
    verdict: Optional[Mapping[str, Any]] = None,
    design_intent: str = "",
    fuel_mode: str = "DT",
) -> str:
    if not isinstance(point_out, dict):
        return prefix
    from ui_nicegui.lib.pd_hero_kpis import hero_kpi_cells
    from ui_nicegui.lib.verdict_core import verdict_summary

    vs = dict(verdict) if isinstance(verdict, Mapping) else verdict_summary(point_out)
    verdict_label = str(vs.get("verdict") or "-")
    bits: list[str] = [verdict_label]
    if bool(point_out.get("mirage_flag_v402")):
        bits.append("MIRAGE")

    # PHYS-KPI-001: never present Q / H98 / Pfus / P_net as claims on INFEASIBLE.
    cells = hero_kpi_cells(
        point_out,
        vs,
        design_intent=design_intent,
        fuel_mode=fuel_mode,
    )
    by_label = {c.label: c for c in cells}
    q_cell = by_label.get("Performance")
    h98_cell = by_label.get("H98(y,2)")
    pfus_cell = by_label.get("Pfus")
    pnet_cell = by_label.get("P_net,e")
    if q_cell is not None:
        bits.append(q_cell.display if q_cell.suppressed else q_cell.display.replace("Q=", "Q≈", 1))
    if h98_cell is not None:
        bits.append(f"H98={h98_cell.display}" if h98_cell.suppressed else f"H98≈{h98_cell.display}")
    if pfus_cell is not None:
        bits.append(f"Pfus={pfus_cell.display}" if pfus_cell.suppressed else f"Pfus≈{pfus_cell.display}")
    if pnet_cell is not None:
        bits.append(f"P_net={pnet_cell.display}")
    else:
        try:
            from ui_nicegui.lib.plant_kpi_honesty_ui import pe_net_display

            pnet_disp = pe_net_display(point_out, artifact=artifact, design_intent=design_intent or None)
            if pnet_disp and pnet_disp not in ("n/a", "-"):
                bits.append(f"P_net={pnet_disp}")
        except Exception:
            pass

    beta = point_out.get("betaN", point_out.get("beta_N"))
    fg = point_out.get("fG", point_out.get("greenwald_fraction"))
    q95 = point_out.get("q95")
    if beta is not None:
        bits.append(f"β_N≈{beta}")
    if fg is not None:
        bits.append(f"f_G≈{fg}")
    if q95 is not None:
        bits.append(f"q95≈{q95} (cyl. proxy)")
    return f"{prefix} ({', '.join(str(b) for b in bits[:max_bits])})"


def baseline_kpi_classes(
    point_out: Optional[dict[str, Any]],
    *,
    verdict: Optional[Mapping[str, Any]] = None,
) -> str:
    """CSS classes for baseline caption — warn on infeasible / mirage."""
    if not isinstance(point_out, dict):
        return "text-caption text-grey"
    if bool(point_out.get("mirage_flag_v402")):
        return "text-caption text-orange"
    from ui_nicegui.lib.verdict_core import verdict_summary

    vs = dict(verdict) if isinstance(verdict, Mapping) else verdict_summary(point_out)
    if not vs.get("feasible", True):
        return "text-caption text-orange"
    return "text-caption text-positive"
