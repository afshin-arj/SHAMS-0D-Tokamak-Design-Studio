"""Deterministic plasma–engineering coupling narratives.

Post-processing only; MUST NOT modify physics truth.
No solvers, no iteration, no smoothing, no randomness.

Consumes already-emitted authority results (margins, regime labels, dominance)
and emits coupling flags + narratives for UI and reviewer packs.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CouplingNarrative:
    code: str
    title: str
    narrative: str
    severity: int  # 1..5


def _as_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return float("nan")


def _has(x: float) -> bool:
    return x == x


def _frag_class(min_margin: Optional[float], fragile_thr: float = 0.05) -> str:
    if min_margin is None:
        return "UNKNOWN"
    if not _has(min_margin):
        return "UNKNOWN"
    if min_margin < 0:
        return "INFEASIBLE"
    if min_margin < fragile_thr:
        return "FRAGILE"
    return "FEASIBLE"


def evaluate_coupling_narratives(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Return a coupling narrative bundle.

    The function is deterministic and side-effect free.
    """
    dom_auth = str(artifact.get("dominant_authority", "") or "").upper()
    dom_con = str(artifact.get("dominant_constraint", "") or "")

    # Pull common margins (signed fractional). Missing => NaN.
    m_pl = _as_float(artifact.get("plasma_min_margin_frac"))
    m_ex = _as_float(artifact.get("exhaust_min_margin_frac"))
    m_mag = _as_float(artifact.get("magnet_margin_min"))
    m_imp = _as_float(artifact.get("impurity_min_margin_frac"))
    m_nuc = _as_float(artifact.get("neutronics_materials_min_margin_frac"))

    # If magnet_min isn't available, attempt common alternatives.
    if not _has(m_mag):
        m_mag = _as_float(artifact.get("magnet_min_margin_frac"))

    flags: List[str] = []
    narratives: List[CouplingNarrative] = []

    def add(code: str, title: str, text: str, severity: int) -> None:
        flags.append(code)
        narratives.append(CouplingNarrative(code=code, title=title, narrative=text, severity=int(severity)))

    # Coupling logic (conservative, explainable rules).
    # 1) Non-plasma authority blocks before plasma regime engages.
    if dom_auth in {"MAGNET", "EXHAUST", "NEUTRONICS", "FUEL", "PLANT", "CONTROL"}:
        if _has(m_pl) and m_pl > 0:
            add(
                code=f"{dom_auth}_BLOCKS_BEFORE_PLASMA",
                title=f"{dom_auth} limits before plasma limits",
                text=(
                    f"Dominant feasibility killer is {dom_auth} (constraint: {dom_con}). "
                    f"Plasma authority minimum margin is positive ({m_pl:.3f}), "
                    "so improving plasma performance alone is unlikely to unlock feasibility. "
                    "Prioritize the dominant engineering/authority blocker first."
                ),
                severity=4,
            )

    # 2) Plasma-limited but engineering fragile.
    if dom_auth == "PLASMA":
        # Magnet fragility
        if _has(m_mag) and m_mag >= 0 and m_mag < 0.05:
            add(
                code="PLASMA_DOMINANT_MAGNET_FRAGILE",
                title="Plasma-limited with fragile magnet margins",
                text=(
                    f"Plasma is the dominant limiter (constraint: {dom_con}), but magnet min margin is small ({m_mag:.3f}). "
                    "Optimization/search may appear plasma-limited while being practically governed by magnet fragility."
                ),
                severity=3,
            )
        # Exhaust fragility
        if _has(m_ex) and m_ex >= 0 and m_ex < 0.05:
            add(
                code="PLASMA_DOMINANT_EXHAUST_FRAGILE",
                title="Plasma-limited with fragile exhaust margins",
                text=(
                    f"Plasma is dominant (constraint: {dom_con}), but exhaust min margin is small ({m_ex:.3f}). "
                    "Operational headroom may be controlled by divertor/SOL limits even if core limits dominate nominally."
                ),
                severity=3,
            )

    # 3) Radiation-driven coupling (impurity/edge).
    rad_dom = str(artifact.get("exhaust_regime", "") or "").lower() == "radiation_dominated"
    if rad_dom and _has(m_imp) and m_imp < 0.05:
        add(
            code="RADIATION_COUPLING_CORE_EDGE",
            title="Coupled core radiation and edge detachment regime",
            text=(
                "Exhaust regime is radiation-dominated and impurity/radiation authority is near limit. "
                f"Impurity min margin is {m_imp:.3f}. This indicates tight coupling between impurity seeding, "
                "core radiation partition, and edge power handling."
            ),
            severity=4,
        )

    # 4) Neutronics-driven coupling (shield/build affects magnets and plasma).
    if dom_auth == "NEUTRONICS" and (_has(m_mag) or _has(m_pl)):
        add(
            code="NEUTRONICS_GEOMETRY_COUPLING",
            title="Neutronics limits coupled to build and magnet feasibility",
            text=(
                "Neutronics/materials is dominant. Shield/build adjustments that improve neutron wall load or lifetime "
                "will also affect inboard space for TF coils and hence Bpeak/Jeng/stress margins, and can move the plasma operating point. "
                "Treat R0 and inboard build as coupled knobs."
            ),
            severity=4,
        )

    # Summary string (deterministic).
    if narratives:
        max_sev = max(n.severity for n in narratives)
        summary = f"{len(narratives)} coupling narratives (max severity {max_sev}/5)."
    else:
        max_sev = 0
        summary = "No strong plasma–engineering coupling flags triggered."

    return {
        "schema_version": "coupling_narratives.v1",
        "coupling_summary": summary,
        "coupling_severity_max": int(max_sev),
        "coupling_flags": flags,
        "coupling_narratives": [
            {"code": n.code, "title": n.title, "narrative": n.narrative, "severity": n.severity}
            for n in narratives
        ],
        "coupling_context": {
            "dominant_authority": dom_auth,
            "dominant_constraint": dom_con,
            "min_margins": {
                "plasma_min_margin_frac": m_pl if _has(m_pl) else None,
                "exhaust_min_margin_frac": m_ex if _has(m_ex) else None,
                "magnet_min_margin": m_mag if _has(m_mag) else None,
                "impurity_min_margin_frac": m_imp if _has(m_imp) else None,
                "neutronics_materials_min_margin_frac": m_nuc if _has(m_nuc) else None,
            },
        },
    }
