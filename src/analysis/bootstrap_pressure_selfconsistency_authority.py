"""Bootstrap & Pressure Self-Consistency Authority (v349).

Deterministic, algebraic check that the reported bootstrap fraction proxy is
consistent with a pressure-derived expectation under the selected bootstrap
proxy model.

No solvers, no iteration.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from typing import Any, Dict, List



def _is_finite(x: Any) -> bool:
    try:
        xf = float(x)
        return xf == xf and abs(xf) < 1.0e300
    except Exception:
        return False


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return default


def evaluate_bootstrap_pressure_selfconsistency_authority(out: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    """Return dict of keys prefixed 'bsp_...'.

    Uses:
      - beta_proxy (dimensionless beta_t)
      - q95_proxy
      - eps = a/R0
      - bootstrap_model (proxy|improved|sauter)
      - profile_f_bootstrap_proxy (reported)

    The expectation is computed algebraically using the same proxy family.
    """
    req: List[str] = list(contract.get("required_terms", []))
    missing = [k for k in req if k not in out or not _is_finite(out.get(k))]
    if missing:
        return {
            "bsp_regime": "unknown",
            "bsp_fragility_class": "UNKNOWN",
            "bsp_min_margin_frac": float("nan"),
            "bsp_top_limiter": "missing_terms",
            "bsp_missing_terms": missing,
        }

    beta = _f(out.get("beta_proxy"))
    q95 = _f(out.get("q95_proxy"))
    eps = _f(out.get("eps"))
    model = str(out.get("bootstrap_model", "proxy") or "proxy").strip().lower()
    f_rep = _f(out.get("profile_f_bootstrap_proxy"))

    beta_p = beta / max(eps, 1.0e-12)

    # grad proxy (optional)
    g = 0.0
    try:
        gp = out.get("profile_grad_proxy")
        if isinstance(gp, dict):
            g = float(gp.get("abs_dlnp_dr@r~0.9", 0.0) or 0.0)
    except Exception:
        g = 0.0

    # Compute expected bootstrap fraction via the selected proxy model.
    try:
        from src.phase1_models import (
            bootstrap_fraction_improved,
            bootstrap_fraction_proxy,
            bootstrap_fraction_sauter_proxy,
        )
    except Exception:
        from phase1_models import (
            bootstrap_fraction_improved,
            bootstrap_fraction_proxy,
            bootstrap_fraction_sauter_proxy,
        )

    f_exp = float("nan")
    if model == "improved":
        f_exp = float(bootstrap_fraction_improved(beta_p, q95, eps))
    elif model == "sauter":
        f_exp = float(bootstrap_fraction_sauter_proxy(beta_p, q95, eps, grad_proxy=g))
    else:
        betaN = _f(out.get("beta_N", out.get("betaN_proxy", float("nan"))))
        if _is_finite(betaN):
            f_exp = float(bootstrap_fraction_proxy(betaN, q95, C_bs=float(out.get("C_bs", 0.15) or 0.15)))

    if not _is_finite(f_exp):
        return {
            "bsp_regime": "unknown",
            "bsp_fragility_class": "UNKNOWN",
            "bsp_min_margin_frac": float("nan"),
            "bsp_top_limiter": "missing_terms_for_proxy",
            "bsp_missing_terms": ["beta_N"],
        }

    d = f_rep - f_exp
    absd = abs(d)

    tol = _f(out.get("bsp_abs_delta_max", contract.get("delta_f_bootstrap_abs_tol_default", 0.08)))
    if not _is_finite(tol) or tol <= 0:
        tol = float(contract.get("delta_f_bootstrap_abs_tol_default", 0.08))

    m = (tol - absd) / max(tol, 1.0e-12)

    fragile_thr = float(contract.get("fragile_margin_frac", 0.05))
    if m < 0:
        frag = "INFEASIBLE"
    elif m < fragile_thr:
        frag = "FRAGILE"
    else:
        frag = "FEASIBLE"

    return {
        "bsp_regime": "checked",
        "bsp_fragility_class": frag,
        "bsp_min_margin_frac": m,
        "bsp_top_limiter": "abs_delta_fbs",
        "bsp_f_bootstrap_reported": f_rep,
        "bsp_f_bootstrap_expected": f_exp,
        "bsp_delta_f_bootstrap": d,
        "bsp_abs_delta_f_bootstrap": absd,
        "bsp_abs_delta_max": tol,
        "bsp_model": model,
        "bsp_beta_p_proxy": beta_p,
        "bsp_grad_proxy": g,
    }
