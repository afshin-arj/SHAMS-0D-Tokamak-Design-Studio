from __future__ import annotations

"""Stability & Control Margin Certification (v374.0).

Design intent
-------------
Provide a *certification-grade* (audit-ready) post-processing layer that:

* consumes a frozen truth artifact (inputs + outputs)
* computes deterministic stability/control margins and activity classes
* runs small, local, single-step fragility probes (1% perturbations)
* emits a reviewer-friendly JSON dictionary suitable for evidence packs

SHAMS law compliance
-------------------
* No solvers, no iteration, no smoothing.
* Uses only algebraic transformations and single-step finite differences.
* Never mutates truth; outputs are derived and explicitly labeled.

Author: © 2026 Afshin Arjhangmehr
"""

import datetime as _dt
import hashlib
import json
import math
from typing import Any, Dict, Optional, Tuple

from src.physics.control_stability import compute_vertical_stability
from src.physics.mhd_rwm import compute_rwm_screening


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _isfinite(x: float) -> bool:
    return bool(x == x and math.isfinite(x))


def _activity_class(margin: float, eps_active: float, eps_tight: float) -> str:
    if not _isfinite(margin):
        return "UNAVAILABLE"
    if margin < 0.0:
        return "BLOCKING"
    if margin <= eps_active:
        return "ACTIVE"
    if margin <= eps_tight:
        return "TIGHT"
    return "LOOSE"


def _hash_inputs(inputs_obj: Any) -> str:
    """Deterministic hash of an inputs object/dict (fallback)."""
    try:
        payload = json.dumps(inputs_obj, sort_keys=True, default=str).encode("utf-8")
    except Exception:
        payload = repr(inputs_obj).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _build_min_out_for_vs(outputs: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "R0_m": outputs.get("R0_m", inputs.get("R0_m")),
        "a_m": outputs.get("a_m", inputs.get("a_m")),
        "kappa": outputs.get("kappa", inputs.get("kappa")),
        "delta": outputs.get("delta", inputs.get("delta")),
        "W_th_MJ": outputs.get("W_th_MJ"),
        "P_fus_total_MW": outputs.get("P_fus_total_MW", outputs.get("Pfus_total_MW")),
    }


def _build_min_out_for_rwm(outputs: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "beta_N": outputs.get("beta_N", outputs.get("betaN_proxy")),
        "betaN_proxy": outputs.get("betaN_proxy"),
        "q95_proxy": outputs.get("q95_proxy", outputs.get("q95")),
        "kappa": outputs.get("kappa", inputs.get("kappa")),
        "delta": outputs.get("delta", inputs.get("delta")),
        "li_proxy": outputs.get("li_proxy", outputs.get("li")),
        "R0_m": outputs.get("R0_m", inputs.get("R0_m")),
        "a_m": outputs.get("a_m", inputs.get("a_m")),
        "pf_magnetic_energy_proxy_MJ": outputs.get("pf_magnetic_energy_proxy_MJ"),
        "pf_E_pulse_MJ": outputs.get("pf_E_pulse_MJ"),
    }


def certify_stability_control_margins(
    *,
    outputs: Dict[str, Any],
    inputs: Dict[str, Any],
    run_id: Optional[str] = None,
    inputs_hash: Optional[str] = None,
    eps_active: float = 0.01,
    eps_tight: float = 0.10,
    probe_frac: float = 0.01,
) -> Dict[str, Any]:
    """Compute a stability/control margin certification dictionary."""

    # --- Baseline channels from truth (if present) ---
    vs_margin = _f(outputs.get("vs_margin"), float("nan"))
    vs_bw_req = _f(outputs.get("vs_bandwidth_req_Hz"), float("nan"))
    vs_P_req = _f(outputs.get("vs_control_power_req_MW"), float("nan"))

    rwm_regime = str(outputs.get("rwm_regime") or "")
    rwm_chi = _f(outputs.get("rwm_chi"), float("nan"))
    rwm_ok = bool(outputs.get("rwm_control_ok", True))

    # PF/CS flux swing (Volt-seconds proxy)
    cs_req = _f(outputs.get("cs_flux_required_Wb"), float("nan"))
    cs_av = _f(outputs.get("cs_flux_available_Wb"), float("nan"))
    cs_margin = _f(outputs.get("cs_flux_margin"), float("nan"))
    V_loop_ramp = _f(outputs.get("cs_V_loop_ramp_V"), float("nan"))
    V_loop_cap = _f(inputs.get("cs_V_loop_max_V"), float("nan"))

    if (not _isfinite(cs_margin)) and _isfinite(cs_req) and _isfinite(cs_av):
        cs_margin = (cs_av - cs_req) / max(cs_req, 1e-12)

    # If the truth artifact doesn't carry explicit RWM regime/chi, infer deterministically.
    try:
        class _Inp:
            pass

        _inp = _Inp()
        for k, v in (inputs or {}).items():
            try:
                setattr(_inp, k, v)
            except Exception:
                continue

        if (not rwm_regime) or (not _isfinite(rwm_chi)):
            rwm = compute_rwm_screening(_build_min_out_for_rwm(outputs, inputs), _inp)
            rwm_regime = rwm.regime
            rwm_chi = float(rwm.chi)
            if "rwm_control_ok" not in outputs:
                rwm_ok = (rwm.regime in {"NO_WALL_STABLE", "RWM_ACTIVE"})
    except Exception:
        pass

    # Activity states
    vs_state = _activity_class(vs_margin, eps_active, eps_tight)
    rwm_margin = (1.0 - rwm_chi) if _isfinite(rwm_chi) else float("nan")
    rwm_state = _activity_class(rwm_margin, eps_active, eps_tight)
    cs_state = _activity_class(cs_margin, eps_active, eps_tight)

    # Fragility probes (single-step, optional)
    probes: Dict[str, Any] = {}
    try:
        class _Inp2:
            pass

        _inp2 = _Inp2()
        for k, v in (inputs or {}).items():
            try:
                setattr(_inp2, k, v)
            except Exception:
                continue

        # VS probe: kappa +1%
        out_vs = _build_min_out_for_vs(outputs, inputs)
        kappa0 = _f(out_vs.get("kappa"), float("nan"))
        if _isfinite(kappa0):
            out_vs_p = dict(out_vs)
            out_vs_p["kappa"] = kappa0 * (1.0 + probe_frac)
            vs0 = compute_vertical_stability(out_vs, _inp2)
            vs1 = compute_vertical_stability(out_vs_p, _inp2)
            probes["vertical_stability_kappa_plus"] = {
                "probe_frac": float(probe_frac),
                "vs_margin_0": float(vs0.vs_margin),
                "vs_margin_1": float(vs1.vs_margin),
                "delta": float(vs1.vs_margin - vs0.vs_margin)
                if (_isfinite(vs0.vs_margin) and _isfinite(vs1.vs_margin))
                else float("nan"),
            }

        # RWM probe: beta_N +1%
        out_rwm = _build_min_out_for_rwm(outputs, inputs)
        beta0 = _f(out_rwm.get("beta_N"), float("nan"))
        if _isfinite(beta0):
            out_rwm_p = dict(out_rwm)
            out_rwm_p["beta_N"] = beta0 * (1.0 + probe_frac)
            r0 = compute_rwm_screening(out_rwm, _inp2)
            r1 = compute_rwm_screening(out_rwm_p, _inp2)
            probes["rwm_betaN_plus"] = {
                "probe_frac": float(probe_frac),
                "regime_0": str(r0.regime),
                "regime_1": str(r1.regime),
                "chi_0": float(r0.chi) if _isfinite(float(r0.chi)) else float("nan"),
                "chi_1": float(r1.chi) if _isfinite(float(r1.chi)) else float("nan"),
                "delta": float(r1.chi - r0.chi)
                if (_isfinite(float(r0.chi)) and _isfinite(float(r1.chi)))
                else float("nan"),
            }

        # CS flux probe: Ip +1% increases required flux => margin decreases
        if _isfinite(cs_req) and _isfinite(cs_av):
            cs_req_p = cs_req * (1.0 + probe_frac)
            cs_margin_0 = (cs_av - cs_req) / max(cs_req, 1e-12)
            cs_margin_p = (cs_av - cs_req_p) / max(cs_req_p, 1e-12)
            probes["cs_flux_Ip_plus"] = {
                "probe_frac": float(probe_frac),
                "cs_margin_0": float(cs_margin_0),
                "cs_margin_1": float(cs_margin_p),
                "delta": float(cs_margin_p - cs_margin_0),
            }
    except Exception:
        pass

    # Volt-loop cap margin (informational)
    V_loop_margin = float("nan")
    if _isfinite(V_loop_ramp) and _isfinite(V_loop_cap) and V_loop_cap > 0:
        V_loop_margin = (V_loop_cap - V_loop_ramp) / V_loop_cap

    ih = str(inputs_hash or outputs.get("inputs_hash") or _hash_inputs(inputs))

    return {
        "schema": "systems_stability_control_margin_certification",
        "schema_version": 1,
        "cert_version": "v374.0",
        "run_id": run_id,
        "inputs_hash": ih,
        "timestamp_utc": _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "thresholds": {
            "eps_active": float(eps_active),
            "eps_tight": float(eps_tight),
            "probe_frac": float(probe_frac),
        },
        "vertical_stability": {
            "vs_margin": float(vs_margin) if _isfinite(vs_margin) else float("nan"),
            "state": vs_state,
            "vs_bandwidth_req_Hz": float(vs_bw_req) if _isfinite(vs_bw_req) else float("nan"),
            "vs_control_power_req_MW": float(vs_P_req) if _isfinite(vs_P_req) else float("nan"),
        },
        "rwm": {
            "regime": rwm_regime or "UNAVAILABLE",
            "chi": float(rwm_chi) if _isfinite(rwm_chi) else float("nan"),
            "proximity_margin": float(rwm_margin) if _isfinite(rwm_margin) else float("nan"),
            "state": rwm_state,
            "rwm_control_ok": bool(rwm_ok),
        },
        "volt_seconds": {
            "cs_flux_required_Wb": float(cs_req) if _isfinite(cs_req) else float("nan"),
            "cs_flux_available_Wb": float(cs_av) if _isfinite(cs_av) else float("nan"),
            "cs_flux_margin": float(cs_margin) if _isfinite(cs_margin) else float("nan"),
            "state": cs_state,
            "V_loop_ramp_V": float(V_loop_ramp) if _isfinite(V_loop_ramp) else float("nan"),
            "cs_V_loop_max_V": float(V_loop_cap) if _isfinite(V_loop_cap) else float("nan"),
            "V_loop_margin": float(V_loop_margin) if _isfinite(V_loop_margin) else float("nan"),
        },
        "fragility_probes": probes,
        "notes": {
            "scope": "Deterministic, algebraic certification derived from frozen truth outputs. Not a time-domain stability simulation.",
        },
    }


def certification_table_rows(cert: Dict[str, Any]) -> Tuple[list, list]:
    """Return (rows, columns) for UI tables."""
    rows = []
    cols = ["component", "metric", "value", "units", "state"]

    vs = cert.get("vertical_stability", {}) if isinstance(cert, dict) else {}
    rows.append(
        {
            "component": "vertical_stability",
            "metric": "vs_margin",
            "value": vs.get("vs_margin"),
            "units": "-",
            "state": vs.get("state"),
        }
    )
    rows.append(
        {
            "component": "vertical_stability",
            "metric": "vs_bandwidth_req",
            "value": vs.get("vs_bandwidth_req_Hz"),
            "units": "Hz",
            "state": vs.get("state"),
        }
    )
    rows.append(
        {
            "component": "vertical_stability",
            "metric": "vs_control_power_req",
            "value": vs.get("vs_control_power_req_MW"),
            "units": "MW",
            "state": vs.get("state"),
        }
    )

    rwm = cert.get("rwm", {}) if isinstance(cert, dict) else {}
    rows.append({"component": "rwm", "metric": "regime", "value": rwm.get("regime"), "units": "-", "state": rwm.get("state")})
    rows.append({"component": "rwm", "metric": "chi", "value": rwm.get("chi"), "units": "-", "state": rwm.get("state")})
    rows.append({"component": "rwm", "metric": "proximity_margin", "value": rwm.get("proximity_margin"), "units": "-", "state": rwm.get("state")})

    vb = cert.get("volt_seconds", {}) if isinstance(cert, dict) else {}
    rows.append({"component": "volt_seconds", "metric": "cs_flux_margin", "value": vb.get("cs_flux_margin"), "units": "-", "state": vb.get("state")})
    rows.append({"component": "volt_seconds", "metric": "cs_flux_required", "value": vb.get("cs_flux_required_Wb"), "units": "Wb", "state": vb.get("state")})
    rows.append({"component": "volt_seconds", "metric": "cs_flux_available", "value": vb.get("cs_flux_available_Wb"), "units": "Wb", "state": vb.get("state")})
    rows.append({"component": "volt_seconds", "metric": "V_loop_margin", "value": vb.get("V_loop_margin"), "units": "-", "state": vb.get("state")})

    return rows, cols
