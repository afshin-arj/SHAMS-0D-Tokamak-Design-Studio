from __future__ import annotations

"""Availability 2.0 — Reliability Envelope Authority (v391.0.0).

Governance-only deterministic certification.

Certifies:
- availability_cert_v391 (envelope)
- planned outage fraction
- maintenance downtime fraction (replacement + activation/cooldown burden)
- unplanned downtime fraction from MTBF/MTTR product proxy

Enforcement is via explicit optional caps/minima (NaN disables).
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
    return here.parents[2] / "contracts" / "availability_reliability_v391_contract.json"


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
class AvailabilityReliabilityCertificationV391:
    contract_sha256: str
    enabled: bool
    availability: float
    availability_min: float
    planned_outage_frac: float
    planned_outage_max: float
    unplanned_downtime_frac: float
    unplanned_downtime_max: float
    maint_downtime_frac: float
    maint_downtime_max: float
    driver: str
    regime: str
    verdict: str
    failed_components: list[str]
    ledger: list[dict]
    ctx: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "availability_reliability_authority.v391",
            "availability_reliability_v391_contract_sha256": self.contract_sha256,
            "enabled": bool(self.enabled),
            "verdict": str(self.verdict),
            "failed_components": list(self.failed_components),
            "metrics": {
                "availability": {
                    "availability_cert": float(self.availability),
                    "availability_min": float(self.availability_min),
                    "regime": str(self.regime),
                    "driver": str(self.driver),
                },
                "downtime": {
                    "planned_outage_frac": float(self.planned_outage_frac),
                    "planned_outage_max": float(self.planned_outage_max),
                    "unplanned_downtime_frac": float(self.unplanned_downtime_frac),
                    "unplanned_downtime_max": float(self.unplanned_downtime_max),
                    "maint_downtime_frac": float(self.maint_downtime_frac),
                    "maint_downtime_max": float(self.maint_downtime_max),
                },
            },
            "ledger": list(self.ledger),
            "context": dict(self.ctx),
            "contract": dict(CONTRACT) if isinstance(CONTRACT, dict) else {},
        }


def certify_availability_reliability_v391(out: Dict[str, Any]) -> Dict[str, Any]:
    enabled = bool(out.get("include_availability_reliability_v391", False))

    A = _safe_float(out, "availability_cert_v391")
    Amin = _safe_float(out, "availability_min_v391")

    planned = _safe_float(out, "planned_outage_frac_v391")
    planned_max = _safe_float(out, "planned_outage_max_frac_v391")

    unplanned = _safe_float(out, "unplanned_downtime_frac_v391")
    unplanned_max = _safe_float(out, "unplanned_downtime_max_frac_v391")

    maint = _safe_float(out, "maint_downtime_frac_v391")
    maint_max = _safe_float(out, "maint_downtime_max_frac_v391")

    driver = str(out.get("availability_driver_v391", ""))
    regime = str(out.get("availability_regime_v391", ""))

    ledger = out.get("availability_ledger_v391", [])
    if not isinstance(ledger, list):
        ledger = []

    failed: list[str] = []
    if enabled:
        if _finite(Amin) and _finite(A) and A < Amin:
            failed.append("Availability")
        if _finite(planned_max) and _finite(planned) and planned > planned_max:
            failed.append("Planned outage")
        if _finite(unplanned_max) and _finite(unplanned) and unplanned > unplanned_max:
            failed.append("Unplanned downtime")
        if _finite(maint_max) and _finite(maint) and maint > maint_max:
            failed.append("Maintenance downtime")

    verdict = "PASS"
    if enabled and failed:
        verdict = "FAIL"
    if not enabled:
        verdict = "OFF"

    cert = AvailabilityReliabilityCertificationV391(
        contract_sha256=_contract_sha256(),
        enabled=enabled,
        availability=A,
        availability_min=Amin,
        planned_outage_frac=planned,
        planned_outage_max=planned_max,
        unplanned_downtime_frac=unplanned,
        unplanned_downtime_max=unplanned_max,
        maint_downtime_frac=maint,
        maint_downtime_max=maint_max,
        driver=driver,
        regime=regime,
        verdict=verdict,
        failed_components=failed,
        ledger=ledger,
        ctx={
            "note": "Deterministic availability envelope using MTBF/MTTR product proxy + planned and maintenance downtime (no RAMI simulation).",
        },
    )
    return cert.to_dict()
