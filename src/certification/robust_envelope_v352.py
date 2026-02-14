
from __future__ import annotations

"""v352.0 — Robust Design Envelope Certification.

Deterministic, audit-ready certification over an explicit candidate set.
This module NEVER modifies frozen truth. It only runs budgeted, deterministic
corner-evaluations under an uncertainty contract and summarizes outcomes.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
import hashlib
import io
import json
import zipfile
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore


@dataclass(frozen=True)
class TierThresholds:
    """Deterministic tier thresholds on worst_hard_margin_frac."""
    tier_A_min: float = 0.10
    tier_B_min: float = 0.03
    tier_C_min: float = 0.00

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier_A_min": float(self.tier_A_min),
            "tier_B_min": float(self.tier_B_min),
            "tier_C_min": float(self.tier_C_min),
        }


def sha256_json(obj: Any) -> str:
    """Stable SHA-256 over canonical JSON (sorted keys, UTF-8)."""
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def _tier_from_worst_margin(worst_hard_margin_frac: Optional[float], thresholds: TierThresholds) -> str:
    if worst_hard_margin_frac is None:
        return "UNSPECIFIED"
    try:
        w = float(worst_hard_margin_frac)
    except Exception:
        return "UNSPECIFIED"
    if w >= thresholds.tier_A_min:
        return "TIER_A"
    if w >= thresholds.tier_B_min:
        return "TIER_B"
    if w >= thresholds.tier_C_min:
        return "TIER_C"
    return "NOT_CERTIFIED"


def certify_points_under_contract(
    *,
    points: List[PointInputs],
    contract_spec: Dict[str, Any],
    run_uq_fn: Any,
    thresholds: Optional[TierThresholds] = None,
    label_prefix: str = "v352",
    max_points: int = 50,
) -> Dict[str, Any]:
    """Certify a list of PointInputs under a deterministic uncertainty contract.

    Args:
      points: explicit candidate set (already selected by user/external process).
      contract_spec: spec dict (UncertaintyContractSpec.to_dict()) for stamping.
      run_uq_fn: function(base_inputs: PointInputs, spec: UncertaintyContractSpec, ...) -> dict
      thresholds: tier thresholds based on worst_hard_margin_frac.
      label_prefix: label prefix for corner artifacts.
      max_points: budget cap (prevents runaway artifact sizes).
    """
    if thresholds is None:
        thresholds = TierThresholds()

    if not isinstance(points, list):
        raise TypeError("points must be a list[PointInputs]")
    if len(points) == 0:
        raise ValueError("points list is empty")
    if len(points) > int(max_points):
        points = list(points[: int(max_points)])

    # Recompute contract fingerprint from dict (do not trust caller string)
    contract_fp = sha256_json(contract_spec)

    rows: List[Dict[str, Any]] = []
    corner_packs: List[Dict[str, Any]] = []

    n_cert = 0
    n_fail = 0
    n_fragile = 0
    n_robust = 0

    # Late import to avoid hard dependency cycles
    try:
        from uq_contracts.spec import UncertaintyContractSpec  # type: ignore
    except Exception:
        from src.uq_contracts.spec import UncertaintyContractSpec  # type: ignore

    from uq_contracts.spec import Interval  # type: ignore
    intervals = {k: Interval(lo=float(v.get('lo')), hi=float(v.get('hi'))) for k, v in (contract_spec.get('intervals') or {}).items()}
    spec = UncertaintyContractSpec(name=str(contract_spec.get('name','uq')), intervals=intervals, policy_overrides=contract_spec.get('policy_overrides') or None, notes=str(contract_spec.get('notes','')))

    for i, inp in enumerate(points):
        uq = run_uq_fn(inp, spec, label_prefix=f"{label_prefix}:p{i:04d}")
        summ = (uq or {}).get("summary", {}) if isinstance(uq, dict) else {}
        verdict = str(summ.get("verdict", "UNKNOWN"))
        worst = summ.get("worst_hard_margin_frac", None)

        tier = "NOT_CERTIFIED"
        if verdict == "ROBUST_PASS":
            tier = _tier_from_worst_margin(worst, thresholds)
            if tier in ("TIER_A", "TIER_B", "TIER_C"):
                n_cert += 1
                n_robust += 1
            else:
                n_fail += 1
        elif verdict == "FRAGILE":
            tier = "FRAGILE"
            n_fragile += 1
        elif verdict == "FAIL":
            tier = "FAIL"
            n_fail += 1
        else:
            tier = "UNKNOWN"

        row = {
            "index": int(i),
            "verdict": verdict,
            "tier": tier,
            "worst_hard_margin_frac": worst,
            "n_corners": summ.get("n_corners"),
            "n_feasible": summ.get("n_feasible"),
            "worst_corner_index": summ.get("worst_corner_index"),
            "inputs": dict(inp.__dict__),
        }
        rows.append(row)

        # Keep corner artifacts for evidence packing (may be large; UI can omit)
        corner_packs.append(uq)

    report = {
        "schema_version": "robust_envelope_certification.v352",
        "label_prefix": str(label_prefix),
        "contract_spec": contract_spec,
        "contract_sha256": contract_fp,
        "thresholds": thresholds.to_dict(),
        "budget": {"max_points": int(max_points), "points_certified": int(len(points))},
        "counts": {
            "n_points": int(len(points)),
            "n_certified": int(n_cert),
            "n_robust": int(n_robust),
            "n_fragile": int(n_fragile),
            "n_fail": int(n_fail),
        },
        "rows": rows,
    }

    report["report_sha256"] = sha256_json(report)

    return {
        "report": report,
        "corner_packs": corner_packs,
    }


def build_certification_evidence_zip(
    *,
    certification: Dict[str, Any],
    include_corners: bool = True,
) -> bytes:
    """Build a deterministic evidence ZIP (bytes) for download.

    Contents:
      - robust_envelope_report.json
      - corners/point_XXXX/uq_contract.json (optional per-corner artifacts)
    """
    if not isinstance(certification, dict) or "report" not in certification:
        raise ValueError("certification must include 'report'")

    report = certification["report"]
    corner_packs = certification.get("corner_packs", [])

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("robust_envelope_report.json", json.dumps(report, indent=2, sort_keys=True))
        if include_corners:
            for i, pack in enumerate(corner_packs):
                if not isinstance(pack, dict):
                    continue
                z.writestr(f"corners/point_{i:04d}/uq_contract.json", json.dumps(pack, indent=2, sort_keys=True))

    return bio.getvalue()
