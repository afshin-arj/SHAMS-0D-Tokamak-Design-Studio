"""UI helpers for plant KPI honesty watermark (Independence 1.2)."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

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
        "CoE_USD_MWh",
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


def watermark_claim_kpi_map(
    mapping: Mapping[str, Any],
    *,
    feasible: bool,
    point_out: Optional[Mapping[str, Any]] = None,
    design_intent: Optional[str] = None,
) -> Dict[str, Any]:
    """Copy a KPI/outputs map with claim keys watermarked (PHYS-KPI-001)."""
    out: Dict[str, Any] = {}
    src = mapping if isinstance(mapping, Mapping) else {}
    for k, v in src.items():
        if is_claim_kpi_key(str(k)):
            out[str(k)] = format_claim_kpi_for_table(
                str(k), v, feasible=feasible, point_out=point_out or src, design_intent=design_intent
            )
        else:
            out[str(k)] = v
    return out


def changed_kpis_table_rows(
    changed_kpis: Mapping[str, Any],
    *,
    feasible_base: bool,
    feasible_scenario: bool,
) -> List[Dict[str, Any]]:
    """Rows for embedded scenario_delta.changed_kpis with per-side watermarking."""
    rows: List[Dict[str, Any]] = []
    if not isinstance(changed_kpis, Mapping):
        return rows
    for k, pair in changed_kpis.items():
        if not isinstance(pair, Mapping):
            continue
        base_v = pair.get("base")
        scen_v = pair.get("scenario")
        if is_claim_kpi_key(str(k)):
            a = format_claim_kpi_for_table(str(k), base_v, feasible=feasible_base)
            b = format_claim_kpi_for_table(str(k), scen_v, feasible=feasible_scenario)
            delta: Any = "— (diagnostic)"
            if feasible_base and feasible_scenario:
                try:
                    delta = float(scen_v) - float(base_v)
                except (TypeError, ValueError):
                    delta = ""
        else:
            a, b = base_v, scen_v
            try:
                delta = float(scen_v) - float(base_v)
            except (TypeError, ValueError):
                delta = ""
        rows.append({"kpi": str(k), "baseline": a, "scenario": b, "delta": delta})
    return rows


def claim_key_for_objective_column(column: str) -> Optional[str]:
    """Map Trade Study / Opt FoM column names to PHYS-KPI claim keys.

    Returns None when the column is not a claim KPI (geometry FoMs etc.).
    Accepts ExtOpt Robust Pareto prefixes ``robust_`` / ``degrade_``.
    """
    col = str(column or "").strip()
    if not col:
        return None
    for prefix in ("robust_", "degrade_"):
        if col.startswith(prefix):
            return claim_key_for_objective_column(col[len(prefix) :])
    if is_claim_kpi_key(col):
        return col
    try:
        from optimization.objective_contract import legacy_metric_keys
    except ImportError:
        try:
            from src.optimization.objective_contract import legacy_metric_keys  # type: ignore
        except ImportError:
            legacy_metric_keys = None  # type: ignore
    if legacy_metric_keys is not None:
        keys = legacy_metric_keys(col)
        if keys:
            for k in keys:
                if is_claim_kpi_key(str(k)):
                    return str(k)
    # Fallback aliases if objective_contract is unavailable.
    fallback = {
        "max_Q": "Q_DT_eqv",
        "max_H98": "H98",
        "max_Pnet": "P_e_net_MW",
        "min_COE": "COE_proxy_USD_per_MWh",
        "max_Pfus": "Pfus_total_MW",
    }
    return fallback.get(col)


def is_claim_scatter_axis(axis_key: str) -> bool:
    """True when a plot axis would present a PHYS-KPI claim coordinate."""
    return claim_key_for_objective_column(axis_key) is not None


def allow_infeasible_scatter_point(*, x_key: str, y_key: str) -> bool:
    """Infeasible shadows may only plot on non-claim axes (geometry / margins).

    Claim-KPI axes (Q / H98 / Pfus / P_net / LCOE FoMs) must not paint
    INFEASIBLE residue as achievement space (PHYS-KPI-001).
    """
    return not (is_claim_scatter_axis(x_key) or is_claim_scatter_axis(y_key))


def scatter_physkpi_caption(x_key: str, y_key: str, *, show_infeasible: bool) -> Optional[str]:
    if not show_infeasible:
        return None
    if not (is_claim_scatter_axis(x_key) or is_claim_scatter_axis(y_key)):
        return None
    return (
        "PHYS-KPI-001: infeasible shadow omitted on claim-KPI axes "
        "(Q / H98 / Pfus / P_net / LCOE) — diagnostic residue is not achievement space."
    )


def watermark_regime_atlas_export(atlas: Mapping[str, Any]) -> Dict[str, Any]:
    """Copy Regime Atlas artifact for download with PHYS-KPI-001 claim hygiene.

    Hard-infeasible records are excluded at the gate; this still watermarks
    claim FoMs on any INFEASIBLE-class Pareto rows that slipped through, and
    stamps an explicit honesty note.
    """
    out: Dict[str, Any] = dict(atlas) if isinstance(atlas, Mapping) else {}
    sets: List[Dict[str, Any]] = []
    for row in out.get("pareto_sets") or []:
        if not isinstance(row, Mapping):
            continue
        rr = dict(row)
        metrics = dict(rr.get("metrics") or {}) if isinstance(rr.get("metrics"), Mapping) else {}
        rclass = str(rr.get("robustness_class") or "").upper()
        if rclass in ("INFEASIBLE", "FAIL"):
            for k, v in list(metrics.items()):
                claim = claim_key_for_objective_column(str(k))
                if claim:
                    metrics[k] = format_claim_kpi_for_table(claim, v, feasible=False)
        rr["metrics"] = metrics
        sets.append(rr)
    out["pareto_sets"] = sets
    out["phys_kpi_note"] = (
        "PHYS-KPI-001: hard-infeasible records are excluded from feasibility gates; "
        "claim FoMs (Q/H98/Pfus/P_net/CoE) on INFEASIBLE-class Pareto rows are "
        "— (diagnostic) — not design claims."
    )
    return out


def watermark_trade_study_table_rows(
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[str],
    *,
    feasible_key: str = "is_feasible",
) -> List[Dict[str, Any]]:
    """Copy study table rows with claim FoM cells watermarked on INFEASIBLE samples."""
    out_rows: List[Dict[str, Any]] = []
    claim_cols = {c: claim_key_for_objective_column(c) for c in columns}
    for r in rows:
        if not isinstance(r, Mapping):
            continue
        feas = bool(r.get(feasible_key))
        row: Dict[str, Any] = {}
        for k in columns:
            if k not in r:
                continue
            claim = claim_cols.get(k)
            if claim and not feas:
                row[k] = format_claim_kpi_for_table(
                    claim, r.get(k), feasible=False, point_out=r.get("outputs") if isinstance(r.get("outputs"), Mapping) else None
                )
            else:
                row[k] = r.get(k)
        out_rows.append(row)
    return out_rows


def _robust_pareto_row_feasible(row: Mapping[str, Any]) -> bool:
    """Nominal hard-feasibility for Robust Pareto ExtOpt rows (PHYS-KPI-001)."""
    if "nominal_feasible" in row:
        return bool(row.get("nominal_feasible"))
    return str(row.get("tier") or "").upper() != "FAIL"


def watermark_robust_pareto_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Watermark robust_*/degrade_* claim FoMs on FAIL / infeasible Robust Pareto rows."""
    out_rows: List[Dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, Mapping):
            continue
        rr = dict(r)
        feas = _robust_pareto_row_feasible(rr)
        if feas:
            out_rows.append(rr)
            continue
        for k, v in list(rr.items()):
            claim = claim_key_for_objective_column(str(k))
            if claim:
                rr[k] = format_claim_kpi_for_table(claim, v, feasible=False)
        out_rows.append(rr)
    return out_rows


def watermark_robust_pareto_export(artifact: Mapping[str, Any]) -> Dict[str, Any]:
    """Copy Robust Pareto artifact for download with FAIL claim KPIs watermarked."""
    out: Dict[str, Any] = dict(artifact) if isinstance(artifact, Mapping) else {}
    rows = list(out.get("rows") or [])
    out["rows"] = watermark_robust_pareto_rows(rows)
    by_i = {r.get("i"): r for r in rows if isinstance(r, Mapping)}
    pts_out: List[Dict[str, Any]] = []
    for p in out.get("points") or []:
        if not isinstance(p, Mapping):
            continue
        pp = dict(p)
        idx = pp.get("index")
        src_row = by_i.get(idx) if idx is not None else None
        feas = _robust_pareto_row_feasible(src_row) if isinstance(src_row, Mapping) else True
        nom = pp.get("nominal_outputs")
        if not feas and isinstance(nom, Mapping):
            pp["nominal_outputs"] = watermark_claim_kpi_map(nom, feasible=False)
        pts_out.append(pp)
    out["points"] = pts_out
    out["phys_kpi_note"] = (
        "PHYS-KPI-001: claim KPIs on FAIL / nominally infeasible Robust Pareto "
        "points are — (diagnostic) — not design claims."
    )
    return out


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
    "watermark_claim_kpi_map",
    "changed_kpis_table_rows",
    "claim_key_for_objective_column",
    "is_claim_scatter_axis",
    "allow_infeasible_scatter_point",
    "scatter_physkpi_caption",
    "watermark_trade_study_table_rows",
    "watermark_robust_pareto_rows",
    "watermark_robust_pareto_export",
    "watermark_regime_atlas_export",
    "honest_performance_caption",
]
