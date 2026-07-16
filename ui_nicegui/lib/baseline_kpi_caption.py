"""Baseline point-evaluation caption for PD-gated study decks."""
from __future__ import annotations

from typing import Any, Optional


def baseline_kpi_caption(
    point_out: Optional[dict[str, Any]],
    *,
    prefix: str = "Point evaluation loaded",
    max_bits: int = 6,
) -> str:
    if not isinstance(point_out, dict):
        return prefix
    from ui_nicegui.lib.verdict_core import verdict_summary

    vs = verdict_summary(point_out)
    verdict = str(vs.get("verdict") or "-")
    bits: list[str] = [verdict]
    if bool(point_out.get("mirage_flag_v402")):
        bits.append("MIRAGE")
    q = point_out.get("Q_DT_eqv", point_out.get("Q"))
    h98 = point_out.get("H98")
    pfus = point_out.get("Pfus_total_MW", point_out.get("Pfus_MW", point_out.get("P_fus_MW")))
    pnet = point_out.get("P_e_net_MW")
    beta = point_out.get("betaN", point_out.get("beta_N"))
    fg = point_out.get("fG", point_out.get("greenwald_fraction"))
    q95 = point_out.get("q95")
    if q is not None:
        bits.append(f"Q≈{q}")
    if h98 is not None:
        bits.append(f"H98≈{h98}")
    if pfus is not None:
        bits.append(f"Pfus≈{pfus} MW")
    if pnet is not None:
        bits.append(f"P_net≈{pnet} MW")
    if beta is not None:
        bits.append(f"β_N≈{beta}")
    if fg is not None:
        bits.append(f"f_G≈{fg}")
    if q95 is not None:
        bits.append(f"q95≈{q95}")
    return f"{prefix} ({', '.join(str(b) for b in bits[:max_bits])})"


def baseline_kpi_classes(point_out: Optional[dict[str, Any]]) -> str:
    """CSS classes for baseline caption — warn on infeasible / mirage."""
    if not isinstance(point_out, dict):
        return "text-caption text-grey"
    if bool(point_out.get("mirage_flag_v402")):
        return "text-caption text-orange"
    from ui_nicegui.lib.verdict_core import verdict_summary

    if not verdict_summary(point_out).get("feasible", True):
        return "text-caption text-orange"
    return "text-caption text-positive"
