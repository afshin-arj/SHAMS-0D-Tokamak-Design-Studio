"""Plant KPI honesty watermark (PROCESS Independence ticket 1.2).

Gate healthy Pe_net / COE (and related plant economics) display on hard
feasibility so infeasible bookkeeping residues never look like certified
plant claims.

Post-processing only — does NOT modify L0 evaluator / hot_ion outputs.
Raw numeric values remain available under each cell's ``raw`` field.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

SCHEMA = "plant_kpi_honesty.v1"

# Canonical plant claim keys → candidate output keys (first finite wins).
_PLANT_KPI_ALIASES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Pe_net_MW", ("P_e_net_MW", "P_net_e_MW", "Pe_net_MW")),
    (
        "COE_proxy_USD_per_MWh",
        ("COE_proxy_USD_per_MWh",),
    ),
    (
        "LCOE_proxy_USD_per_MWh",
        (
            "LCOE_proxy_USD_per_MWh",
            "avail_v420_LCOE_USD_per_MWh",
            "costing_v421_LCOE_USD_per_MWh",
            "LCOE_proxy_v360_USD_per_MWh",
            "LCOE_proxy_v359_USD_per_MWh",
            "LCOE_lite_v383_USD_per_MWh",
            "LCOE_lite_v388_USD_per_MWh",
        ),
    ),
)

_DIAGNOSTIC_DISPLAY = "— (diagnostic)"
_NA_DISPLAY = "n/a"

_MSG_INFEASIBLE = (
    "Plant Pe_net / COE / LCOE are bookkeeping residues on a HARD-INFEASIBLE "
    "point — not certified net-electric or cost claims. See Constraints / "
    "NO-SOLUTION atlas for attribution."
)
_MSG_FEASIBLE = (
    "Hard constraints pass — plant Pe_net / COE may be shown as screening KPIs "
    "(still proxy economics; not a PROCESS-class cost authority)."
)
_MSG_UNKNOWN = (
    "Hard feasibility unknown — plant Pe_net / COE shown as diagnostic only."
)


def _sf(x: Any, default: float = float("nan")) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def _pick_raw(outputs: Mapping[str, Any], aliases: Sequence[str]) -> Tuple[float, str]:
    for key in aliases:
        if key in outputs:
            v = _sf(outputs.get(key))
            if math.isfinite(v):
                return v, key
    return float("nan"), (aliases[0] if aliases else "")


def hard_feasible_from_constraints_json(
    constraints_json: Optional[Sequence[Mapping[str, Any]]],
) -> Optional[bool]:
    """Return hard feasibility from constraint JSON, or None if undecidable."""
    if not constraints_json:
        return None
    saw_hard = False
    for c in constraints_json:
        if not isinstance(c, Mapping):
            continue
        if str(c.get("severity", "hard")).lower() != "hard":
            continue
        saw_hard = True
        if not bool(c.get("passed", True)):
            return False
    return True if saw_hard else None


def resolve_hard_feasible(
    *,
    hard_feasible: Optional[bool] = None,
    constraints_json: Optional[Sequence[Mapping[str, Any]]] = None,
    outputs: Optional[Mapping[str, Any]] = None,
    design_intent: Optional[str] = None,
) -> Tuple[Optional[bool], str]:
    """Resolve hard feasibility with explicit provenance.

    Returns (hard_feasible_or_None, source).
    """
    if hard_feasible is not None:
        return bool(hard_feasible), "explicit"
    from_json = hard_feasible_from_constraints_json(constraints_json)
    if from_json is not None:
        return from_json, "constraints_json"
    if isinstance(outputs, Mapping) and outputs:
        try:
            try:
                from constraints.unified import build_all_constraints, dominant_failing_constraint
            except ImportError:
                from src.constraints.unified import (  # type: ignore
                    build_all_constraints,
                    dominant_failing_constraint,
                )
            bundle = build_all_constraints(dict(outputs), design_intent=design_intent)
            dom = dominant_failing_constraint(bundle, use_governance=True)
            feasible = dom is None and bool(getattr(bundle, "governance_feasible", True))
            return bool(feasible), "constraint_bundle"
        except Exception:
            return None, "unknown"
    return None, "unknown"


def _fmt_display(raw: float, *, claim_allowed: bool, units: str = "") -> str:
    if not math.isfinite(raw):
        return _NA_DISPLAY
    if not claim_allowed:
        return _DIAGNOSTIC_DISPLAY
    if units == "MW":
        return f"{raw:.3g} MW"
    if units in ("$/MWh", "USD/MWh"):
        return f"{raw:.3g} USD/MWh"
    return f"{raw:.3g}"


def build_plant_kpi_honesty(
    outputs: Optional[Mapping[str, Any]] = None,
    *,
    hard_feasible: Optional[bool] = None,
    constraints_json: Optional[Sequence[Mapping[str, Any]]] = None,
    design_intent: Optional[str] = None,
) -> Dict[str, Any]:
    """Build plant_kpi_honesty.v1 watermark for Pe_net / COE / LCOE.

    When hard constraints fail (or feasibility is unknown), claim_allowed is
    False and display strings are diagnostic watermarks. Raw values are never
    deleted — consumers that need bookkeeping can still read ``raw``.
    """
    out = dict(outputs or {})
    hf, source = resolve_hard_feasible(
        hard_feasible=hard_feasible,
        constraints_json=constraints_json,
        outputs=out,
        design_intent=design_intent,
    )

    if hf is True:
        watermark = "HARD_FEASIBLE"
        claim_allowed = True
        message = _MSG_FEASIBLE
    elif hf is False:
        watermark = "HARD_INFEASIBLE"
        claim_allowed = False
        message = _MSG_INFEASIBLE
    else:
        watermark = "UNKNOWN"
        claim_allowed = False
        message = _MSG_UNKNOWN

    units_map = {
        "Pe_net_MW": "MW",
        "COE_proxy_USD_per_MWh": "USD/MWh",
        "LCOE_proxy_USD_per_MWh": "USD/MWh",
    }
    kpis: Dict[str, Any] = {}
    for canon, aliases in _PLANT_KPI_ALIASES:
        raw, src_key = _pick_raw(out, aliases)
        kpis[canon] = {
            "raw": float(raw) if math.isfinite(raw) else float("nan"),
            "source_key": src_key,
            "claim_allowed": bool(claim_allowed and math.isfinite(raw)),
            "display": _fmt_display(raw, claim_allowed=claim_allowed, units=units_map.get(canon, "")),
            "watermark": watermark if math.isfinite(raw) else "MISSING",
        }

    return {
        "schema": SCHEMA,
        "hard_feasible": hf,
        "feasibility_source": source,
        "watermark": watermark,
        "claim_allowed": bool(claim_allowed),
        "message": message,
        "kpis": kpis,
    }


def format_plant_kpi(
    honesty: Mapping[str, Any],
    canon_key: str,
    *,
    fallback_raw: Any = None,
    units: str = "",
) -> str:
    """UI helper: return watermarked display string for a plant KPI."""
    kpis = honesty.get("kpis") if isinstance(honesty, Mapping) else None
    cell = kpis.get(canon_key) if isinstance(kpis, Mapping) else None
    if isinstance(cell, Mapping) and "display" in cell:
        return str(cell.get("display") or _NA_DISPLAY)
    # Fallback when honesty block missing
    claim = bool(honesty.get("claim_allowed", False)) if isinstance(honesty, Mapping) else False
    raw = _sf(fallback_raw)
    return _fmt_display(raw, claim_allowed=claim, units=units)


def plant_kpi_banner_text(honesty: Mapping[str, Any]) -> str:
    """Short banner for Suite / ledger surfaces."""
    if not isinstance(honesty, Mapping):
        return ""
    wm = str(honesty.get("watermark") or "")
    if wm == "HARD_INFEASIBLE":
        return "WATERMARK: HARD-INFEASIBLE — Pe_net / COE are diagnostic only"
    if wm == "UNKNOWN":
        return "WATERMARK: feasibility unknown — Pe_net / COE diagnostic only"
    return ""


def attach_plant_kpi_honesty_to_artifact(
    art: Dict[str, Any],
    *,
    outputs: Optional[Mapping[str, Any]] = None,
    constraints_json: Optional[Sequence[Mapping[str, Any]]] = None,
    design_intent: Optional[str] = None,
) -> Dict[str, Any]:
    """Stamp plant_kpi_honesty.v1 onto a run artifact (mutates and returns art)."""
    if not isinstance(art, dict):
        return art
    out = outputs if isinstance(outputs, Mapping) else art.get("outputs")
    cons = constraints_json
    if cons is None:
        raw_cons = art.get("constraints")
        cons = raw_cons if isinstance(raw_cons, list) else None
    kpis = art.get("kpis") if isinstance(art.get("kpis"), dict) else {}
    hf_explicit: Optional[bool] = None
    if "feasible_hard" in kpis:
        hf_explicit = bool(kpis.get("feasible_hard"))
    honesty = build_plant_kpi_honesty(
        out if isinstance(out, Mapping) else {},
        hard_feasible=hf_explicit,
        constraints_json=cons,
        design_intent=design_intent,
    )
    art["plant_kpi_honesty"] = honesty
    # Convenience mirrors for dashboards / exports (do not overwrite raw outputs).
    if isinstance(kpis, dict):
        kpis["plant_claim_allowed"] = bool(honesty.get("claim_allowed"))
        kpis["plant_kpi_watermark"] = str(honesty.get("watermark") or "")
        pe = (honesty.get("kpis") or {}).get("Pe_net_MW") or {}
        coe = (honesty.get("kpis") or {}).get("COE_proxy_USD_per_MWh") or {}
        lcoe = (honesty.get("kpis") or {}).get("LCOE_proxy_USD_per_MWh") or {}
        kpis["Pe_net_display"] = pe.get("display", _NA_DISPLAY)
        kpis["COE_display"] = coe.get("display", _NA_DISPLAY)
        kpis["LCOE_display"] = lcoe.get("display", _NA_DISPLAY)
        art["kpis"] = kpis
    return art
