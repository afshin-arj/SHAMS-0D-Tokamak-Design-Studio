"""
phase1_hot_ion_ext.py (drop-in wrapper)

This file preserves the original function names used by your Phase-1 scripts,
but delegates implementation to the refactored modules.

If your old tooling imports:
- phase1_hot_ion_point
- solve_fG_for_QDTeqv
- solve_Ip_for_H98_with_Q_match

…those symbols are still available here.
"""

from __future__ import annotations
from typing import Dict, Optional, Tuple

from phase1_core import (
    PointInputs,
    hot_ion_point as _hot_ion_point,
    solve_fG_for_QDTeqv as _solve_fG_for_Q,
    solve_Ip_for_H98_with_Q_match as _solve_Ip_for_H98,
)

def phase1_hot_ion_point(
    R0_m: float,
    a_m: float,
    B0_T: float,
    Ip_MA: float,
    Ti_keV: float,
    f_G: float,
    t_shield_m: float,
    P_aux_MW: float,
    Ti_over_Te: float = 2.0,
    P_aux_for_Q_MW: Optional[float] = None,
    n_override_m3: Optional[float] = None,  # accepted for API-compat; not used in this refactor
    Zeff: float = 1.8,
    dilution_fuel: float = 0.85,
    extra_rad_factor: float = 0.2,
    alpha_loss_frac: float = 0.05,
    kappa: float = 1.8,
    C_bs: float = 0.15,
    require_Hmode: bool = False,
    PLH_margin: float = 0.0,
) -> Dict[str, float]:
    inp = PointInputs(
        R0_m=R0_m, a_m=a_m, kappa=kappa, Bt_T=B0_T,
        Ip_MA=Ip_MA, Ti_keV=Ti_keV, fG=f_G,
        t_shield_m=t_shield_m, Paux_MW=P_aux_MW,
        Ti_over_Te=Ti_over_Te,
        zeff=Zeff, dilution_fuel=dilution_fuel,
        extra_rad_factor=extra_rad_factor, alpha_loss_frac=alpha_loss_frac,
        C_bs=C_bs, require_Hmode=require_Hmode, PLH_margin=PLH_margin,
    )
    return _hot_ion_point(inp, Paux_for_Q_MW=P_aux_for_Q_MW)

def solve_fG_for_QDTeqv(
    target_Q: float,
    R0_m: float,
    a_m: float,
    B0_T: float,
    Ip_MA: float,
    Ti_keV: float,
    t_shield_m: float,
    P_aux_MW: float,
    Ti_over_Te: float = 2.0,
    P_aux_for_Q_MW: Optional[float] = None,
    fG_min: float = 0.01,
    fG_max: float = 1.20,
    tol: float = 1e-3,
    **kwargs,
) -> Tuple[float, Dict[str, float], bool]:
    inp = PointInputs(
        R0_m=R0_m, a_m=a_m, kappa=kwargs.get("kappa", 1.8), Bt_T=B0_T,
        Ip_MA=Ip_MA, Ti_keV=Ti_keV, fG=0.5*(fG_min+fG_max),
        t_shield_m=t_shield_m, Paux_MW=P_aux_MW,
        Ti_over_Te=Ti_over_Te,
        zeff=kwargs.get("Zeff", 1.8),
        dilution_fuel=kwargs.get("dilution_fuel", 0.85),
        extra_rad_factor=kwargs.get("extra_rad_factor", 0.2),
        alpha_loss_frac=kwargs.get("alpha_loss_frac", 0.05),
        C_bs=kwargs.get("C_bs", 0.15),
        require_Hmode=kwargs.get("require_Hmode", False),
        PLH_margin=kwargs.get("PLH_margin", 0.0),
    )
    sol, out, ok = _solve_fG_for_Q(inp, target_Q, fG_min, fG_max, tol, P_aux_for_Q_MW)
    return sol.fG, out, ok

def solve_Ip_for_H98_with_Q_match(
    target_H98: float,
    target_Q: float,
    R0_m: float,
    a_m: float,
    B0_T: float,
    Ti_keV: float,
    t_shield_m: float,
    P_aux_MW: float,
    Ti_over_Te: float = 2.0,
    P_aux_for_Q_MW: Optional[float] = None,
    Ip_min: float = 10.0,
    Ip_max: float = 120.0,
    fG_min: float = 0.01,
    fG_max: float = 1.20,
    tol: float = 1e-3,
    **kwargs,
) -> Tuple[float, float, Dict[str, float], bool]:
    inp = PointInputs(
        R0_m=R0_m, a_m=a_m, kappa=kwargs.get("kappa", 1.8), Bt_T=B0_T,
        Ip_MA=0.5*(Ip_min+Ip_max), Ti_keV=Ti_keV, fG=0.8,
        t_shield_m=t_shield_m, Paux_MW=P_aux_MW,
        Ti_over_Te=Ti_over_Te,
        zeff=kwargs.get("Zeff", 1.8),
        dilution_fuel=kwargs.get("dilution_fuel", 0.85),
        extra_rad_factor=kwargs.get("extra_rad_factor", 0.2),
        alpha_loss_frac=kwargs.get("alpha_loss_frac", 0.05),
        C_bs=kwargs.get("C_bs", 0.15),
        require_Hmode=kwargs.get("require_Hmode", False),
        PLH_margin=kwargs.get("PLH_margin", 0.0),
    )
    sol, out, ok = _solve_Ip_for_H98(inp, target_H98, target_Q, Ip_min, Ip_max, fG_min, fG_max, tol, P_aux_for_Q_MW)
    return sol.Ip_MA, sol.fG, out, ok
