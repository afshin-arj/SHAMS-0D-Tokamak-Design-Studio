from __future__ import annotations

"""Structural Stress Authority (v389.0.0)

Deterministic, algebraic structural stress / margin proxies intended for
feasibility-first screening and audit-friendly reporting.

Scope (v389)
------------
- TF inner-leg von Mises stress proxy (uses existing sigma_vm_MPa from truth stack)
- Central solenoid / PF structural stress proxy (magnetic pressure thin-shell)
- Vacuum vessel external pressure stress proxy (thin-shell)
- Margin ledger entries with dominant driver attribution

Hard rules
----------
- No iteration, no solvers, no stochastic elements.
- No mutation of upstream physics outputs; this authority only derives additional
  metrics and optional feasibility constraints.

Units
-----
- Stress: MPa
- Pressure: MPa
- Length: m
- Margins: dimensionless (allowable / applied)

Validity
--------
These are order-of-magnitude screening proxies, not detailed finite-element
mechanics. They should be interpreted as *governance signals*.
"""

from dataclasses import dataclass
import math
from typing import Dict, List, Optional

MU0 = 4e-7 * math.pi


def magnetic_pressure_MPa(B_T: float) -> float:
    """Magnetic pressure p = B^2/(2*mu0), returned in MPa."""
    if not math.isfinite(B_T):
        return float("nan")
    return (B_T * B_T) / (2.0 * MU0) / 1e6


def thin_shell_stress_MPa(p_MPa: float, R_m: float, t_m: float) -> float:
    """Thin-shell hoop stress proxy sigma ~ p * R / t (MPa)."""
    if not (math.isfinite(p_MPa) and math.isfinite(R_m) and math.isfinite(t_m)):
        return float("nan")
    t = max(float(t_m), 1e-6)
    R = max(float(R_m), 1e-6)
    return float(p_MPa) * R / t


def safe_margin(allow_MPa: float, applied_MPa: float) -> float:
    if not (math.isfinite(allow_MPa) and math.isfinite(applied_MPa)):
        return float("nan")
    if applied_MPa <= 0.0:
        return float("inf")
    return float(allow_MPa) / float(applied_MPa)


@dataclass(frozen=True)
class MarginLedgerEntry:
    component: str
    applied_MPa: float
    allowable_MPa: float
    margin: float
    driver: str
    notes: str = ""


def compute_structural_stress_bundle_v389(out: Dict[str, float], inp: object) -> Dict[str, object]:
    """Compute v389 structural stress proxies + margin ledger.

    This function is safe to call even if inputs are incomplete; missing values
    propagate as NaN and constraints are omitted upstream.

    Returns
    -------
    Dict[str, object]
      - scalar outputs (stress/margins/minima)
      - a 'structural_margin_ledger_v389' list of dict entries
    """
    include = bool(getattr(inp, "include_structural_stress_v389", False))
    if not include:
        # Return NaNs so constraints are omitted and UI doesn't show certified blocks unless enabled
        return {
            "include_structural_stress_v389": False,
            "tf_struct_margin_v389": float("nan"),
            "tf_struct_margin_min_v389": float(getattr(inp, "tf_struct_margin_min_v389", float("nan"))),
            "cs_struct_margin_v389": float("nan"),
            "cs_struct_margin_min_v389": float(getattr(inp, "cs_struct_margin_min_v389", float("nan"))),
            "vv_struct_margin_v389": float("nan"),
            "vv_struct_margin_min_v389": float(getattr(inp, "vv_struct_margin_min_v389", float("nan"))),
            "cs_sigma_proxy_MPa_v389": float("nan"),
            "vv_sigma_ext_MPa_v389": float("nan"),
            "structural_margin_ledger_v389": [],
        }

    ledger: List[MarginLedgerEntry] = []

    # --- TF coil ---
    sigma_tf = float(out.get("sigma_vm_MPa", float("nan")))
    sigma_tf_allow = float(out.get("sigma_allow_MPa", float(getattr(inp, "sigma_allow_MPa", float("nan")))))
    tf_margin = safe_margin(sigma_tf_allow, sigma_tf)
    ledger.append(MarginLedgerEntry(
        component="TF inner-leg (von Mises proxy)",
        applied_MPa=sigma_tf,
        allowable_MPa=sigma_tf_allow,
        margin=tf_margin,
        driver="B_peak_T / t_tf_struct_m",
        notes="Uses sigma_vm_MPa from magnet proxy; thin-shell pR/t mapping.",
    ))

    # --- CS / PF proxy ---
    # Use cs_Bmax_T and estimated CS radius and structural thickness.
    cs_Bmax_T = float(getattr(inp, "cs_Bmax_T", float("nan")))
    cs_radius_factor = float(getattr(inp, "cs_radius_factor", float("nan")))
    R0 = float(getattr(inp, "R0_m", float("nan")))
    R_cs = cs_radius_factor * R0 if (math.isfinite(cs_radius_factor) and math.isfinite(R0)) else float("nan")
    t_cs = float(getattr(inp, "t_cs_struct_m_v389", float("nan")))
    p_cs_MPa = magnetic_pressure_MPa(cs_Bmax_T)
    sigma_cs = thin_shell_stress_MPa(p_cs_MPa, R_cs, t_cs)
    sigma_cs_allow = float(getattr(inp, "sigma_cs_allow_MPa_v389", float("nan")))
    cs_margin = safe_margin(sigma_cs_allow, sigma_cs)
    ledger.append(MarginLedgerEntry(
        component="Central solenoid / PF (pressure proxy)",
        applied_MPa=sigma_cs,
        allowable_MPa=sigma_cs_allow,
        margin=cs_margin,
        driver="cs_Bmax_T / t_cs_struct_m_v389",
        notes="Thin-shell pR/t with p=B^2/(2μ0); R≈cs_radius_factor*R0.",
    ))

    # --- Vacuum vessel external pressure proxy ---
    # External pressure ~ 1 atm by default (buckling not modeled; this is a stress proxy only).
    p_vv_ext_MPa = float(getattr(inp, "vv_ext_pressure_MPa_v389", 0.101))
    # Vessel radius ~ outboard plasma edge + blanket + vv (proxy)
    a = float(getattr(inp, "a_m", float("nan")))
    R_vv = (R0 + a + float(getattr(inp, "t_blanket_m", 0.0)) + 0.5 * float(getattr(inp, "t_vv_m", 0.0))) if (math.isfinite(R0) and math.isfinite(a)) else float("nan")
    t_vv = float(getattr(inp, "t_vv_m", float("nan")))
    sigma_vv = thin_shell_stress_MPa(p_vv_ext_MPa, R_vv, t_vv)
    sigma_vv_allow = float(getattr(inp, "sigma_vv_allow_MPa_v389", float("nan")))
    vv_margin = safe_margin(sigma_vv_allow, sigma_vv)
    ledger.append(MarginLedgerEntry(
        component="Vacuum vessel (external pressure proxy)",
        applied_MPa=sigma_vv,
        allowable_MPa=sigma_vv_allow,
        margin=vv_margin,
        driver="vv_ext_pressure_MPa_v389 / t_vv_m",
        notes="Thin-shell pR/t; does NOT model buckling." ,
    ))

    # Constraint minima (defaults)
    tf_min = float(getattr(inp, "tf_struct_margin_min_v389", 1.0))
    cs_min = float(getattr(inp, "cs_struct_margin_min_v389", 1.0))
    vv_min = float(getattr(inp, "vv_struct_margin_min_v389", 1.0))

    return {
        "include_structural_stress_v389": True,
        "tf_struct_margin_v389": tf_margin,
        "tf_struct_margin_min_v389": tf_min,
        "cs_sigma_proxy_MPa_v389": sigma_cs,
        "cs_struct_margin_v389": cs_margin,
        "cs_struct_margin_min_v389": cs_min,
        "vv_sigma_ext_MPa_v389": sigma_vv,
        "vv_struct_margin_v389": vv_margin,
        "vv_struct_margin_min_v389": vv_min,
        "structural_margin_ledger_v389": [e.__dict__ for e in ledger],
    }
