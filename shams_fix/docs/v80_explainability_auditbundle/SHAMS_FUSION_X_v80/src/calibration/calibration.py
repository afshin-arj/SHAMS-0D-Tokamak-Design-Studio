from __future__ import annotations
from typing import Any, Dict

from calibration.registry import CalibrationRegistry, default_registry


def apply_calibration(outputs: Dict[str, Any], calib: Dict[str, Any] | None) -> Dict[str, Any]:
    """Apply transparent multiplicative calibration factors to outputs.

    Backward compatible:
    - if calib is a flat dict {key: factor}, it is accepted.
    - if calib looks like a registry dict ({'name':..., 'factors':...}), it is accepted.

    Always records what was applied under `outputs['calibration_applied']`.
    """
    if not isinstance(outputs, dict):
        return outputs

    out = dict(outputs)

    # Parse calibration input
    factors: Dict[str, float] = {}
    reg_meta: Dict[str, Any] = {}

    if isinstance(calib, dict) and "factors" in calib and isinstance(calib.get("factors"), dict):
        # registry-like
        reg = CalibrationRegistry.from_dict(calib)
        factors = reg.select_factors(out.get("_inputs", {})) if isinstance(out.get("_inputs"), dict) else {k: float(v.factor) for k,v in (reg.factors or {}).items()}
        reg_meta = {"name": reg.name, "created_unix": reg.created_unix}
    elif isinstance(calib, dict):
        factors = {k: float(v) for k, v in calib.items() if isinstance(v, (int, float))}

    if not factors:
        # default: no change
        factors = {}

    f_conf = float(factors.get("confinement", 1.0) or 1.0)
    f_div = float(factors.get("divertor", 1.0) or 1.0)
    f_bs = float(factors.get("bootstrap", 1.0) or 1.0)

    # Confinement-like fields
    for k in ("H98y2", "H98", "tau_E_s", "P_aux_MW_required"):
        if k in out:
            try:
                out[k] = float(out[k]) * f_conf
            except Exception:
                pass

    # Bootstrap-like fields
    for k in ("f_bs", "I_bs_MA"):
        if k in out:
            try:
                out[k] = float(out[k]) * f_bs
            except Exception:
                pass

    # Divertor / exhaust-like fields
    for k in ("q_div_MW_m2", "q_peak_MW_m2", "q_div_est_MW_m2"):
        if k in out:
            try:
                out[k] = float(out[k]) * f_div
            except Exception:
                pass

    out["calibration_applied"] = {
        "factors": {"confinement": f_conf, "divertor": f_div, "bootstrap": f_bs},
        "registry": reg_meta,
    }
    return out
