from __future__ import annotations

"""Neutronics & Activation Authority 3.0 (v390.0.0).

Governance-only deterministic certification.

Certifies:
- shielding envelope margin
- DPA-lite rate and FW lifetime (FPY)
- activation index and cooldown bin

All enforcement is via explicit optional caps/minima (NaN disables).
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
    return here.parents[2] / "contracts" / "neutronics_activation_v390_contract.json"


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
class NeutronicsActivationCertificationV390:
    contract_sha256: str
    enabled: bool
    shield_margin_cm: float
    shield_margin_min_cm: float
    dpa_per_fpy: float
    dpa_max: float
    fw_life_fpy: float
    fw_life_min_fpy: float
    activation_index: float
    activation_max: float
    cooldown_bin: str
    verdict: str
    failed_components: list[str]
    ledger: list[dict]
    ctx: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "neutronics_activation_authority.v390",
            "neutronics_activation_v390_contract_sha256": self.contract_sha256,
            "enabled": bool(self.enabled),
            "verdict": str(self.verdict),
            "failed_components": list(self.failed_components),
            "metrics": {
                "shield": {
                    "margin_cm": float(self.shield_margin_cm),
                    "min_margin_cm": float(self.shield_margin_min_cm),
                },
                "damage": {
                    "dpa_per_fpy": float(self.dpa_per_fpy),
                    "dpa_per_fpy_max": float(self.dpa_max),
                    "fw_life_fpy": float(self.fw_life_fpy),
                    "fw_life_min_fpy": float(self.fw_life_min_fpy),
                },
                "activation": {
                    "activation_index": float(self.activation_index),
                    "activation_index_max": float(self.activation_max),
                    "cooldown_bin": str(self.cooldown_bin),
                },
            },
            "ledger": list(self.ledger),
            "context": dict(self.ctx),
            "contract": dict(CONTRACT) if isinstance(CONTRACT, dict) else {},
        }


def certify_neutronics_activation_v390(out: Dict[str, Any]) -> Dict[str, Any]:
    enabled = bool(out.get("include_neutronics_activation_v390", False))

    shield_margin = _safe_float(out, "shield_margin_cm_v390")
    shield_min = _safe_float(out, "shield_margin_min_cm_v390")

    dpa = _safe_float(out, "dpa_per_fpy_v390")
    dpa_max = _safe_float(out, "dpa_per_fpy_max_v390")

    fw_life = _safe_float(out, "fw_life_fpy_v390")
    fw_life_min = _safe_float(out, "fw_life_min_fpy_v390")

    act = _safe_float(out, "activation_index_v390")
    act_max = _safe_float(out, "activation_index_max_v390")
    cooldown_bin = str(out.get("cooldown_bin_v390", ""))

    ledger = out.get("neutronics_activation_ledger_v390", [])
    if not isinstance(ledger, list):
        ledger = []

    failed: list[str] = []
    if enabled:
        # Shielding: require margin >= min (if min finite)
        if _finite(shield_min) and _finite(shield_margin) and shield_margin < shield_min:
            failed.append("Shielding margin")
        # DPA cap
        if _finite(dpa_max) and _finite(dpa) and dpa > dpa_max:
            failed.append("FW DPA rate")
        # FW lifetime minimum
        if _finite(fw_life_min) and _finite(fw_life) and fw_life < fw_life_min:
            failed.append("FW lifetime")
        # Activation cap
        if _finite(act_max) and _finite(act) and act > act_max:
            failed.append("Activation index")

    verdict = "PASS"
    if enabled and failed:
        verdict = "FAIL"
    if not enabled:
        verdict = "OFF"

    cert = NeutronicsActivationCertificationV390(
        contract_sha256=_contract_sha256(),
        enabled=enabled,
        shield_margin_cm=shield_margin,
        shield_margin_min_cm=shield_min,
        dpa_per_fpy=dpa,
        dpa_max=dpa_max,
        fw_life_fpy=fw_life,
        fw_life_min_fpy=fw_life_min,
        activation_index=act,
        activation_max=act_max,
        cooldown_bin=cooldown_bin,
        verdict=verdict,
        failed_components=failed,
        ledger=ledger,
        ctx={
            "note": "Screening-only neutronics/activation envelopes; no MC transport; FW damage driven by wall load.",
        },
    )
    return cert.to_dict()
