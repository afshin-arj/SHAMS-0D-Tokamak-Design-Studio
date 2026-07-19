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


# Keys that must not read as design claims on infeasible study points.
_CLAIM_KPI_KEYS = frozenset(
    {
        "Q",
        "Q_DT_eqv",
        "P_e_net_MW",
        "P_net_e_MW",
        "Pe_net_MW",
        "LCOE_proxy_USD_per_MWh",
        "LCOE_USD_per_MWh",
        "COE_proxy_USD_per_MWh",
        "avail_v420_LCOE_USD_per_MWh",
        "costing_v421_LCOE_USD_per_MWh",
        "H98",
        "Pfus_total_MW",
        "Pfus_MW",
        "P_fus_MW",
        "Pfus_DT_adj_MW",
    }
)
_DIAGNOSTIC = "— (diagnostic)"


def is_claim_kpi_key(key: str) -> bool:
    return str(key) in _CLAIM_KPI_KEYS


def format_claim_kpi_for_table(
    key: str,
    value: Any,
    *,
    feasible: bool,
    point_out: Optional[Mapping[str, Any]] = None,
    design_intent: Optional[str] = None,
    digits: int = 4,
) -> str:
    """Watermark / suppress pe_net · LCOE · Q (and kin) on infeasible study rows.

    Feasible rows keep a compact numeric display. Infeasible rows never present
    these as achievement claims (PHYS-KPI-001 / plant_kpi_honesty.v1).
    """
    k = str(key)
    if not is_claim_kpi_key(k):
        try:
            return f"{float(value):.{digits}g}"
        except (TypeError, ValueError):
            return str(value) if value is not None else "n/a"

    if not feasible:
        return _DIAGNOSTIC

    # Feasible: prefer plant honesty formatting for economics / Pe_net when outputs exist.
    if k in (
        "P_e_net_MW",
        "P_net_e_MW",
        "Pe_net_MW",
    ) and isinstance(point_out, Mapping):
        return pe_net_display(point_out, design_intent=design_intent)
    if k in (
        "LCOE_proxy_USD_per_MWh",
        "LCOE_USD_per_MWh",
        "COE_proxy_USD_per_MWh",
        "avail_v420_LCOE_USD_per_MWh",
        "costing_v421_LCOE_USD_per_MWh",
    ) and isinstance(point_out, Mapping):
        if k.startswith("COE"):
            return coe_display(point_out, design_intent=design_intent)
        return lcoe_display(point_out, design_intent=design_intent)

    try:
        v = float(value)
        if v != v:  # NaN
            return "n/a"
        return f"{v:.{digits}g}"
    except (TypeError, ValueError):
        return str(value) if value is not None else "n/a"


def honest_performance_caption(
    performance: Mapping[str, Any],
    *,
    feasible: bool,
    point_out: Optional[Mapping[str, Any]] = None,
    design_intent: Optional[str] = None,
    prefix: str = "Operating point: ",
) -> str:
    """Single-line caption for Scan/Forge probe strips."""
    if not performance:
        return ""
    bits = [
        f"{k}={format_claim_kpi_for_table(k, v, feasible=feasible, point_out=point_out, design_intent=design_intent)}"
        for k, v in performance.items()
    ]
    return prefix + ", ".join(bits)


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
    "is_claim_kpi_key",
    "format_claim_kpi_for_table",
    "honest_performance_caption",
]
