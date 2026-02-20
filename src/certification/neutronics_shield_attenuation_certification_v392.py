from __future__ import annotations

"""Neutronics Shield Attenuation Authority (v392.0.0).

Governance-only deterministic certification.

Certifies:
- TF-case fluence proxy (n/m^2/FPY)
- Cryostat fluence proxy (n/m^2/FPY)
- Outside-bioshield dose-rate proxy (uSv/h)

Enforcement is via explicit optional caps (NaN disables).
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
    return here.parents[2] / "contracts" / "neutronics_shield_attenuation_v392_contract.json"


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
class NeutronicsShieldAttenuationCertificationV392:
    contract_sha256: str
    enabled: bool
    tf_fluence: float
    tf_fluence_max: float
    cryo_fluence: float
    cryo_fluence_max: float
    bio_dose: float
    bio_dose_max: float
    verdict: str
    failed_components: list[str]
    ledger: list[dict]
    ctx: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "neutronics_shield_attenuation_authority.v392",
            "neutronics_shield_attenuation_v392_contract_sha256": self.contract_sha256,
            "enabled": bool(self.enabled),
            "verdict": str(self.verdict),
            "failed_components": list(self.failed_components),
            "metrics": {
                "tf_case": {
                    "fluence_n_m2_per_fpy": float(self.tf_fluence),
                    "fluence_max_n_m2_per_fpy": float(self.tf_fluence_max),
                },
                "cryostat": {
                    "fluence_n_m2_per_fpy": float(self.cryo_fluence),
                    "fluence_max_n_m2_per_fpy": float(self.cryo_fluence_max),
                },
                "bioshield": {
                    "dose_rate_uSv_h": float(self.bio_dose),
                    "dose_rate_max_uSv_h": float(self.bio_dose_max),
                },
            },
            "ledger": list(self.ledger),
            "context": dict(self.ctx),
            "contract": dict(CONTRACT) if isinstance(CONTRACT, dict) else {},
        }


def certify_neutronics_shield_attenuation_v392(out: Dict[str, Any]) -> Dict[str, Any]:
    enabled = bool(out.get("include_neutronics_shield_attenuation_v392", False))

    tf_flu = _safe_float(out, "tf_case_fluence_n_m2_per_fpy_v392")
    tf_max = _safe_float(out, "tf_case_fluence_max_n_m2_per_fpy_v392")

    cryo_flu = _safe_float(out, "cryostat_fluence_n_m2_per_fpy_v392")
    cryo_max = _safe_float(out, "cryostat_fluence_max_n_m2_per_fpy_v392")

    bio_dose = _safe_float(out, "bioshield_dose_rate_uSv_h_v392")
    bio_max = _safe_float(out, "bioshield_dose_rate_max_uSv_h_v392")

    ledger = out.get("neutronics_shield_attenuation_ledger_v392", [])
    if not isinstance(ledger, list):
        ledger = []

    failed: list[str] = []
    if enabled:
        if _finite(tf_max) and _finite(tf_flu) and tf_flu > tf_max:
            failed.append("TF-case fluence")
        if _finite(cryo_max) and _finite(cryo_flu) and cryo_flu > cryo_max:
            failed.append("Cryostat fluence")
        if _finite(bio_max) and _finite(bio_dose) and bio_dose > bio_max:
            failed.append("Bioshield dose rate")

    verdict = "PASS"
    if enabled and failed:
        verdict = "FAIL"
    if not enabled:
        verdict = "OFF"

    cert = NeutronicsShieldAttenuationCertificationV392(
        contract_sha256=_contract_sha256(),
        enabled=enabled,
        tf_fluence=tf_flu,
        tf_fluence_max=tf_max,
        cryo_fluence=cryo_flu,
        cryo_fluence_max=cryo_max,
        bio_dose=bio_dose,
        bio_dose_max=bio_max,
        verdict=verdict,
        failed_components=failed,
        ledger=ledger,
        ctx={
            "note": "Screening-only attenuation-length envelopes; no MC transport; optional 1/r^2 dilution is a coarse geometric proxy.",
        },
    )
    return cert.to_dict()
