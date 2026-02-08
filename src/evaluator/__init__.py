"""Evaluator layer (PROCESS-inspired).

This package defines the *single* choke-point between solvers and the SHAMS
physics/models.

Design intent:
  - Solvers call an Evaluator (x -> outputs, residuals, diagnostics)
  - The Evaluator calls the physics/model stack
  - UI, studies, and batch runners also call the Evaluator for consistency

Keeping this seam clean makes solver upgrades, Jacobian improvements,
diagnostics, and validation much easier.
"""

from .core import Evaluator, EvalResult

__all__ = ["Evaluator", "EvalResult"]

from .derivatives import register_derivative, get_derivative

# -----------------------------------------------------------------------------
# Minimal semi-analytic Jacobian hooks (opt-in via Evaluator.jacobian_targets).
# These are intentionally small, transparent derivatives for the stiffest knobs.
# Finite-difference fallback remains for all other (target,var) pairs.
# -----------------------------------------------------------------------------
try:
    import math

    def _dH98_d_confinement_mult(inp, out):
        cm = float(getattr(inp, "confinement_mult", 1.0) or 0.0)
        if cm <= 0.0:
            return 0.0
        H98 = float(out.get("H98", 0.0))
        return H98 / cm if math.isfinite(H98) else 0.0

    def _dQ_d_Paux(inp, out):
        Paux = float(getattr(inp, "Paux_MW", 0.0) or 0.0)
        Q = float(out.get("Q_DT_eqv", 0.0))
        if Paux <= 0.0 or not math.isfinite(Q):
            return 0.0
        return -Q / Paux

    register_derivative("H98", "confinement_mult", _dH98_d_confinement_mult)
    register_derivative("Q_DT_eqv", "Paux_MW", _dQ_d_Paux)

    def _dPsol_d_Paux(inp, out):
        # P_SOL = Pin - Prad_core. Pin = Paux + Palpha (legacy).
        # If radiation is a fixed fraction of Pin, then dPsol/dPaux = (1 - f_rad_core).
        rad_model = str(getattr(inp, "radiation_model", "fraction") or "fraction").lower()
        if rad_model in ("fraction", "fractional"):
            f = float(getattr(inp, "f_rad_core", 0.0) or 0.0)
            f = min(max(f, 0.0), 0.95)
            return 1.0 - f
        return 1.0

    def _dPsol_over_R_d_Paux(inp, out):
        R0 = float(getattr(inp, "R0_m", 0.0) or 0.0)
        if R0 <= 0.0:
            return 0.0
        return _dPsol_d_Paux(inp, out) / R0

    def _dqmid_d_Paux(inp, out):
        # q_midplane = P_SOL / (2π R0 λq)
        R0 = float(getattr(inp, "R0_m", 0.0) or 0.0)
        lam_m = float(getattr(inp, "lambda_q_m", 0.0) or 0.0)
        if R0 <= 0.0 or lam_m <= 0.0:
            return 0.0
        return _dPsol_d_Paux(inp, out) / (2.0 * math.pi * R0 * lam_m)

    def _d_power_balance_resid_d_Paux(inp, out):
        # power_balance_residual = Pin - (Prad_core + P_SOL) = 0 by definition in this closure.
        # As a diagnostic, treat derivative as 0 to avoid introducing stiffness.
        return 0.0

    register_derivative("P_SOL_MW", "Paux_MW", _dPsol_d_Paux)
    register_derivative("P_SOL_over_R_MW_m", "Paux_MW", _dPsol_over_R_d_Paux)
    register_derivative("q_midplane_MW_m2", "Paux_MW", _dqmid_d_Paux)
    register_derivative("power_balance_residual_MW", "Paux_MW", _d_power_balance_resid_d_Paux)
except Exception:
    pass
