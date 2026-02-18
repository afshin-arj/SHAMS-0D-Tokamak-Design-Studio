"""SHAMS v378.0.0 — Control & Actuation Authority (PF/RWM coupling deepening).

Deterministic, governance-only certification derived from *frozen* Systems outputs.

Hard laws:
 - No solvers, no iteration, no relaxation.
 - Same inputs -> same outputs.
 - Certification does not modify truth.

This module intentionally operates on *already-produced* Systems artifacts.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


def _isfinite(x: Any) -> bool:
    try:
        import math

        return math.isfinite(float(x))
    except Exception:
        return False


def _safe_float(d: Dict[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        v = d.get(key, default)
        return float(v)
    except Exception:
        return float(default)


def _hash_inputs(inputs: Dict[str, Any]) -> str:
    """Stable SHA-256 of inputs dict."""
    try:
        payload = json.dumps(inputs, sort_keys=True, default=str).encode("utf-8")
    except Exception:
        payload = repr(inputs).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class ActuationCaps:
    """User-visible caps for actuator authority.

    These are *not* truth parameters. They are governance assumptions used to
    compute margins (caps - required)/caps.
    """

    vs_bandwidth_cap_Hz: float = 300.0
    vs_power_cap_MW: float = 50.0
    pf_power_cap_MW: float = 200.0
    rwm_power_cap_MW: float = 20.0
    rwm_power_ref_MW: float = 10.0


def _margin(cap: float, req: float) -> float:
    if not (_isfinite(cap) and _isfinite(req) and cap > 0.0):
        return float("nan")
    return (cap - req) / cap


def _tier(m: float, warn: float = 0.10, ok: float = 0.25) -> str:
    """Classify margin tiers."""
    if not _isfinite(m):
        return "UNAVAILABLE"
    if m < 0.0:
        return "BLOCK"
    if m < warn:
        return "TIGHT"
    if m < ok:
        return "OK"
    return "ROBUST"


def certify_control_actuation(
    *,
    outputs: Dict[str, Any],
    inputs: Dict[str, Any],
    run_id: Optional[str] = None,
    inputs_hash: Optional[str] = None,
    caps: Optional[ActuationCaps] = None,
) -> Dict[str, Any]:
    """Compute v378 actuation authority certification.

    Parameters
    ----------
    outputs:
        Frozen truth outputs (Systems artifact outputs dict).
    inputs:
        Inputs dict (Systems artifact inputs dict).
    caps:
        Governance caps used for margins.

    Returns
    -------
    dict
        Certification JSON-serializable payload.
    """

    caps = caps or ActuationCaps()

    # We prefer to reuse the already-existing v374 stability/control certification logic
    # to avoid duplicating implicit key mappings from truth outputs.
    # This is still deterministic and solver-free.
    stability_cert: Optional[Dict[str, Any]] = None
    try:
        from src.certification.stability_control_certification_v374 import (
            certify_stability_control_margin,
        )

        stability_cert = certify_stability_control_margin(
            outputs=outputs,
            inputs=inputs,
            run_id=run_id,
            inputs_hash=inputs_hash,
            eps_active=0.15,
            eps_tight=0.25,
            probe_frac=0.01,
        )
    except Exception:
        stability_cert = None

    vs_blk = (stability_cert or {}).get("vertical_stability", {}) if isinstance(stability_cert, dict) else {}
    vb = (stability_cert or {}).get("volt_seconds", {}) if isinstance(stability_cert, dict) else {}
    rwm = (stability_cert or {}).get("rwm", {}) if isinstance(stability_cert, dict) else {}

    vs_bw_req = float(vs_blk.get("vs_bandwidth_req_Hz")) if _isfinite(vs_blk.get("vs_bandwidth_req_Hz")) else float("nan")
    vs_P_req = float(vs_blk.get("vs_control_power_req_MW")) if _isfinite(vs_blk.get("vs_control_power_req_MW")) else float("nan")

    cs_req = float(vb.get("cs_flux_required_Wb")) if _isfinite(vb.get("cs_flux_required_Wb")) else float("nan")
    cs_av = float(vb.get("cs_flux_available_Wb")) if _isfinite(vb.get("cs_flux_available_Wb")) else float("nan")
    V_loop_ramp = float(vb.get("V_loop_ramp_V")) if _isfinite(vb.get("V_loop_ramp_V")) else float("nan")
    V_loop_cap = float(vb.get("cs_V_loop_max_V")) if _isfinite(vb.get("cs_V_loop_max_V")) else float("nan")

    cs_margin = float("nan")
    if _isfinite(cs_req) and _isfinite(cs_av) and abs(cs_req) > 0.0:
        cs_margin = (cs_av - cs_req) / max(cs_req, 1e-12)

    V_loop_margin = float("nan")
    if _isfinite(V_loop_ramp) and _isfinite(V_loop_cap) and V_loop_cap > 0.0:
        V_loop_margin = (V_loop_cap - V_loop_ramp) / V_loop_cap

    # RWM power requirement proxy: demand increases as chi exceeds 1.
    # This is governance-only (no MHD solver). The mapping is explicit and tunable via rwm_power_ref_MW.
    rwm_chi = float(rwm.get("chi")) if _isfinite(rwm.get("chi")) else float("nan")
    rwm_req_P = float("nan")
    if _isfinite(rwm_chi):
        rwm_req_P = float(caps.rwm_power_ref_MW) * max(0.0, float(rwm_chi) - 1.0)

    # PF power requirement proxy: include VS control power and ramp-loop power proxy if present.
    # If VS power is unavailable, PF requirement falls back to NaN (UNAVAILABLE tier).
    pf_req_P = float("nan")
    if _isfinite(vs_P_req):
        pf_req_P = float(vs_P_req)

    # Margins
    m_vs_bw = _margin(float(caps.vs_bandwidth_cap_Hz), vs_bw_req)
    m_vs_P = _margin(float(caps.vs_power_cap_MW), vs_P_req)
    m_pf_P = _margin(float(caps.pf_power_cap_MW), pf_req_P)
    m_rwm_P = _margin(float(caps.rwm_power_cap_MW), rwm_req_P)

    # Aggregate
    # Conservative: take the minimum finite margin across the core actuator set.
    finite_margins = [m for m in [m_vs_bw, m_vs_P, m_pf_P, m_rwm_P, cs_margin, V_loop_margin] if _isfinite(m)]
    m_min = min(finite_margins) if finite_margins else float("nan")

    ih = str(inputs_hash or outputs.get("inputs_hash") or _hash_inputs(inputs))

    return {
        "schema": "systems_control_actuation_certification",
        "schema_version": 1,
        "cert_version": "v378.0",
        "run_id": run_id,
        "inputs_hash": ih,
        "timestamp_utc": _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "caps": {
            "vs_bandwidth_cap_Hz": float(caps.vs_bandwidth_cap_Hz),
            "vs_power_cap_MW": float(caps.vs_power_cap_MW),
            "pf_power_cap_MW": float(caps.pf_power_cap_MW),
            "rwm_power_cap_MW": float(caps.rwm_power_cap_MW),
            "rwm_power_ref_MW": float(caps.rwm_power_ref_MW),
        },
        "requirements": {
            "vs_bandwidth_req_Hz": float(vs_bw_req) if _isfinite(vs_bw_req) else float("nan"),
            "vs_control_power_req_MW": float(vs_P_req) if _isfinite(vs_P_req) else float("nan"),
            "pf_power_req_MW": float(pf_req_P) if _isfinite(pf_req_P) else float("nan"),
            "rwm_chi": float(rwm_chi) if _isfinite(rwm_chi) else float("nan"),
            "rwm_power_req_MW_proxy": float(rwm_req_P) if _isfinite(rwm_req_P) else float("nan"),
            "cs_flux_required_Wb": float(cs_req) if _isfinite(cs_req) else float("nan"),
            "cs_flux_available_Wb": float(cs_av) if _isfinite(cs_av) else float("nan"),
            "V_loop_ramp_V": float(V_loop_ramp) if _isfinite(V_loop_ramp) else float("nan"),
            "cs_V_loop_max_V": float(V_loop_cap) if _isfinite(V_loop_cap) else float("nan"),
        },
        "margins": {
            "vs_bandwidth_margin": float(m_vs_bw) if _isfinite(m_vs_bw) else float("nan"),
            "vs_power_margin": float(m_vs_P) if _isfinite(m_vs_P) else float("nan"),
            "pf_power_margin": float(m_pf_P) if _isfinite(m_pf_P) else float("nan"),
            "rwm_power_margin": float(m_rwm_P) if _isfinite(m_rwm_P) else float("nan"),
            "cs_flux_margin": float(cs_margin) if _isfinite(cs_margin) else float("nan"),
            "V_loop_margin": float(V_loop_margin) if _isfinite(V_loop_margin) else float("nan"),
            "min_margin": float(m_min) if _isfinite(m_min) else float("nan"),
        },
        "tiers": {
            "vs_bandwidth": _tier(m_vs_bw),
            "vs_power": _tier(m_vs_P),
            "pf_power": _tier(m_pf_P),
            "rwm_power": _tier(m_rwm_P),
            "volt_seconds": _tier(cs_margin),
            "V_loop": _tier(V_loop_margin),
            "overall": _tier(m_min),
        },
        "notes": {
            "scope": "Deterministic, algebraic actuator authority derived from frozen truth outputs. Not a PF/RWM dynamic simulation.",
            "rwm_power_proxy": "P_rwm_req = rwm_power_ref_MW * max(0, chi - 1). Tunable governance mapping.",
        },
    }


def certification_table_rows(cert: Dict[str, Any]) -> Tuple[list, list]:
    rows = []
    cols = ["component", "metric", "value", "units", "tier"]

    req = cert.get("requirements", {}) if isinstance(cert, dict) else {}
    mar = cert.get("margins", {}) if isinstance(cert, dict) else {}
    tiers = cert.get("tiers", {}) if isinstance(cert, dict) else {}

    rows.append({"component": "VS", "metric": "bandwidth_req", "value": req.get("vs_bandwidth_req_Hz"), "units": "Hz", "tier": tiers.get("vs_bandwidth")})
    rows.append({"component": "VS", "metric": "bandwidth_margin", "value": mar.get("vs_bandwidth_margin"), "units": "-", "tier": tiers.get("vs_bandwidth")})
    rows.append({"component": "VS", "metric": "power_req", "value": req.get("vs_control_power_req_MW"), "units": "MW", "tier": tiers.get("vs_power")})
    rows.append({"component": "VS", "metric": "power_margin", "value": mar.get("vs_power_margin"), "units": "-", "tier": tiers.get("vs_power")})

    rows.append({"component": "PF", "metric": "power_req", "value": req.get("pf_power_req_MW"), "units": "MW", "tier": tiers.get("pf_power")})
    rows.append({"component": "PF", "metric": "power_margin", "value": mar.get("pf_power_margin"), "units": "-", "tier": tiers.get("pf_power")})

    rows.append({"component": "RWM", "metric": "chi", "value": req.get("rwm_chi"), "units": "-", "tier": tiers.get("rwm_power")})
    rows.append({"component": "RWM", "metric": "power_req_proxy", "value": req.get("rwm_power_req_MW_proxy"), "units": "MW", "tier": tiers.get("rwm_power")})
    rows.append({"component": "RWM", "metric": "power_margin", "value": mar.get("rwm_power_margin"), "units": "-", "tier": tiers.get("rwm_power")})

    rows.append({"component": "CS", "metric": "cs_flux_margin", "value": mar.get("cs_flux_margin"), "units": "-", "tier": tiers.get("volt_seconds")})
    rows.append({"component": "CS", "metric": "V_loop_margin", "value": mar.get("V_loop_margin"), "units": "-", "tier": tiers.get("V_loop")})
    rows.append({"component": "overall", "metric": "min_margin", "value": mar.get("min_margin"), "units": "-", "tier": tiers.get("overall")})

    return rows, cols
