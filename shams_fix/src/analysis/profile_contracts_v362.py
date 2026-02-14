from __future__ import annotations

"""Profile Contracts 2.0 (v362.0).

Deterministic robust-vs-optimistic feasibility screening against finite envelopes
over v358 profile-family knobs.

Law compliance
-------------
- Does not modify frozen truth.
- No solvers, no iteration, no Monte Carlo.
- Finite corner evaluation only (C8/C16/C32 presets).

© 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
import math

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore

try:
    from ..evaluator.core import Evaluator  # type: ignore
    from ..constraints.constraints import evaluate_constraints  # type: ignore
except Exception:
    from evaluator.core import Evaluator  # type: ignore
    from constraints.constraints import evaluate_constraints  # type: ignore

from ..contracts.profile_contracts_v362_contract import load_profile_contracts_v362


def _sha256_json(obj: Any) -> str:
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def _isfinite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def _clamp(x: float, lo: float, hi: float) -> float:
    if not math.isfinite(x):
        return float("nan")
    return max(lo, min(hi, x))


def _corner_signs(n_axes: int) -> List[List[int]]:
    """Return deterministic +/-1 hypercube corners for n_axes."""
    out: List[List[int]] = []
    for i in range(2 ** n_axes):
        row: List[int] = []
        for j in range(n_axes):
            bit = (i >> j) & 1
            row.append(+1 if bit else -1)
        out.append(row)
    return out


def _apply_axis(nominal: float, *, kind: str, span: float, sign: int, lo: float, hi: float) -> float:
    if not _isfinite(nominal):
        # Conservative nominal fallback (center of clamp)
        nominal = 0.5 * (float(lo) + float(hi))
    if kind == "add":
        v = float(nominal) + float(sign) * float(span)
    else:
        v = float(nominal) * (1.0 + float(sign) * float(span))
    return _clamp(float(v), float(lo), float(hi))


def _hard_feasible(constraints_json: List[Dict[str, Any]]) -> bool:
    for c in constraints_json or []:
        if not isinstance(c, dict):
            continue
        if str(c.get("severity", "hard")).strip().lower() != "hard":
            continue
        if not bool(c.get("passed", True)):
            return False
    return True


def _min_margin_frac(constraints_json: List[Dict[str, Any]]) -> float:
    m = float("inf")
    for c in constraints_json or []:
        if not isinstance(c, dict):
            continue
        if str(c.get("severity", "hard")).strip().lower() != "hard":
            continue
        mf = c.get("margin_frac")
        if mf is None:
            mf = c.get("margin")
        try:
            mfv = float(mf)
        except Exception:
            continue
        if not math.isfinite(mfv):
            continue
        m = min(m, mfv)
    return float(m if math.isfinite(m) else float("nan"))


@dataclass(frozen=True)
class ProfileContractsReportV362:
    schema_version: str
    preset: str
    tier: str
    contract_sha256: str
    run_fingerprint_sha256: str
    corner_count: int
    optimistic_feasible: bool
    robust_feasible: bool
    mirage: bool
    corners: List[Dict[str, Any]]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_profile_contracts_v362(
    base_inputs: PointInputs,
    *,
    preset: str = "C8",
    tier: str = "both",
    policy: Optional[Dict[str, Any]] = None,
) -> ProfileContractsReportV362:
    """Evaluate frozen truth at profile-contract corners.

    Parameters
    ----------
    base_inputs:
        PointInputs used as the nominal design.
    preset:
        One of C8/C16/C32.
    tier:
        'optimistic' | 'robust' | 'both'.
    policy:
        Optional feasibility-semantics policy (passed to constraint evaluation).
    """
    con, con_sha = load_profile_contracts_v362()
    preset_u = str(preset or "C8").upper().strip()
    if preset_u not in con.presets:
        preset_u = "C8"
    axes = list((con.presets[preset_u] or {}).get("axes", []) or [])
    axes = [str(a) for a in axes if str(a)]
    if not axes:
        axes = ["p_peaking", "j_peaking", "confinement_mult"]
    n_axes = int(len(axes))
    corners_signs = _corner_signs(n_axes)

    tier_n = str(tier or "both").lower().strip()
    if tier_n not in {"optimistic", "robust", "both"}:
        tier_n = "both"

    evaluator = Evaluator(cache_enabled=False)
    base_d = base_inputs.to_dict() if hasattr(base_inputs, "to_dict") else dict(getattr(base_inputs, "__dict__", {}))

    # Nominals for axes (for fingerprinting)
    nominals: Dict[str, float] = {}
    for ax in axes:
        spec = dict((con.axes or {}).get(ax, {}) or {})
        k = str(spec.get("input_key", ""))
        try:
            nominals[ax] = float(base_d.get(k, float("nan")))
        except Exception:
            nominals[ax] = float("nan")

    def _eval_one_tier(tier_name: str) -> Tuple[bool, List[Dict[str, Any]]]:
        rows: List[Dict[str, Any]] = []
        for idx, sgns in enumerate(corners_signs):
            overrides: Dict[str, float] = {}
            applied_axes: Dict[str, float] = {}
            for ax, s in zip(axes, sgns):
                spec = dict((con.axes or {}).get(ax, {}) or {})
                k = str(spec.get("input_key"))
                kind = str(spec.get("kind", "mult")).lower().strip()
                span = float(spec.get(f"{tier_name}_span", 0.0))
                lo = float(spec.get("clamp_lo", float("-inf")))
                hi = float(spec.get("clamp_hi", float("inf")))
                nominal = float(base_d.get(k, float("nan")))
                v = _apply_axis(nominal, kind=kind, span=span, sign=int(s), lo=lo, hi=hi)
                overrides[k] = float(v)
                applied_axes[ax] = float(v)

            # Build mutated PointInputs
            d2 = dict(base_d)
            d2.update(overrides)
            inp2 = PointInputs.from_dict(d2)

            ev = evaluator.evaluate(inp2)
            out = ev.out if isinstance(ev.out, dict) else {}
            cons = evaluate_constraints(out, policy=policy, point_inputs=d2)
            cons_json = [c.as_dict() for c in cons]

            row = {
                "corner_index": int(idx),
                "corner_bits": [int(x) for x in sgns],
                "tier": tier_name,
                "axes": applied_axes,
                "ok": bool(ev.ok),
                "eval_message": str(ev.message or ""),
                "hard_feasible": _hard_feasible(cons_json) if ev.ok else False,
                "min_margin_frac": _min_margin_frac(cons_json) if ev.ok else float("nan"),
                "constraints": cons_json,
            }
            rows.append(row)

        feasible = all(bool(r.get("hard_feasible")) for r in rows)
        return feasible, rows

    optimistic_feasible = False
    robust_feasible = False
    corners_all: List[Dict[str, Any]] = []
    if tier_n in {"optimistic", "both"}:
        optimistic_feasible, rows = _eval_one_tier("optimistic")
        corners_all.extend(rows)
    if tier_n in {"robust", "both"}:
        robust_feasible, rows = _eval_one_tier("robust")
        corners_all.extend(rows)

    if tier_n == "optimistic":
        robust_feasible = bool(optimistic_feasible)
    if tier_n == "robust":
        optimistic_feasible = bool(robust_feasible)

    mirage = bool(optimistic_feasible and not robust_feasible)

    # Summary: worst corner by min margin
    worst = None
    worst_m = float("inf")
    for r in corners_all:
        try:
            m = float(r.get("min_margin_frac", float("inf")))
        except Exception:
            continue
        if math.isfinite(m) and m < worst_m:
            worst_m, worst = m, r

    summary = {
        "axes": axes,
        "nominals": nominals,
        "worst_min_margin_frac": float(worst_m) if math.isfinite(worst_m) else None,
        "worst_corner": {
            "tier": worst.get("tier") if isinstance(worst, dict) else None,
            "corner_index": worst.get("corner_index") if isinstance(worst, dict) else None,
            "axes": worst.get("axes") if isinstance(worst, dict) else None,
        }
        if isinstance(worst, dict)
        else {},
    }

    run_fp = _sha256_json(
        {
            "schema": "profile_contracts_run_fingerprint.v1",
            "contract_sha256": con_sha,
            "preset": preset_u,
            "tier": tier_n,
            "axes": axes,
            "nominals": nominals,
        }
    )

    return ProfileContractsReportV362(
        schema_version="profile_contracts_report.v362",
        preset=preset_u,
        tier=tier_n,
        contract_sha256=con_sha,
        run_fingerprint_sha256=run_fp,
        corner_count=int(len(corners_all)),
        optimistic_feasible=bool(optimistic_feasible),
        robust_feasible=bool(robust_feasible),
        mirage=bool(mirage),
        corners=corners_all,
        summary=summary,
    )
