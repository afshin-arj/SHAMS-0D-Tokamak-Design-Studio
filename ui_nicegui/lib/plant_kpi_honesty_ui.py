"""UI helpers for plant KPI honesty watermark (Independence 1.2)."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

try:
    from diagnostics.plant_kpi_honesty import (
        SCHEMA,
        build_plant_kpi_honesty,
        format_plant_kpi,
        plant_kpi_banner_text,
    )
except ImportError:
    from src.diagnostics.plant_kpi_honesty import (  # type: ignore
        SCHEMA,
        build_plant_kpi_honesty,
        format_plant_kpi,
        plant_kpi_banner_text,
    )


def plant_kpi_honesty_for_point(
    point_out: Optional[Mapping[str, Any]] = None,
    *,
    artifact: Optional[Mapping[str, Any]] = None,
    design_intent: Optional[str] = None,
) -> Dict[str, Any]:
    """Prefer stamped artifact block; otherwise build from point outputs."""
    if isinstance(artifact, Mapping):
        stamped = artifact.get("plant_kpi_honesty")
        if isinstance(stamped, Mapping) and stamped.get("schema") == SCHEMA:
            return dict(stamped)
        kpis = artifact.get("kpis") if isinstance(artifact.get("kpis"), Mapping) else {}
        cons = artifact.get("constraints") if isinstance(artifact.get("constraints"), list) else None
        hf = kpis.get("feasible_hard") if isinstance(kpis, Mapping) and "feasible_hard" in kpis else None
        out = point_out
        if out is None and isinstance(artifact.get("outputs"), Mapping):
            out = artifact.get("outputs")
        return build_plant_kpi_honesty(
            out if isinstance(out, Mapping) else {},
            hard_feasible=bool(hf) if hf is not None else None,
            constraints_json=cons if isinstance(cons, Sequence) else None,
            design_intent=design_intent,
        )
    return build_plant_kpi_honesty(
        point_out if isinstance(point_out, Mapping) else {},
        design_intent=design_intent,
    )


def pe_net_display(
    point_out: Optional[Mapping[str, Any]] = None,
    *,
    artifact: Optional[Mapping[str, Any]] = None,
    design_intent: Optional[str] = None,
) -> str:
    honesty = plant_kpi_honesty_for_point(point_out, artifact=artifact, design_intent=design_intent)
    raw = None
    if isinstance(point_out, Mapping):
        raw = point_out.get("P_e_net_MW", point_out.get("P_net_e_MW", point_out.get("Pe_net_MW")))
    return format_plant_kpi(honesty, "Pe_net_MW", fallback_raw=raw, units="MW")


def coe_display(
    point_out: Optional[Mapping[str, Any]] = None,
    *,
    artifact: Optional[Mapping[str, Any]] = None,
    design_intent: Optional[str] = None,
) -> str:
    honesty = plant_kpi_honesty_for_point(point_out, artifact=artifact, design_intent=design_intent)
    raw = point_out.get("COE_proxy_USD_per_MWh") if isinstance(point_out, Mapping) else None
    return format_plant_kpi(honesty, "COE_proxy_USD_per_MWh", fallback_raw=raw, units="USD/MWh")


def lcoe_display(
    point_out: Optional[Mapping[str, Any]] = None,
    *,
    artifact: Optional[Mapping[str, Any]] = None,
    design_intent: Optional[str] = None,
) -> str:
    honesty = plant_kpi_honesty_for_point(point_out, artifact=artifact, design_intent=design_intent)
    raw = None
    if isinstance(point_out, Mapping):
        raw = point_out.get(
            "LCOE_proxy_USD_per_MWh",
            point_out.get("LCOE_proxy_v360_USD_per_MWh", point_out.get("LCOE_proxy_v359_USD_per_MWh")),
        )
    return format_plant_kpi(honesty, "LCOE_proxy_USD_per_MWh", fallback_raw=raw, units="USD/MWh")


def bottom_up_lcoe_display(
    point_out: Optional[Mapping[str, Any]] = None,
    *,
    artifact: Optional[Mapping[str, Any]] = None,
    design_intent: Optional[str] = None,
) -> str:
    """Watermarked display of the bottom-up costing LCOE restatement.

    Uses the same hard-feasibility watermark as the global LCOE claim but
    formats the bottom-up key specifically, so the bottom-up costing panel
    never pairs its CAPEX with an LCOE computed on a different CAPEX basis.
    """
    honesty = plant_kpi_honesty_for_point(point_out, artifact=artifact, design_intent=design_intent)
    raw = (
        point_out.get("costing_v421_LCOE_USD_per_MWh")
        if isinstance(point_out, Mapping)
        else None
    )
    # The canon key is intentionally absent from the honesty kpis map, so
    # format_plant_kpi falls back to claim_allowed + this specific raw value.
    return format_plant_kpi(
        honesty, "costing_v421_LCOE_USD_per_MWh", fallback_raw=raw, units="USD/MWh"
    )


def render_plant_kpi_watermark_banner(
    point_out: Optional[Mapping[str, Any]] = None,
    *,
    artifact: Optional[Mapping[str, Any]] = None,
    design_intent: Optional[str] = None,
) -> Optional[str]:
    """Return banner text if watermark needed; None when claim-allowed."""
    honesty = plant_kpi_honesty_for_point(point_out, artifact=artifact, design_intent=design_intent)
    text = plant_kpi_banner_text(honesty)
    return text or None


__all__ = [
    "SCHEMA",
    "build_plant_kpi_honesty",
    "plant_kpi_honesty_for_point",
    "pe_net_display",
    "coe_display",
    "lcoe_display",
    "bottom_up_lcoe_display",
    "render_plant_kpi_watermark_banner",
    "format_plant_kpi",
    "plant_kpi_banner_text",
]
