"""SHAMS — Authority Dominance Engine 2.0 (v402.0.0)

Author: © 2026 Afshin Arjhangmehr

Purpose
-------
Governance-only post-processing overlay that produces a *global* dominance ranking
across major authority modules and classifies the operating *regime*.

Hard laws
---------
- Deterministic and algebraic (no solvers, no iteration, no smoothing).
- Does not mutate core TRUTH; only augments outputs.
- Missing fields are handled non-fatally (NaN margins + UNKNOWN tiers).

Design
------
v402 consumes already-computed authority outputs:
  - v396: transport envelope spread ratio + tier
  - v397: profile proxy metrics + optional caps
  - v398: control & stability ledger margins + optional caps
  - v399: impurity/radiation partition + detachment diagnostics
  - v400: magnet technology authority margin ledger
  - v401: neutronics/materials contract tier min margin

It produces:
  - authority_margin_map_v402: {authority: min_margin_frac}
  - dominance_order_v402: sorted table (worst->best)
  - global_dominant_authority_v402, global_min_margin_v402
  - regime_class_v402: deterministic regime label
  - mirage_flag_v402: feasible but credibility-fragile flag + reasons

Notes on normalization
---------------------
Margins are normalized to *signed fractional* margins where possible:
  - For "le"-type caps: (cap - value)/cap
  - For "ge"-type caps or already-a-margin: use directly

Where a cap is not provided, v402 uses conservative fixed reference thresholds
to provide a deterministic ranking signal. These are explicitly reported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import math


def _nan() -> float:
    return float("nan")


def _finite(x: float) -> bool:
    return bool(x == x and math.isfinite(x))


def _sf(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _margin_le(value: float, cap: float) -> float:
    """Signed fractional margin for value <= cap."""
    if not (_finite(value) and _finite(cap) and cap > 0.0):
        return _nan()
    return (cap - value) / cap


def _margin_ge(value: float, floor: float) -> float:
    """Signed fractional margin for value >= floor."""
    if not (_finite(value) and _finite(floor) and abs(floor) > 0.0):
        return _nan()
    return (value - floor) / abs(floor)


def _min_finite(values: List[float]) -> float:
    mm = _nan()
    for v in values:
        if _finite(v):
            mm = v if (not _finite(mm) or v < mm) else mm
    return mm


@dataclass(frozen=True)
class DominanceRowV402:
    authority: str
    min_margin_frac: float
    notes: str


def evaluate_authority_dominance_v402(out: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    enabled = bool(getattr(inp, "include_authority_dominance_v402", True))
    if not enabled:
        return {
            "include_authority_dominance_v402": False,
            "authority_margin_map_v402": {},
            "dominance_order_v402": [],
            "global_dominant_authority_v402": "OFF",
            "global_min_margin_v402": _nan(),
            "dominance_gap_to_second_v402": _nan(),
            "regime_class_v402": "OFF",
            "mirage_flag_v402": False,
            "mirage_reasons_v402": [],
            "authority_dominance_contract_sha256_v402": "3b2b2e1f2c5a4f0d9a7b8c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7402",
        }

    # Reference thresholds (used only when explicit caps are not provided)
    # These are deliberately conservative, intended for ranking/diagnostics only.
    ref_transport_spread = float(getattr(inp, "transport_spread_ref_v402", 3.0) or 3.0)
    ref_profile_peaking_p = float(getattr(inp, "profile_peaking_p_ref_v402", 3.0) or 3.0)
    ref_zeff_max = float(getattr(inp, "zeff_ref_max_v402", 2.5) or 2.5)

    rows: List[DominanceRowV402] = []

    # ------------------------------------------------------------------
    # Transport authority (v396)
    # ------------------------------------------------------------------
    spread = _sf(out.get("transport_spread_ratio_v396", _nan()))
    cap = _sf(out.get("transport_spread_max_v396", _nan()))
    cap_enabled = bool(out.get("transport_spread_cap_enabled_v396", False)) and _finite(cap) and cap > 0.0
    if _finite(spread):
        m = _margin_le(spread, cap) if cap_enabled else _margin_le(spread, ref_transport_spread)
        note = f"spread_ratio={spread:.3g}; cap={'on' if cap_enabled else 'ref'}={cap if cap_enabled else ref_transport_spread:.3g}"
        rows.append(DominanceRowV402("TRANSPORT", float(m), note))

    # ------------------------------------------------------------------
    # Profile proxy authority (v397)
    # ------------------------------------------------------------------
    ppk = _sf(out.get("profile_peaking_p_v397", _nan()))
    q95 = _sf(out.get("q95_proxy_v397", _nan()))
    q0 = _sf(out.get("q0_proxy_v397", _nan()))
    boot_loc = _sf(out.get("bootstrap_localization_index_v397", _nan()))
    ppk_cap = _sf(out.get("profile_peaking_p_max_v397", _nan()))
    q95_floor = _sf(out.get("q95_proxy_min_v397", _nan()))
    q0_floor = _sf(out.get("q0_proxy_min_v397", _nan()))
    boot_cap = _sf(out.get("bootstrap_localization_max_v397", _nan()))

    prof_margins: List[float] = []
    prof_notes: List[str] = []
    if _finite(ppk):
        prof_margins.append(_margin_le(ppk, ppk_cap) if _finite(ppk_cap) and ppk_cap > 0.0 else _margin_le(ppk, ref_profile_peaking_p))
        prof_notes.append(f"p_peaking={ppk:.3g}; cap={'set' if (_finite(ppk_cap) and ppk_cap>0) else 'ref'}={ppk_cap if (_finite(ppk_cap) and ppk_cap>0) else ref_profile_peaking_p:.3g}")
    if _finite(q95) and _finite(q95_floor):
        prof_margins.append(_margin_ge(q95, q95_floor))
        prof_notes.append(f"q95={q95:.3g}>= {q95_floor:.3g}")
    if _finite(q0) and _finite(q0_floor):
        prof_margins.append(_margin_ge(q0, q0_floor))
        prof_notes.append(f"q0={q0:.3g}>= {q0_floor:.3g}")
    if _finite(boot_loc) and _finite(boot_cap) and boot_cap > 0.0:
        prof_margins.append(_margin_le(boot_loc, boot_cap))
        prof_notes.append(f"boot_loc={boot_loc:.3g}<= {boot_cap:.3g}")

    prof_min = _min_finite(prof_margins)
    if _finite(prof_min):
        rows.append(DominanceRowV402("PROFILE", float(prof_min), "; ".join(prof_notes) if prof_notes else ""))

    # ------------------------------------------------------------------
    # Control & Stability (v398)
    # ------------------------------------------------------------------
    vs_margin = _sf(out.get("vs_budget_margin_v398", _nan()))
    vde_head = _sf(out.get("vde_headroom_v398", _nan()))
    rwm_idx = _sf(out.get("rwm_proximity_index_v398", _nan()))

    vs_floor = _sf(out.get("vs_budget_margin_min_v398", _nan()))
    vde_floor = _sf(out.get("vde_headroom_min_v398", _nan()))
    rwm_cap = _sf(out.get("rwm_proximity_index_max_v398", _nan()))

    ctrl_margins: List[float] = []
    ctrl_notes: List[str] = []
    if _finite(vs_margin):
        if _finite(vs_floor):
            ctrl_margins.append(_margin_ge(vs_margin, vs_floor))
            ctrl_notes.append(f"vs_margin={vs_margin:.3g}>= {vs_floor:.3g}")
        else:
            ctrl_margins.append(vs_margin)
            ctrl_notes.append(f"vs_margin={vs_margin:.3g}")
    if _finite(vde_head):
        if _finite(vde_floor):
            ctrl_margins.append(_margin_ge(vde_head, vde_floor))
            ctrl_notes.append(f"vde_headroom={vde_head:.3g}>= {vde_floor:.3g}")
        else:
            ctrl_margins.append(vde_head)
            ctrl_notes.append(f"vde_headroom={vde_head:.3g}")
    if _finite(rwm_idx):
        if _finite(rwm_cap) and rwm_cap > 0.0:
            ctrl_margins.append(_margin_le(rwm_idx, rwm_cap))
            ctrl_notes.append(f"rwm_idx={rwm_idx:.3g}<= {rwm_cap:.3g}")
        else:
            # interpret proximity index: smaller is better; use 1-idx as a normalized margin
            ctrl_margins.append(1.0 - rwm_idx)
            ctrl_notes.append(f"rwm_idx={rwm_idx:.3g} (margin~1-idx)")

    ctrl_min = _min_finite(ctrl_margins)
    if _finite(ctrl_min):
        rows.append(DominanceRowV402("CONTROL", float(ctrl_min), "; ".join(ctrl_notes) if ctrl_notes else ""))

    # ------------------------------------------------------------------
    # Exhaust/Radiation (v399 implicit; values already in TRUTH outputs)
    # ------------------------------------------------------------------
    Zeff = _sf(out.get("impurity_v399_zeff", out.get("Zeff", out.get("impurity_zeff_proxy", _nan()))))
    det_margin = _sf(out.get("detachment_margin", out.get("detachment_margin_v399", _nan())))

    # If detachment_margin is not directly available, attempt derive from required radiation
    if not _finite(det_margin):
        prad_sol_div = _sf(out.get("impurity_v399_prad_sol_MW", _nan())) + _sf(out.get("impurity_v399_prad_div_MW", _nan()))
        prad_req = _sf(out.get("detachment_prad_sol_div_required_MW", _nan()))
        if _finite(prad_sol_div) and _finite(prad_req) and prad_req > 0.0:
            det_margin = prad_sol_div / prad_req - 1.0

    rad_margins: List[float] = []
    rad_notes: List[str] = []
    if _finite(Zeff):
        rad_margins.append(_margin_le(Zeff, ref_zeff_max))
        rad_notes.append(f"Zeff={Zeff:.3g}<=ref {ref_zeff_max:.3g}")
    if _finite(det_margin):
        rad_margins.append(det_margin)  # already >=0 feasible
        rad_notes.append(f"det_margin={det_margin:.3g} (ach/req - 1)")
    rad_min = _min_finite(rad_margins)
    if _finite(rad_min):
        rows.append(DominanceRowV402("EXHAUST_RADIATION", float(rad_min), "; ".join(rad_notes) if rad_notes else ""))

    # ------------------------------------------------------------------
    # Magnet tech (v400)
    # ------------------------------------------------------------------
    mag = _sf(out.get("magnet_v400_margin", _nan()))
    if _finite(mag):
        rows.append(DominanceRowV402("MAGNET", float(mag), f"magnet_v400_margin={mag:.3g}"))

    
    # ------------------------------------------------------------------
    # Structural life authority (v404 preferred; fallback v389 stress margins)
    # ------------------------------------------------------------------
    struct_min = _sf(out.get("struct_global_min_margin_v404", _nan()))
    if not _finite(struct_min):
        # fallback to v389 structural stress margins if v404 not enabled
        tfm = _sf(out.get("tf_struct_margin_v389", _nan()))
        vvm = _sf(out.get("vv_struct_margin_v389", _nan()))
        csm = _sf(out.get("cs_struct_margin_v389", _nan()))
        struct_min = _min_finite([tfm, vvm, csm])
        note = "fallback=v389; min(tf,vv,cs)"
    else:
        note = f"v404_min_margin={struct_min:+.3f}"
    if _finite(struct_min):
        rows.append(DominanceRowV402("STRUCTURAL", float(struct_min), note))

# ------------------------------------------------------------------
    # Neutronics/Materials (v403 preferred; fallback v401)
    # ------------------------------------------------------------------
    nm403 = _sf(out.get("nm_min_margin_frac_v403", _nan()))
    if _finite(nm403) and bool(out.get("include_neutronics_materials_library_v403", False)):
        tier403 = str(out.get("nm_regime_tier_v403", "UNKNOWN") or "UNKNOWN")
        dom403 = str(out.get("nm_dominant_driver_v403", "unknown") or "unknown")
        rows.append(DominanceRowV402(
            "NEUTRONICS_MATERIALS",
            float(nm403),
            f"v403 min_margin={nm403:.3g}; tier={tier403}; dom={dom403}",
        ))
    else:
        nm = _sf(out.get("nm_min_margin_frac_v401", _nan()))
        if _finite(nm):
            tier = str(out.get("nm_contract_tier_v401", "NOMINAL") or "NOMINAL")
            rows.append(DominanceRowV402("NEUTRONICS_MATERIALS", float(nm), f"v401 min_margin={nm:.3g}; tier={tier}"))

    # Build ranking
    finite_rows = [r for r in rows if _finite(r.min_margin_frac)]
    finite_rows.sort(key=lambda r: r.min_margin_frac)

    if not finite_rows:
        return {
            "include_authority_dominance_v402": True,
            "authority_margin_map_v402": {},
            "dominance_order_v402": [],
            "global_dominant_authority_v402": "unknown",
            "global_min_margin_v402": _nan(),
            "dominance_gap_to_second_v402": _nan(),
            "regime_class_v402": "unknown",
            "mirage_flag_v402": False,
            "mirage_reasons_v402": ["no_finite_authority_margins"],
            "authority_dominance_contract_sha256_v402": "3b2b2e1f2c5a4f0d9a7b8c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7402",
            "authority_dominance_refs_v402": {
                "transport_spread_ref": ref_transport_spread,
                "profile_peaking_p_ref": ref_profile_peaking_p,
                "zeff_ref_max": ref_zeff_max,
            },
        }

    dom = finite_rows[0]
    second = finite_rows[1] if len(finite_rows) > 1 else None
    gap2 = (second.min_margin_frac - dom.min_margin_frac) if (second is not None) else _nan()

    regime = str(dom.authority)
    # Provide a stable label namespace
    if regime == "EXHAUST_RADIATION":
        regime_class = "EXHAUST_RADIATION_LIMITED"
    elif regime == "MAGNET":
        regime_class = "MAGNET_LIMITED"
    elif regime == "CONTROL":
        regime_class = "CONTROL_LIMITED"
    elif regime == "TRANSPORT":
        regime_class = "TRANSPORT_FRAGILITY"
    elif regime == "PROFILE":
        regime_class = "PROFILE_SAFETY_LIMITED"
    elif regime == "NEUTRONICS_MATERIALS":
        regime_class = "NEUTRONICS_MATERIALS_LIMITED"
    elif regime == "STRUCTURAL":
        regime_class = "STRUCTURAL_LIFE_LIMITED"
    else:
        regime_class = "UNKNOWN"

    # Mirage detector: feasible but driven by thin margins + epistemic fragility
    is_feasible = bool(out.get("is_feasible", out.get("feasible", False)))
    mirage = False
    reasons: List[str] = []
    try:
        transport_tier = str(out.get("transport_credibility_tier_v396", ""))
        if transport_tier.lower() in {"weak", "questionable"}:
            reasons.append(f"transport_tier={transport_tier}")
    except Exception:
        pass
    if _finite(spread) and spread > 1.2 * ref_transport_spread:
        reasons.append(f"transport_spread_high={spread:.3g}")
    if _finite(mag) and mag < 0.05:
        reasons.append(f"magnet_margin_thin={mag:.3g}")
    if str(out.get("nm_contract_tier_v401", "NOMINAL") or "NOMINAL").upper() == "OPTIMISTIC":
        reasons.append("nm_tier_optimistic")
    if _finite(nm) and nm < 0.05:
        reasons.append(f"nm_margin_thin={nm:.3g}")

    if is_feasible and reasons:
        mirage = True

    margin_map = {r.authority: float(r.min_margin_frac) for r in finite_rows}
    order = [
        {
            "rank": i + 1,
            "authority": r.authority,
            "min_margin_frac": float(r.min_margin_frac),
            "notes": r.notes,
        }
        for i, r in enumerate(finite_rows)
    ]

    return {
        "include_authority_dominance_v402": True,
        "authority_margin_map_v402": margin_map,
        "dominance_order_v402": order,
        "global_dominant_authority_v402": str(dom.authority),
        "global_min_margin_v402": float(dom.min_margin_frac),
        "dominance_gap_to_second_v402": float(gap2) if _finite(gap2) else _nan(),
        "regime_class_v402": str(regime_class),
        "mirage_flag_v402": bool(mirage),
        "mirage_reasons_v402": reasons,
        "authority_dominance_contract_sha256_v402": "3b2b2e1f2c5a4f0d9a7b8c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7402",
        "authority_dominance_refs_v402": {
            "transport_spread_ref": float(ref_transport_spread),
            "profile_peaking_p_ref": float(ref_profile_peaking_p),
            "zeff_ref_max": float(ref_zeff_max),
        },
    }
