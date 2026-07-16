from __future__ import annotations

"""Magnet SC system authority v410 — TF / PF / CS depth beyond v400.

Purpose
-------
MATCH-as-overlay deepening of PROCESS-class TF/PF/CS + superconductor *coverage*
for DEMO-like studies, without putting magnet iteration into L0.

v400 covers a TF technology margin ledger (B–J–stress–SC–T[/ohmic]).
v410 adds an explicit **per-family** (TF / PF / CS) superconducting / engineering
margin stack from already-computed truth + proxy outputs, plus a combined system
margin and dominant limiter.

Hard laws
---------
- Algebraic, single-pass, deterministic. No solvers, no iteration, no smoothing.
- Does **not** mutate L0 truth equations; governance overlay only.
- Screening / proxy tier — not a replacement for detailed coil design codes.
- No invented PROCESS MFILE reference numbers; uses magnet_tech_contract allowables
  and existing SHAMS outputs only.

Inputs (expected)
-----------------
From ``inp``:
- magnet_technology, include_magnet_sc_system_authority_v410
- optional caps: magnet_system_margin_min_v410, tf/pf/cs family margin mins
- cs_Bmax_T (operating CS peak field proxy)

From ``out`` (already computed):
- TF: magnet_v400_* margins, B_peak_*, J_eng_*, sigma_*, hts_margin*, Tcoil_*,
  quench_proxy_*, coil_heat_nuclear_*
- CS: cs_flux_margin, cs_struct_margin_v389 (optional), cs_Bmax via inp
- PF: pf_I_peak_MA, pf_stress_proxy, pf_* envelope peaks + caps

Author
------
© 2026 Afshin Arjhangmehr
"""

import math
from typing import Any, Dict, List, Optional, Tuple


AUTHORITY_ID = "magnet_sc_system_authority_v410"
OVERLAY_VERSION = "v410.0.0"
SCREENING_TIER = "proxy"


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else float(default)
    except (TypeError, ValueError):
        return float(default)


def _finite(x: float) -> bool:
    return x == x and math.isfinite(x)


def _ratio_margin(allow: float, req: float) -> float:
    """Return (allow/req - 1). NaN if not computable."""
    a = _f(allow)
    r = _f(req)
    if not (_finite(a) and _finite(r)) or r <= 0.0:
        return float("nan")
    return a / r - 1.0


def _tier_from_margin(m: float, fragile: float = 0.05) -> str:
    if not _finite(m):
        return "unknown"
    if m < 0.0:
        return "deficit"
    if m < fragile:
        return "near_limit"
    return "comfortable"


def _min_finite(values: List[float]) -> float:
    finite = [v for v in values if _finite(v)]
    return min(finite) if finite else float("nan")


def _is_copper(tech: str) -> bool:
    t = (tech or "").upper()
    return "COPPER" in t or t in ("CU", "RESISTIVE", "COPPER_TF") or "RESIST" in t


def _tf_family(out: Dict[str, Any], tech: str, fragile: float) -> Dict[str, Any]:
    """TF family: prefer v400 ledger; deepen with quench + nuclear heat margins."""
    margins: List[Tuple[str, float]] = []

    v400 = _f(out.get("magnet_v400_margin"))
    if _finite(v400):
        margins.append(("tf_v400_combined", v400))
    else:
        # Reconstruct TF aspects if v400 off
        for key, label in (
            ("magnet_v400_b_margin", "tf_B"),
            ("magnet_v400_j_margin", "tf_J"),
            ("magnet_v400_stress_margin", "tf_stress"),
            ("magnet_v400_sc_oper_margin", "tf_sc_oper"),
            ("magnet_v400_t_window_margin", "tf_T_window"),
        ):
            m = _f(out.get(key))
            if _finite(m):
                margins.append((label, m))
        if not margins:
            margins.append(("tf_B", _ratio_margin(_f(out.get("B_peak_allow_T")), _f(out.get("B_peak_T")))))
            margins.append(("tf_J", _ratio_margin(_f(out.get("J_eng_max_A_mm2")), _f(out.get("J_eng_A_mm2")))))
            margins.append(("tf_stress", _ratio_margin(_f(out.get("sigma_allow_MPa")), _f(out.get("sigma_vm_MPa")))))
            sc = _f(out.get("hts_margin"))
            sc_min = _f(out.get("hts_margin_min"), 1.0)
            if _finite(sc) and _finite(sc_min) and sc_min > 0.0:
                margins.append(("tf_sc_oper", sc / sc_min - 1.0))

    q = _f(out.get("quench_proxy_margin"))
    q_min = _f(out.get("quench_proxy_min"))
    if _finite(q) and _finite(q_min):
        # quench_proxy_margin is already a margin-like quantity vs min
        margins.append(("tf_quench", q - q_min if _finite(q_min) else q))

    pn = _f(out.get("coil_heat_nuclear_MW"))
    pn_max = _f(out.get("coil_heat_nuclear_max_MW"))
    if _finite(pn) and _finite(pn_max):
        margins.append(("tf_nuclear_heat", _ratio_margin(pn_max, pn)))

    if _is_copper(tech):
        poh = _f(out.get("magnet_v400_p_tf_ohmic_margin"))
        if not _finite(poh):
            poh = _ratio_margin(_f(out.get("P_tf_ohmic_max_MW")), _f(out.get("P_tf_ohmic_MW")))
        if _finite(poh):
            margins.append(("tf_ohmic", poh))

    finite = [(k, m) for k, m in margins if _finite(m)]
    family_min = _min_finite([m for _, m in finite])
    if finite:
        dom_k, dom_m = min(finite, key=lambda km: km[1])
    else:
        dom_k, dom_m = "unknown", float("nan")

    return {
        "magnet_v410_tf_margin": float(family_min),
        "magnet_v410_tf_tier": _tier_from_margin(family_min, fragile),
        "magnet_v410_tf_dominant": str(dom_k),
        "magnet_v410_tf_dominant_margin": float(dom_m),
        "magnet_v410_tf_quench_margin": float(
            next((m for k, m in finite if k == "tf_quench"), float("nan"))
        ),
        "magnet_v410_tf_nuclear_heat_margin": float(
            next((m for k, m in finite if k == "tf_nuclear_heat"), float("nan"))
        ),
    }


def _cs_family(inp: Any, out: Dict[str, Any], tech: str, fragile: float) -> Dict[str, Any]:
    """CS family: peak-field vs contract allow, flux swing, optional structure, SC oper proxy."""
    margins: List[Tuple[str, float]] = []

    B_allow = _f(out.get("B_peak_allow_T"))
    B_cs = _f(getattr(inp, "cs_Bmax_T", float("nan")))
    if not _finite(B_cs):
        B_cs = _f(out.get("cs_Bmax_T"))
    cs_B_margin = _ratio_margin(B_allow, B_cs)
    if _finite(cs_B_margin):
        margins.append(("cs_B", cs_B_margin))

    flux_m = _f(out.get("cs_flux_margin"))
    if _finite(flux_m):
        margins.append(("cs_flux", flux_m))

    struct_m = _f(out.get("cs_struct_margin_v389"))
    if _finite(struct_m):
        margins.append(("cs_struct", struct_m))

    # SC operating proxy for CS: reuse TF critical-surface margin when SC tech;
    # when CS peak exceeds TF peak, derate by B_cs/B_tf (transparent algebraic screen).
    if not _is_copper(tech):
        sc = _f(out.get("hts_margin"))
        sc_min = _f(out.get("hts_margin_min"), 1.0)
        B_tf = _f(out.get("B_peak_T"))
        if _finite(sc) and _finite(sc_min) and sc_min > 0.0:
            sc_oper = sc / sc_min - 1.0
            if _finite(B_cs) and _finite(B_tf) and B_tf > 0.0 and B_cs > B_tf:
                # Higher CS field → tighter SC headroom; derate linearly with B ratio.
                sc_oper = sc_oper - (B_cs / B_tf - 1.0)
            margins.append(("cs_sc_oper", sc_oper))

        Tcoil = _f(out.get("Tcoil_K"), _f(getattr(inp, "Tcoil_K", float("nan"))))
        Tmin = _f(out.get("Tcoil_min_K"))
        Tmax = _f(out.get("Tcoil_max_K"))
        if _finite(Tcoil) and _finite(Tmin) and _finite(Tmax) and Tmax > Tmin:
            t_m = min((Tcoil - Tmin) / (Tmax - Tmin), (Tmax - Tcoil) / (Tmax - Tmin))
            margins.append(("cs_T_window", t_m))

    finite = [(k, m) for k, m in margins if _finite(m)]
    family_min = _min_finite([m for _, m in finite])
    if finite:
        dom_k, dom_m = min(finite, key=lambda km: km[1])
    else:
        dom_k, dom_m = "unknown", float("nan")

    return {
        "magnet_v410_cs_margin": float(family_min),
        "magnet_v410_cs_tier": _tier_from_margin(family_min, fragile),
        "magnet_v410_cs_dominant": str(dom_k),
        "magnet_v410_cs_dominant_margin": float(dom_m),
        "magnet_v410_cs_B_margin": float(cs_B_margin),
        "magnet_v410_cs_flux_margin": float(flux_m),
        "magnet_v410_cs_sc_oper_margin": float(
            next((m for k, m in finite if k == "cs_sc_oper"), float("nan"))
        ),
    }


def _pf_family(out: Dict[str, Any], tech: str, fragile: float) -> Dict[str, Any]:
    """PF family: envelope current/stress/power/energy margins + optional SC screen."""
    margins: List[Tuple[str, float]] = []

    pairs = [
        ("pf_I", "pf_I_peak_MA", "pf_I_peak_max_MA"),
        ("pf_I_legacy", "pf_I_pf_MA", "pf_current_max_MA"),
        ("pf_stress", "pf_stress_proxy", "pf_stress_max"),
        ("pf_dIdt", "pf_dIdt_peak_MA_s", "pf_dIdt_max_MA_s"),
        ("pf_V", "pf_V_peak_V", "pf_V_peak_max_V"),
        ("pf_P", "pf_P_peak_MW", "pf_P_peak_max_MW"),
        ("pf_E", "pf_E_pulse_MJ", "pf_E_pulse_max_MJ"),
        ("pf_P_avg", "P_pf_avg_MW", "P_pf_avg_max_MW"),
    ]
    seen_I = False
    for label, vkey, lkey in pairs:
        if label.startswith("pf_I") and seen_I:
            continue
        m = _ratio_margin(_f(out.get(lkey)), _f(out.get(vkey)))
        if _finite(m):
            margins.append((label if not label.startswith("pf_I") else "pf_I", m))
            if label.startswith("pf_I"):
                seen_I = True

    # Optional PF peak field screen if caller provided pf_Bmax_T / allow
    B_pf = _f(out.get("pf_Bmax_T"), _f(out.get("pf_B_peak_T")))
    B_allow = _f(out.get("B_peak_allow_T"))
    pf_B_margin = _ratio_margin(B_allow, B_pf)
    if _finite(pf_B_margin):
        margins.append(("pf_B", pf_B_margin))

    if not _is_copper(tech):
        sc = _f(out.get("hts_margin"))
        sc_min = _f(out.get("hts_margin_min"), 1.0)
        if _finite(sc) and _finite(sc_min) and sc_min > 0.0:
            # PF coils typically see lower peak B than TF; use TF SC margin as
            # conservative shared-cryostat SC headroom screen (documented proxy).
            margins.append(("pf_sc_oper", sc / sc_min - 1.0))

    finite = [(k, m) for k, m in margins if _finite(m)]
    family_min = _min_finite([m for _, m in finite])
    if finite:
        dom_k, dom_m = min(finite, key=lambda km: km[1])
    else:
        dom_k, dom_m = "unknown", float("nan")

    return {
        "magnet_v410_pf_margin": float(family_min),
        "magnet_v410_pf_tier": _tier_from_margin(family_min, fragile),
        "magnet_v410_pf_dominant": str(dom_k),
        "magnet_v410_pf_dominant_margin": float(dom_m),
        "magnet_v410_pf_I_margin": float(
            next((m for k, m in finite if k == "pf_I"), float("nan"))
        ),
        "magnet_v410_pf_stress_margin": float(
            next((m for k, m in finite if k == "pf_stress"), float("nan"))
        ),
        "magnet_v410_pf_B_margin": float(pf_B_margin),
        "magnet_v410_pf_sc_oper_margin": float(
            next((m for k, m in finite if k == "pf_sc_oper"), float("nan"))
        ),
    }


def compute(inp: Any, out: Dict[str, Any]) -> Dict[str, Any]:
    tech = str(getattr(inp, "magnet_technology", "") or out.get("magnet_technology", "") or "").strip()
    if not tech:
        tech = "UNKNOWN"
    fragile = _f(out.get("fragile_margin_frac"), _f(getattr(inp, "fragile_margin_frac", 0.05)))
    if not _finite(fragile):
        fragile = 0.05

    tf = _tf_family(out, tech, fragile)
    cs = _cs_family(inp, out, tech, fragile)
    pf = _pf_family(out, tech, fragile)

    family_rows: List[Tuple[str, float]] = [
        ("TF", _f(tf["magnet_v410_tf_margin"])),
        ("PF", _f(pf["magnet_v410_pf_margin"])),
        ("CS", _f(cs["magnet_v410_cs_margin"])),
    ]
    finite_fam = [(k, m) for k, m in family_rows if _finite(m)]
    system_margin = _min_finite([m for _, m in finite_fam])
    if finite_fam:
        dom_fam, dom_fam_m = min(finite_fam, key=lambda km: km[1])
    else:
        dom_fam, dom_fam_m = "unknown", float("nan")

    patch: Dict[str, Any] = {
        "magnet_v410_enabled": True,
        "magnet_v410_authority_id": AUTHORITY_ID,
        "magnet_v410_overlay_version": OVERLAY_VERSION,
        "magnet_v410_screening_tier": SCREENING_TIER,
        "magnet_v410_technology": tech.upper() if tech != "UNKNOWN" else tech,
        "magnet_v410_provenance": (
            "algebraic TF/PF/CS margin stack from magnet_tech_contract allowables "
            "+ existing SHAMS TF/PF/CS proxies; not PROCESS MFILE parity"
        ),
        "magnet_v410_contract_sha256": str(out.get("magnet_contract_sha256", "") or ""),
        "magnet_v410_system_margin": float(system_margin),
        "magnet_v410_system_tier": _tier_from_margin(system_margin, fragile),
        "magnet_v410_dominant_family": str(dom_fam),
        "magnet_v410_dominant_family_margin": float(dom_fam_m),
        # Optional caps echoed for constraint layer (NaN disables)
        "magnet_system_margin_min_v410": _f(getattr(inp, "magnet_system_margin_min_v410", float("nan"))),
        "tf_family_margin_min_v410": _f(getattr(inp, "tf_family_margin_min_v410", float("nan"))),
        "pf_family_margin_min_v410": _f(getattr(inp, "pf_family_margin_min_v410", float("nan"))),
        "cs_family_margin_min_v410": _f(getattr(inp, "cs_family_margin_min_v410", float("nan"))),
    }
    patch.update(tf)
    patch.update(cs)
    patch.update(pf)

    # Units ledger for reviewer packs / UI
    patch["magnet_v410_units"] = {
        "margins": "fraction (allow/req - 1 or signed headroom)",
        "B": "T",
        "J_eng": "A/mm^2",
        "stress": "MPa",
        "I_pf": "MA",
        "P": "MW",
        "E_pulse": "MJ",
        "flux": "Wb",
        "T": "K",
    }
    return patch


def evaluate_magnet_sc_system_authority_v410(out: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    """Deterministic TF/PF/CS SC system overlay. Does not re-solve physics.

    When disabled, returns ``{}`` so default evaluator outputs (and goldens) are
    unchanged — L0 numeric truth and artifact key sets stay frozen.
    """
    enabled = bool(getattr(inp, "include_magnet_sc_system_authority_v410", False))
    if not enabled:
        return {}
    patch = compute(inp, out)
    patch["include_magnet_sc_system_authority_v410"] = True
    return patch
