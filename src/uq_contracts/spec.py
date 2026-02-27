from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


def default_uncertainty_contract(inp: Any) -> "UncertaintyContractSpec":
    """Return a conservative default uncertainty contract.

    The default targets the explicit calibration multipliers already present in
    PointInputs. These are safe to vary in a deterministic corner analysis
    without implying transport fidelity:

    - confinement_mult: +/- 10%
    - lambda_q_mult:    +/- 20%
    - hts_Jc_mult:      +/- 10%
    """
    def _g(k: str, default: float) -> float:
        try:
            return float(getattr(inp, k))
        except Exception:
            return float(default)

    c = _g("confinement_mult", 1.0)
    lq = _g("lambda_q_mult", 1.0)
    jc = _g("hts_Jc_mult", 1.0)

    intervals = {
        "confinement_mult": Interval(lo=0.90 * c, hi=1.10 * c),
        "lambda_q_mult": Interval(lo=0.80 * lq, hi=1.20 * lq),
        "hts_Jc_mult": Interval(lo=0.90 * jc, hi=1.10 * jc),
    }
    return UncertaintyContractSpec(
        name="default_uq",
        intervals=intervals,
        policy_overrides=None,
        notes="Default UQ-lite: multipliers only (confinement, lambda_q, HTS Jc).",
    )


def optimistic_uncertainty_contract(inp: Any) -> "UncertaintyContractSpec":
    """Return an explicitly optimistic UQ-lite contract.

    Philosophy:
      - still interval-based (no probability)
      - centers performance multipliers slightly optimistic
      - narrows uncertainty to represent a "best-case but declared" scenario

    Defaults (relative to current PointInputs multipliers):
      - confinement_mult: center +8%, +/- 5%
      - lambda_q_mult:    center +10%, +/- 10%   (larger lambda_q reduces q_div)
      - hts_Jc_mult:      center +8%, +/- 5%
    """
    def _g(k: str, default: float) -> float:
        try:
            return float(getattr(inp, k))
        except Exception:
            return float(default)

    c = _g("confinement_mult", 1.0)
    lq = _g("lambda_q_mult", 1.0)
    jc = _g("hts_Jc_mult", 1.0)

    c0 = 1.08 * c
    lq0 = 1.10 * lq
    jc0 = 1.08 * jc

    intervals = {
        "confinement_mult": Interval(lo=0.95 * c0, hi=1.05 * c0),
        "lambda_q_mult": Interval(lo=0.90 * lq0, hi=1.10 * lq0),
        "hts_Jc_mult": Interval(lo=0.95 * jc0, hi=1.05 * jc0),
    }
    return UncertaintyContractSpec(
        name="optimistic_uq",
        intervals=intervals,
        policy_overrides=None,
        notes="Optimistic UQ-lite: slightly improved multipliers + narrower intervals.",
    )


def robust_uncertainty_contract(inp: Any) -> "UncertaintyContractSpec":
    """Return a more conservative robust UQ-lite contract.

    This intentionally widens the default intervals to stress-test feasibility.

    Defaults (relative to current PointInputs multipliers):
      - confinement_mult: +/- 15%
      - lambda_q_mult:    +/- 25%
      - hts_Jc_mult:      +/- 15%
    """
    def _g(k: str, default: float) -> float:
        try:
            return float(getattr(inp, k))
        except Exception:
            return float(default)

    c = _g("confinement_mult", 1.0)
    lq = _g("lambda_q_mult", 1.0)
    jc = _g("hts_Jc_mult", 1.0)

    intervals = {
        "confinement_mult": Interval(lo=0.85 * c, hi=1.15 * c),
        "lambda_q_mult": Interval(lo=0.75 * lq, hi=1.25 * lq),
        "hts_Jc_mult": Interval(lo=0.85 * jc, hi=1.15 * jc),
    }
    return UncertaintyContractSpec(
        name="robust_uq",
        intervals=intervals,
        policy_overrides=None,
        notes="Robust UQ-lite: widened intervals (stress test).",
    )


@dataclass(frozen=True)
class Interval:
    """Closed interval [lo, hi] (deterministic, non-probabilistic)."""
    lo: float
    hi: float

    def normalized(self) -> "Interval":
        lo = float(self.lo)
        hi = float(self.hi)
        if hi < lo:
            lo, hi = hi, lo
        return Interval(lo=lo, hi=hi)

    def to_dict(self) -> Dict[str, Any]:
        it = self.normalized()
        return {"lo": float(it.lo), "hi": float(it.hi)}


@dataclass(frozen=True)
class UncertaintyContractSpec:
    """Interval truth contract for PointInputs fields.

    Interpretation:
      - the user declares uncertain inputs as intervals
      - SHAMS enumerates all corners deterministically (2^N)
      - no probability, no Monte Carlo

    Robustness classes:
      - ROBUST_PASS: all corners feasible
      - FAIL: all corners infeasible
      - FRAGILE: mixed feasibility

    Optional policy_overrides apply to constraint tier semantics (not physics).
    """
    name: str
    intervals: Dict[str, Interval]
    policy_overrides: Optional[Dict[str, Any]] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "uncertainty_contract_spec.v1",
            "name": str(self.name),
            "intervals": {k: v.to_dict() for k, v in (self.intervals or {}).items()},
            "policy_overrides": dict(self.policy_overrides or {}),
            "notes": str(self.notes or ""),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "UncertaintyContractSpec":
        if not isinstance(d, dict):
            raise TypeError("UncertaintyContractSpec.from_dict expects a dict")
        schema = str(d.get("schema_version", "") or d.get("schema", ""))
        if schema not in {"uncertainty_contract_spec.v1", "uncertainty_contract_spec"}:
            raise ValueError(f"Unsupported uncertainty contract schema_version: {schema}")
        name = str(d.get("name", d.get("label", "contract")))
        intervals_in = d.get("intervals") or {}
        if not isinstance(intervals_in, dict):
            raise TypeError("uncertainty_contract_spec.intervals must be a dict")
        intervals: Dict[str, Interval] = {}
        for k, v in intervals_in.items():
            if not isinstance(v, dict):
                continue
            try:
                lo = float(v.get("lo"))
                hi = float(v.get("hi"))
                intervals[str(k)] = Interval(lo=lo, hi=hi)
            except Exception:
                continue
        pol = d.get("policy_overrides")
        if pol is not None and not isinstance(pol, dict):
            pol = None
        notes = str(d.get("notes", "") or "")
        return UncertaintyContractSpec(name=name, intervals=intervals, policy_overrides=pol, notes=notes)
