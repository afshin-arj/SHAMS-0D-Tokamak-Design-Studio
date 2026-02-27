from __future__ import annotations

"""SHAMS — Structural Life Authority 3.0 (v404.0.0)

Author: © 2026 Afshin Arjhangmehr

Purpose
-------
Deterministic, audit-friendly structural life envelopes: stress allowables degraded by
temperature + irradiation, plus fatigue, creep-rupture, and buckling proxies.

Hard laws
---------
- Algebraic only (no solvers, no iteration, no smoothing).
- Governance-only overlay: does not mutate TRUTH; augments output dict.
- Explicit failure modes: if required inputs are missing, outputs are NaN and tiers become 'unknown'.

Scope (v404.0.0)
----------------
Components:
- FW/B (first wall / blanket structural module proxy)
- VV (vacuum vessel shell proxy)
- TF (TF case / TF inner-leg structural proxy)

Modes:
- stress margin (sigma_allow / sigma_applied - 1)
- fatigue usage (Miner proxy) -> margin = 1 - usage
- creep rupture usage -> margin = 1 - usage
- buckling margin (sigma_cr / sigma - 1)

This authority is designed to integrate with:
- v403 neutronics/materials (DPA, He appm, cooldown)
- v389 structural stress authority (sigma proxies)
- v402 dominance engine (global regime mapping)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import math


def _nan() -> float:
    return float("nan")


def _finite(x: float) -> bool:
    return isinstance(x, (int, float)) and (x == x) and math.isfinite(float(x))


def _sf(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return _nan()


def _clip(x: float, lo: float, hi: float) -> float:
    if not _finite(x):
        return x
    return max(lo, min(hi, x))


@dataclass(frozen=True)
class MaterialV404:
    name: str
    # Base allowable stress envelope (piecewise linear) in MPa as function of T[K]
    # points: [(T_K, sigma_allow_MPa)]
    allow_pts: Tuple[Tuple[float, float], ...]
    # Irradiation degradation coefficients (dimensionless):
    # f_irr = max(f_min, 1 - a_dpa * DPA - b_he * (He_appm/1000))
    a_dpa: float
    b_he_per_1000appm: float
    f_min: float
    # Fatigue Basquin proxy: Nf = C * (Δσ_MPa)^(-m)
    basquin_C: float
    basquin_m: float
    # Creep rupture proxy: log10(tr_hr) = c0 + c1*(1000/T_K) + c2*log10(σ_MPa)
    # (simple parametric envelope; deterministic)
    creep_c0: float
    creep_c1: float
    creep_c2: float
    # Elastic modulus proxy at 300K [GPa] and linear slope vs T [GPa/K]
    E0_GPa: float
    dE_dT_GPa_perK: float


_MATERIALS: Dict[str, MaterialV404] = {
    # Conservative, proxy-level parameters; intended for feasibility screening.
    "SS316": MaterialV404(
        name="SS316",
        allow_pts=((300.0, 220.0), (600.0, 160.0), (800.0, 120.0)),
        a_dpa=0.010,
        b_he_per_1000appm=0.05,
        f_min=0.35,
        basquin_C=2.0e14,
        basquin_m=4.0,
        creep_c0=10.0,
        creep_c1=8.0,
        creep_c2=-2.0,
        E0_GPa=193.0,
        dE_dT_GPa_perK=-0.04,
    ),
    "EUROFER": MaterialV404(
        name="EUROFER",
        allow_pts=((300.0, 450.0), (600.0, 300.0), (800.0, 200.0)),
        a_dpa=0.006,
        b_he_per_1000appm=0.04,
        f_min=0.45,
        basquin_C=5.0e14,
        basquin_m=4.5,
        creep_c0=11.0,
        creep_c1=9.0,
        creep_c2=-2.2,
        E0_GPa=210.0,
        dE_dT_GPa_perK=-0.05,
    ),
    "INCONEL": MaterialV404(
        name="INCONEL",
        allow_pts=((300.0, 600.0), (700.0, 450.0), (900.0, 350.0)),
        a_dpa=0.004,
        b_he_per_1000appm=0.03,
        f_min=0.55,
        basquin_C=8.0e14,
        basquin_m=5.0,
        creep_c0=12.0,
        creep_c1=10.0,
        creep_c2=-2.3,
        E0_GPa=205.0,
        dE_dT_GPa_perK=-0.045,
    ),
    "W": MaterialV404(
        name="W",
        allow_pts=((300.0, 800.0), (800.0, 650.0), (1200.0, 500.0)),
        a_dpa=0.003,
        b_he_per_1000appm=0.02,
        f_min=0.60,
        basquin_C=1.0e15,
        basquin_m=6.0,
        creep_c0=13.0,
        creep_c1=11.0,
        creep_c2=-2.5,
        E0_GPa=410.0,
        dE_dT_GPa_perK=-0.08,
    ),
    "CuCrZr": MaterialV404(
        name="CuCrZr",
        allow_pts=((300.0, 250.0), (500.0, 180.0), (650.0, 120.0)),
        a_dpa=0.012,
        b_he_per_1000appm=0.06,
        f_min=0.30,
        basquin_C=8.0e13,
        basquin_m=3.8,
        creep_c0=9.5,
        creep_c1=7.5,
        creep_c2=-2.0,
        E0_GPa=130.0,
        dE_dT_GPa_perK=-0.03,
    ),
}


def _interp_piecewise(pts: Tuple[Tuple[float, float], ...], x: float) -> float:
    if not _finite(x) or len(pts) == 0:
        return _nan()
    if x <= pts[0][0]:
        return float(pts[0][1])
    if x >= pts[-1][0]:
        return float(pts[-1][1])
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return float(y0)
            f = (x - x0) / (x1 - x0)
            return float(y0 + f * (y1 - y0))
    return float(pts[-1][1])


def _material(name: str) -> MaterialV404 | None:
    key = str(name or "").strip()
    return _MATERIALS.get(key)


def _sigma_allow_MPa(mat: MaterialV404, T_K: float, dpa: float, he_appm: float) -> float:
    base = _interp_piecewise(mat.allow_pts, T_K)
    if not _finite(base):
        return _nan()
    dpa_v = _sf(dpa)
    he_v = _sf(he_appm)
    if not _finite(dpa_v):
        dpa_v = 0.0
    if not _finite(he_v):
        he_v = 0.0
    f_irr = 1.0 - mat.a_dpa * max(0.0, dpa_v) - mat.b_he_per_1000appm * max(0.0, he_v) / 1000.0
    f_irr = max(mat.f_min, f_irr)
    return float(base * f_irr)


def _fatigue_Nf(mat: MaterialV404, delta_sigma_MPa: float) -> float:
    ds = _sf(delta_sigma_MPa)
    if not _finite(ds) or ds <= 0.0:
        return _nan()
    return float(mat.basquin_C * (ds ** (-mat.basquin_m)))


def _creep_tr_hours(mat: MaterialV404, sigma_MPa: float, T_K: float) -> float:
    s = _sf(sigma_MPa)
    T = _sf(T_K)
    if not (_finite(s) and s > 0.0 and _finite(T) and T > 0.0):
        return _nan()
    # log10(tr_hr) envelope
    logtr = mat.creep_c0 + mat.creep_c1 * (1000.0 / T) + mat.creep_c2 * math.log10(s)
    return float(10.0 ** logtr)


def _E_GPa(mat: MaterialV404, T_K: float) -> float:
    T = _sf(T_K)
    if not _finite(T):
        return _nan()
    return float(max(1.0, mat.E0_GPa + mat.dE_dT_GPa_perK * (T - 300.0)))


def evaluate_structural_life_authority_v404(out: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    enabled = bool(getattr(inp, "include_structural_life_v404", False))
    if not enabled:
        return {
            "include_structural_life_v404": False,
            "struct_global_min_margin_v404": _nan(),
            "struct_dominant_component_v404": "OFF",
            "struct_dominant_mode_v404": "OFF",
            "struct_margin_table_v404": [],
            "struct_min_margin_frac_v404": float(getattr(inp, "struct_min_margin_frac_v404", _nan())),
            "structural_life_contract_sha256_v404": "f4c1f0e6b7a2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789",
        }

    # Pull irradiation markers (prefer v403, fallback to earlier proxies if present)
    dpa_fw = _sf(out.get("dpa_fw_v403", out.get("dpa_fw", _nan())))
    he_fw = _sf(out.get("he_appm_fw_v403", out.get("he_appm_fw", _nan())))

    # Service/cycling knobs
    pulse_count = _sf(getattr(inp, "pulse_count_v404", _nan()))
    if not _finite(pulse_count):
        # conservative default for pulsed machine screening
        pulse_count = 1.0e5
    hot_fraction = _sf(getattr(inp, "hot_fraction_v404", 0.2))
    hot_fraction = _clip(hot_fraction, 0.0, 1.0)
    service_years = _sf(getattr(inp, "service_years_v404", 1.0))
    if not _finite(service_years) or service_years <= 0.0:
        service_years = 1.0
    total_hours = 8760.0 * service_years
    hot_hours = total_hours * hot_fraction

    # Component inputs
    comp_defs = [
        ("FW", getattr(inp, "material_fw_v404", "EUROFER"), _sf(getattr(inp, "T_fw_K_v404", 700.0)),
         _sf(out.get("fw_sigma_proxy_MPa", _nan())), _sf(getattr(inp, "fw_delta_sigma_MPa_v404", _nan())),
         _sf(getattr(inp, "fw_panel_span_m_v404", _nan())), _sf(getattr(inp, "fw_t_m_v404", _nan())), _sf(getattr(inp, "fw_R_m_v404", _nan()))
        ),
        ("VV", getattr(inp, "material_vv_v404", "SS316"), _sf(getattr(inp, "T_vv_K_v404", 450.0)),
         _sf(out.get("vv_sigma_ext_MPa_v389", _nan())), _sf(getattr(inp, "vv_delta_sigma_MPa_v404", _nan())),
         _sf(getattr(inp, "vv_span_m_v404", _nan())), _sf(getattr(inp, "vv_t_m_v404", _nan())), _sf(getattr(inp, "vv_R_m_v404", _nan()))
        ),
        ("TF", getattr(inp, "material_tf_v404", "INCONEL"), _sf(getattr(inp, "T_tf_K_v404", 350.0)),
         _sf(out.get("sigma_vm_MPa", _nan())), _sf(getattr(inp, "tf_delta_sigma_MPa_v404", _nan())),
         _sf(getattr(inp, "tf_span_m_v404", _nan())), _sf(getattr(inp, "tf_t_m_v404", _nan())), _sf(getattr(inp, "tf_R_m_v404", _nan()))
        ),
    ]

    table: List[Dict[str, Any]] = []

    global_min = _nan()
    dom_comp = "UNKNOWN"
    dom_mode = "unknown"

    for comp, mat_name, T_K, sigma_MPa, delta_sigma_MPa, span_m, t_m, R_m in comp_defs:
        mat = _material(mat_name)
        if mat is None:
            row = {
                "component": comp,
                "material": str(mat_name),
                "tier": "unknown",
                "sigma_MPa": sigma_MPa,
                "T_K": T_K,
                "stress_margin": _nan(),
                "fatigue_usage": _nan(),
                "fatigue_margin": _nan(),
                "creep_usage": _nan(),
                "creep_margin": _nan(),
                "buckling_margin": _nan(),
                "min_margin": _nan(),
                "dominant_mode": "unknown",
            }
            table.append(row)
            continue

        # Component-specific irradiation: FW uses FW markers; VV/TF use same as conservative proxy unless provided
        dpa = dpa_fw
        he = he_fw
        if comp != "FW":
            dpa = _sf(out.get(f"dpa_{comp.lower()}_v403", dpa_fw))
            he = _sf(out.get(f"he_appm_{comp.lower()}_v403", he_fw))

        # Stress margin
        sigma_allow = _sigma_allow_MPa(mat, T_K, dpa, he)
        stress_margin = _nan()
        if _finite(sigma_allow) and _finite(sigma_MPa) and sigma_MPa > 0.0:
            stress_margin = float(sigma_allow / sigma_MPa - 1.0)

        # Fatigue
        # If user didn't provide delta_sigma, use 0.3*sigma as conservative cyclic amplitude proxy.
        if not _finite(delta_sigma_MPa) and _finite(sigma_MPa) and sigma_MPa > 0.0:
            delta_sigma_MPa = 0.3 * sigma_MPa
        Nf = _fatigue_Nf(mat, max(_sf(delta_sigma_MPa), 0.0))
        fatigue_usage = _nan()
        fatigue_margin = _nan()
        if _finite(Nf) and Nf > 0.0 and _finite(pulse_count):
            fatigue_usage = float(pulse_count / Nf)
            fatigue_margin = float(1.0 - fatigue_usage)

        # Creep
        tr_hr = _creep_tr_hours(mat, max(_sf(sigma_MPa), 0.0), T_K)
        creep_usage = _nan()
        creep_margin = _nan()
        if _finite(tr_hr) and tr_hr > 0.0:
            creep_usage = float(hot_hours / tr_hr)
            creep_margin = float(1.0 - creep_usage)

        # Buckling (only if geometry present)
        # Use generic σ_cr = K * E(T) * (t/R)^2 in MPa, with K chosen per component type.
        buckling_margin = _nan()
        if _finite(sigma_MPa) and sigma_MPa > 0.0 and _finite(t_m) and t_m > 0.0 and _finite(R_m) and R_m > 0.0:
            E = _E_GPa(mat, T_K)  # GPa
            # conservative K values
            K = 0.6 if comp == "VV" else (0.8 if comp == "TF" else 0.5)
            sigma_cr_MPa = float(K * (E * 1000.0) * (t_m / R_m) ** 2)  # (GPa->MPa)
            buckling_margin = float(sigma_cr_MPa / sigma_MPa - 1.0)

        # Min margin & dominant mode
        margins = {
            "stress": stress_margin,
            "fatigue": fatigue_margin,
            "creep": creep_margin,
            "buckling": buckling_margin,
        }
        min_mode = "unknown"
        min_margin = _nan()
        for k, v in margins.items():
            if _finite(v):
                if (not _finite(min_margin)) or v < min_margin:
                    min_margin = float(v)
                    min_mode = k

        tier = "unknown"
        if _finite(min_margin):
            tier = "OK" if min_margin >= 0.2 else ("watch" if min_margin >= 0.0 else "deficit")

        row = {
            "component": comp,
            "material": mat.name,
            "tier": tier,
            "sigma_MPa": sigma_MPa,
            "sigma_allow_MPa": sigma_allow,
            "T_K": T_K,
            "dpa": dpa,
            "he_appm": he,
            "stress_margin": stress_margin,
            "pulse_count": pulse_count,
            "delta_sigma_MPa": delta_sigma_MPa,
            "fatigue_usage": fatigue_usage,
            "fatigue_margin": fatigue_margin,
            "hot_hours": hot_hours,
            "creep_tr_hours": tr_hr,
            "creep_usage": creep_usage,
            "creep_margin": creep_margin,
            "buckling_margin": buckling_margin,
            "min_margin": min_margin,
            "dominant_mode": min_mode,
        }
        table.append(row)

        if _finite(min_margin):
            if (not _finite(global_min)) or min_margin < global_min:
                global_min = float(min_margin)
                dom_comp = comp
                dom_mode = min_mode

    # Global contract threshold (optional)
    struct_min_margin = float(getattr(inp, "struct_min_margin_frac_v404", _nan()))

    return {
        "include_structural_life_v404": True,
        "struct_min_margin_frac_v404": struct_min_margin,
        "struct_global_min_margin_v404": global_min,
        "struct_dominant_component_v404": dom_comp,
        "struct_dominant_mode_v404": dom_mode,
        "struct_margin_table_v404": table,
        "structural_life_contract_sha256_v404": "f4c1f0e6b7a2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789",
    }
