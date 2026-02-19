from __future__ import annotations

"""Structural Stress Authority (v389.0.0).

Governance-only, deterministic certification of structural stress proxies.

This authority is deliberately algebraic:
- derives margins from outputs produced by the frozen evaluator stack
- optionally enforces feasibility via explicit minima (when enabled)
- attaches contract SHA-256 for auditability
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import hashlib
import json
import math


def _safe_float(d: Dict[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        return float(d.get(key, default))
    except Exception:
        return float(default)


def _finite(x: float) -> bool:
    return (x == x) and math.isfinite(x)


def _contract_path() -> Path:
    here = Path(__file__).resolve()
    return here.parents[2] / "contracts" / "structural_stress_v389_contract.json"


def _contract_sha256() -> str:
    p = _contract_path()
    try:
        if p.exists():
            return hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception:
        pass
    return ""


def _load_contract() -> Dict[str, Any]:
    p = _contract_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


CONTRACT: Dict[str, Any] = _load_contract()


@dataclass(frozen=True)
class StructuralStressCertificationV389:
    contract_sha256: str
    enabled: bool
    tf_margin: float
    tf_min: float
    cs_margin: float
    cs_min: float
    vv_margin: float
    vv_min: float
    verdict: str
    failed_components: list[str]
    ledger: list[dict]
    ctx: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "structural_stress_authority.v389",
            "structural_stress_v389_contract_sha256": self.contract_sha256,
            "enabled": bool(self.enabled),
            "verdict": str(self.verdict),
            "failed_components": list(self.failed_components),
            "margins": {
                "tf": {"margin": float(self.tf_margin), "min": float(self.tf_min)},
                "cs": {"margin": float(self.cs_margin), "min": float(self.cs_min)},
                "vv": {"margin": float(self.vv_margin), "min": float(self.vv_min)},
            },
            "margin_ledger": list(self.ledger),
            "context": dict(self.ctx),
            "contract": dict(CONTRACT) if isinstance(CONTRACT, dict) else {},
        }


def certify_structural_stress_v389(out: Dict[str, Any]) -> Dict[str, Any]:
    enabled = bool(out.get("include_structural_stress_v389", False))

    tf = _safe_float(out, "tf_struct_margin_v389")
    tf_min = _safe_float(out, "tf_struct_margin_min_v389")
    cs = _safe_float(out, "cs_struct_margin_v389")
    cs_min = _safe_float(out, "cs_struct_margin_min_v389")
    vv = _safe_float(out, "vv_struct_margin_v389")
    vv_min = _safe_float(out, "vv_struct_margin_min_v389")

    ledger = out.get("structural_margin_ledger_v389", [])
    if not isinstance(ledger, list):
        ledger = []

    failed: list[str] = []
    if enabled:
        if _finite(tf) and _finite(tf_min) and tf < tf_min:
            failed.append("TF")
        if _finite(cs) and _finite(cs_min) and cs < cs_min:
            failed.append("CS/PF")
        if _finite(vv) and _finite(vv_min) and vv < vv_min:
            failed.append("Vacuum vessel")

    verdict = "PASS"
    if enabled and failed:
        verdict = "FAIL"
    if not enabled:
        verdict = "OFF"

    cert = StructuralStressCertificationV389(
        contract_sha256=_contract_sha256(),
        enabled=enabled,
        tf_margin=tf,
        tf_min=tf_min,
        cs_margin=cs,
        cs_min=cs_min,
        vv_margin=vv,
        vv_min=vv_min,
        verdict=verdict,
        failed_components=failed,
        ledger=ledger,
        ctx={
            "note": "Screening-only structural stress proxies (thin-shell pR/t). No buckling/FEA.",
        },
    )
    return cert.to_dict()
