from __future__ import annotations
"""Guaranteed Safe Domain Shrink (v147)

Goal:
Given a baseline feasible point and a desired set of variables, automatically propose a
*smaller* hyper-rectangle around the baseline that is likely to be certified feasible,
then certify it using v144 interval certification.

This is intentionally conservative and auditable:
- start from user-proposed bounds (or default +-rel around baseline)
- attempt to certify via interval_certificate (corners + random probes)
- if fails: shrink bounds multiplicatively and retry, up to max_iter
- returns a report + the final certified interval certificate (or last failure)

No physics/solver changes; uses feasibility_deepdive.interval_certificate.
"""

from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional
import time, json, hashlib

from tools.feasibility_deepdive import IntervalConfig, interval_certificate

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha(x: Any) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, default=str).encode("utf-8")).hexdigest()

@dataclass
class ShrinkConfig:
    baseline_inputs: Dict[str, Any]
    bounds: Dict[str, Tuple[float, float]]
    shrink_factor: float = 0.85
    max_iter: int = 10
    n_random: int = 40
    seed: int = 0

def _shrink(bounds: Dict[str, Tuple[float,float]], baseline: Dict[str, Any], factor: float) -> Dict[str, Tuple[float,float]]:
    out={}
    for k,(lo,hi) in bounds.items():
        x0=float(baseline.get(k))
        lo=float(lo); hi=float(hi)
        w=(hi-lo)*0.5*float(factor)
        out[k]=(x0-w, x0+w)
    return out

def run_safe_domain_shrink(cfg: ShrinkConfig) -> Dict[str, Any]:
    created=_utc()
    b0=dict(cfg.baseline_inputs or {})
    bounds=dict(cfg.bounds or {})
    hist=[]
    last_cert=None
    ok=False
    for i in range(int(cfg.max_iter)):
        cert = interval_certificate(IntervalConfig(baseline_inputs=b0, bounds=bounds, n_random=int(cfg.n_random), seed=int(cfg.seed)))
        hist.append({"iter": i, "bounds": {k:[float(v[0]), float(v[1])] for k,v in bounds.items()}, "certified": bool(cert.get("verdict",{}).get("interval_certified")), "worst_margin": cert.get("verdict",{}).get("worst_seen_margin_frac"), "worst_constraint": cert.get("verdict",{}).get("worst_seen_constraint")})
        last_cert = cert
        if cert.get("verdict",{}).get("interval_certified") is True:
            ok=True
            break
        bounds = _shrink(bounds, b0, float(cfg.shrink_factor))
    return {
        "kind":"shams_safe_domain_shrink_report",
        "version":"v147",
        "created_utc": created,
        "config": {
            "shrink_factor": float(cfg.shrink_factor),
            "max_iter": int(cfg.max_iter),
            "n_random": int(cfg.n_random),
            "seed": int(cfg.seed),
        },
        "final_certified": bool(ok),
        "history": hist,
        "final_bounds": (hist[-1]["bounds"] if hist else {}),
        "interval_certificate_v144": last_cert,
        "hashes": {
            "report_sha256": _sha(hist),
        }
    }
