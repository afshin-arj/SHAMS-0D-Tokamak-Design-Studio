from __future__ import annotations

"""v375 Exhaust & Divertor Authority (deterministic).

This is a *governance-grade* hardening layer for SOL/divertor screening in 0-D.

Scope
-----
* Applies explicit bounds (contracted) to the *inputs used* by the divertor proxy:
  - λ_q (mm)
  - divertor flux expansion
  - strike-point count proxy
  - wetted-area utilization (f_wet)
* Provides unit/scale sanity flags (does not modify truth outputs).
* Exports a compact, certified bundle for UI + evidence packs.

Hard laws respected
-------------------
* Deterministic
* No hidden iteration / no solvers
* Frozen evaluator remains the source of truth; this module only makes
  the screening proxies explicit and bounded.

Author: © 2026 Afshin Arjhangmehr
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple


_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT_PATH = _REPO_ROOT / "contracts" / "exhaust_divertor_authority_v375.json"


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()


def _sha256_file(p: Path) -> str:
    return _sha256_bytes(p.read_bytes())


def _load_contract() -> Dict[str, Any]:
    return json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))


CONTRACT: Dict[str, Any] = _load_contract()
CONTRACT_SHA256: str = _sha256_file(_CONTRACT_PATH)


def _clamp(x: float, lo: float, hi: float) -> Tuple[float, str]:
    if x != x:
        return x, "nan"
    if x < lo:
        return lo, "clamped_low"
    if x > hi:
        return hi, "clamped_high"
    return x, "ok"


@dataclass(frozen=True)
class ExhaustAuthorityBundle:
    lambda_q_mm_raw: float
    lambda_q_mm_used: float
    lambda_q_status: str

    flux_expansion_raw: float
    flux_expansion_used: float
    flux_expansion_status: str

    n_strike_points_raw: int
    n_strike_points_used: int

    f_wet_raw: float
    f_wet_used: float
    f_wet_status: str

    q_div_unit_suspect: float
    A_wet_m2: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "exhaust_authority.v375",
            "exhaust_authority_contract_sha256": CONTRACT_SHA256,
            "lambda_q_mm_raw": self.lambda_q_mm_raw,
            "lambda_q_mm_used": self.lambda_q_mm_used,
            "lambda_q_status": self.lambda_q_status,
            "flux_expansion_raw": self.flux_expansion_raw,
            "flux_expansion_used": self.flux_expansion_used,
            "flux_expansion_status": self.flux_expansion_status,
            "n_strike_points_raw": self.n_strike_points_raw,
            "n_strike_points_used": self.n_strike_points_used,
            "f_wet_raw": self.f_wet_raw,
            "f_wet_used": self.f_wet_used,
            "f_wet_status": self.f_wet_status,
            "q_div_unit_suspect": self.q_div_unit_suspect,
            "A_wet_m2": self.A_wet_m2,
        }


def apply_exhaust_authority(
    *,
    lambda_q_mm_raw: float,
    flux_expansion_raw: float,
    n_strike_points_raw: int,
    f_wet_raw: float,
    q_div_MW_m2: float,
    A_wet_m2: float,
) -> ExhaustAuthorityBundle:
    g = CONTRACT.get("global") or {}
    lam_lo = float(g.get("lambda_q_mm_min", 0.5))
    lam_hi = float(g.get("lambda_q_mm_max", 10.0))
    fexp_lo = float(g.get("flux_expansion_min", 2.0))
    fexp_hi = float(g.get("flux_expansion_max", 20.0))
    wet_lo = float(g.get("f_wet_min", 0.2))
    wet_hi = float(g.get("f_wet_max", 1.0))
    nmax = int(g.get("n_strike_points_max", 4))

    lam_used, lam_status = _clamp(float(lambda_q_mm_raw), lam_lo, lam_hi)
    fexp_used, fexp_status = _clamp(float(flux_expansion_raw), fexp_lo, fexp_hi)
    fwet_used, fwet_status = _clamp(float(f_wet_raw), wet_lo, wet_hi)

    n_raw = int(n_strike_points_raw)
    if n_raw <= 0:
        n_raw = 2
    n_used = max(1, min(n_raw, nmax))

    unit_thr = float(g.get("q_div_unit_suspect_threshold_MW_m2", 1e5))
    q = float(q_div_MW_m2)
    q_sus = 1.0 if (q == q and q > unit_thr) else 0.0

    return ExhaustAuthorityBundle(
        lambda_q_mm_raw=float(lambda_q_mm_raw),
        lambda_q_mm_used=float(lam_used),
        lambda_q_status=str(lam_status),
        flux_expansion_raw=float(flux_expansion_raw),
        flux_expansion_used=float(fexp_used),
        flux_expansion_status=str(fexp_status),
        n_strike_points_raw=int(n_strike_points_raw),
        n_strike_points_used=int(n_used),
        f_wet_raw=float(f_wet_raw),
        f_wet_used=float(fwet_used),
        f_wet_status=str(fwet_status),
        q_div_unit_suspect=float(q_sus),
        A_wet_m2=float(A_wet_m2),
    )
