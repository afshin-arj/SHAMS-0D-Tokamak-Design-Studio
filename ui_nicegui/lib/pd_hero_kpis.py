"""Hero KPI display policy — suppress misleading diagnostics on infeasible points.

Raw evaluator outputs remain unchanged in artifacts/telemetry; this module only
governs verdict-first headline presentation (hero strip + mission snapshot lead).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    from certification.transport_confinement_certification_v376 import _envelope_for_intent
except ImportError:
    from src.certification.transport_confinement_certification_v376 import _envelope_for_intent

# Infeasible headline caps — diagnostic power-balance closure, not achievement claims.
_Q_MAX_INFEASIBLE_DT = 25.0
_Q_MAX_INFEASIBLE_DD = 0.08


@dataclass(frozen=True)
class HeroKpiCell:
    label: str
    display: str
    suppressed: bool = False
    raw_value: Optional[float] = None
    note: str = ""


def _sf(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _intent_bucket(design_intent: str) -> str:
    s = str(design_intent or "").strip().lower()
    if "reactor" in s or "pilot" in s or "demonstration" in s:
        return "reactor"
    if "research" in s or "hfs" in s or "high-field" in s:
        return "research"
    return "unknown"


def _fmt_num(x: Any, *, digits: int = 3) -> str:
    v = _sf(x)
    if not math.isfinite(v):
        return "n/a"
    return f"{v:.{digits}g}"


def _is_dd_fuel(fuel_mode: str) -> bool:
    return str(fuel_mode or "").strip().upper().startswith("DD")


def _q_infeasible_suppressed(q: float, *, fuel_mode: str) -> Tuple[bool, str]:
    if not math.isfinite(q):
        return False, ""
    if _is_dd_fuel(fuel_mode):
        if q > _Q_MAX_INFEASIBLE_DD:
            return True, (
                f"Raw Q_DT_eqv={q:.3g} exceeds DD headline cap ({_Q_MAX_INFEASIBLE_DD:g}) "
                "on an infeasible point — suppressed from hero."
            )
        return False, ""
    if q > _Q_MAX_INFEASIBLE_DT:
        return True, (
            f"Raw Q_DT_eqv={q:.3g} exceeds headline credibility cap ({_Q_MAX_INFEASIBLE_DT:g}) "
            "on an infeasible point — power-balance diagnostic only."
        )
    return False, ""


def _h98_infeasible_suppressed(h98: float, *, design_intent: str) -> Tuple[bool, str]:
    if not math.isfinite(h98):
        return False, ""
    env = _envelope_for_intent(_intent_bucket(design_intent))
    if h98 > float(env.H98_max):
        return True, (
            f"Implied H98={h98:.3g} exceeds {env.H98_max:.2g}× IPB98(y,2) credibility envelope "
            f"({env.intent}) — fixed-Ti closure, not achieved confinement."
        )
    return False, ""


def hero_kpi_cells(
    out: Dict[str, Any],
    summary: Dict[str, Any],
    *,
    design_intent: str = "",
    fuel_mode: str = "DT",
    headline: Optional[Dict[str, Any]] = None,
) -> List[HeroKpiCell]:
    """Build hero KPI cells with infeasibility-aware suppression."""
    feasible = bool(summary.get("feasible"))
    head = headline if isinstance(headline, dict) else {}

    q_raw = _sf(head.get("Q_DT_eqv", out.get("Q_DT_eqv", out.get("Q"))))
    h98_raw = _sf(head.get("H98", out.get("H98")))
    pnet_raw = _sf(head.get("P_net_e_MW", out.get("P_net_e_MW", out.get("P_e_net_MW"))))
    pfus_raw = _sf(
        head.get(
            "Pfus_total_MW",
            out.get("Pfus_total_MW", out.get("P_fus_MW", out.get("Pfus_MW"))),
        )
    )

    notes: List[str] = []
    q_sup, q_note = (False, "")
    h98_sup, h98_note = (False, "")
    pnet_sup = False
    pfus_sup = False

    if not feasible:
        q_extreme_sup, q_extreme_note = _q_infeasible_suppressed(q_raw, fuel_mode=fuel_mode)
        h98_sup, h98_note = _h98_infeasible_suppressed(h98_raw, design_intent=design_intent)
        # INFEASIBLE: never present Q / P_net,e / Pfus as design claims (PHYS-KPI-001).
        q_sup = math.isfinite(q_raw)
        pnet_sup = math.isfinite(pnet_raw)
        pfus_sup = math.isfinite(pfus_raw)
        if q_extreme_sup and q_extreme_note:
            q_note = q_extreme_note
        elif q_sup:
            q_note = (
                "Q on an INFEASIBLE point is power-balance closure only — not a performance claim."
            )
        if pnet_sup:
            notes.append(
                "P_net,e on an INFEASIBLE point is plant bookkeeping residue — not a net-electric claim."
            )
        if pfus_sup:
            notes.append(
                "Pfus on an INFEASIBLE point is fusion-power closure only — not an achievement claim."
            )
    else:
        q_sup, q_note = (False, "")
        h98_sup, h98_note = (False, "")
        pnet_sup = False
        pfus_sup = False

    if q_note:
        notes.append(q_note)
    if h98_note:
        notes.append(h98_note)

    mirage = bool(out.get("mirage_flag_v402"))
    if feasible and mirage:
        notes.append(
            "Feasible but credibility-fragile — treat KPIs as screening only until dominance review."
        )

    q_display = "—" if q_sup else (summary.get("q_label") or f"Q={_fmt_num(q_raw)}")
    if q_sup and math.isfinite(q_raw):
        q_display = "— (diagnostic)"

    h98_display = "— (implied)" if h98_sup else _fmt_num(h98_raw)
    if math.isfinite(pnet_raw) and not pnet_sup:
        pnet_display = f"{_fmt_num(pnet_raw)} MW"
    elif pnet_sup:
        pnet_display = "— (diagnostic)"
    else:
        pnet_display = "n/a"

    if math.isfinite(pfus_raw) and not pfus_sup:
        pfus_display = f"{_fmt_num(pfus_raw)} MW"
    elif pfus_sup:
        pfus_display = "— (diagnostic)"
    else:
        pfus_display = "n/a"

    nt_label = summary.get("nt_label", "n·T=n/a")
    if not feasible and (q_sup or h98_sup):
        nt_label = "— (diagnostic)"

    cells = [
        HeroKpiCell("Performance", q_display, suppressed=q_sup, raw_value=q_raw if math.isfinite(q_raw) else None),
        HeroKpiCell(
            "Pfus",
            pfus_display,
            suppressed=pfus_sup,
            raw_value=pfus_raw if math.isfinite(pfus_raw) else None,
        ),
        HeroKpiCell("H98(y,2)", h98_display, suppressed=h98_sup, raw_value=h98_raw if math.isfinite(h98_raw) else None, note=h98_note),
        HeroKpiCell("P_net,e", pnet_display, suppressed=pnet_sup, raw_value=pnet_raw if math.isfinite(pnet_raw) else None),
        HeroKpiCell("n·T (pressure proxy)", nt_label, suppressed=bool(q_sup or h98_sup)),
    ]
    return cells


def hero_diagnostic_notes(
    out: Dict[str, Any],
    summary: Dict[str, Any],
    *,
    design_intent: str = "",
    fuel_mode: str = "DT",
    headline: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Collect caption lines for suppressed / fragile hero KPIs."""
    from ui_nicegui.lib.pd_intent_policy import classify_failed_constraints, design_intent_key
    from ui_nicegui.lib.pd_parity_helpers import failed_hard_names

    cells = hero_kpi_cells(
        out, summary, design_intent=design_intent, fuel_mode=fuel_mode, headline=headline
    )
    notes: List[str] = []
    if (
        not summary.get("feasible")
        and design_intent_key(design_intent) == "research"
        and isinstance(out, dict)
    ):
        cls = classify_failed_constraints(failed_hard_names(out), design_intent=design_intent)
        exhaust_diag = [n for n in cls.get("diagnostic", []) if n in ("q_div", "P_SOL/R")]
        if exhaust_diag:
            notes.append(
                "Research covenant: divertor / exhaust limits ("
                + ", ".join(exhaust_diag)
                + ") are diagnostic-only — not blocking under this intent. "
                "Do not treat Q or P_net,e as compliance claims."
            )
    for c in cells:
        if c.note and c.note not in notes:
            notes.append(c.note)
    if any(c.suppressed for c in cells):
        notes.insert(
            0,
            "Headline KPIs suppressed or labeled **diagnostic** — point is INFEASIBLE; "
            "see Telemetry for raw closure values and Constraints for attribution.",
        )
    return notes
