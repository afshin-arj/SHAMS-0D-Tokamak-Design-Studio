from __future__ import annotations

"""Cost Authority 3.0 — Industrial Depth (v388.0.0).

Governance-only, deterministic, algebraic certification.

Design goals:
- no iteration, no solvers
- audit-friendly: contract SHA-256 fingerprint
- derived from the last Systems artifact outputs (+ optional inputs dict)

This authority is *additive* to v383 (does not modify or replace it).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import hashlib
import math
import json


def _safe_float(d: Dict[str, Any], *keys: str, default: float = float("nan")) -> float:
    for k in keys:
        if k in d:
            try:
                return float(d.get(k))
            except Exception:
                continue
    return float(default)


def _finite(x: float) -> bool:
    return (x == x) and math.isfinite(x)


def _contract_path() -> Path:
    here = Path(__file__).resolve()
    return here.parents[2] / "contracts" / "economics_v388_contract.json"


def _load_contract() -> Dict[str, Any]:
    path = _contract_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _contract_sha256() -> str:
    path = _contract_path()
    try:
        if path.exists():
            return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        pass
    return ""


CONTRACT: Dict[str, Any] = _load_contract()


@dataclass(frozen=True)
class CostAuthorityCertificationV388:
    contract_sha256: str
    capex_MUSD: float
    opex_MUSD_per_y: float
    lcoe_USD_per_MWh: float
    magnet_regime: str
    B_peak_bin: str
    dominant_driver: str
    dominant_frac: float
    caps: Dict[str, float]
    ctx: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "economics_authority.v388",
            "economics_v388_contract_sha256": self.contract_sha256,
            "metrics": {
                "CAPEX_industrial_v388_MUSD": self.capex_MUSD,
                "OPEX_industrial_v388_MUSD_per_y": self.opex_MUSD_per_y,
                "LCOE_lite_v388_USD_per_MWh": self.lcoe_USD_per_MWh,
                "magnet_regime_v388": self.magnet_regime,
                "B_peak_bin_v388": self.B_peak_bin,
                "dominant_cost_driver_v388": self.dominant_driver,
                "dominant_cost_frac_v388": self.dominant_frac,
            },
            "caps": dict(self.caps),
            "ctx": dict(self.ctx),
        }


def evaluate_cost_authority_v388(
    outputs: Dict[str, Any],
    inputs: Optional[Dict[str, Any]] = None,
    *,
    contract: Dict[str, Any] = CONTRACT,
) -> CostAuthorityCertificationV388:
    """Evaluate the v388 industrial-depth cost authority from Systems outputs."""

    capex = _safe_float(outputs, "CAPEX_industrial_v388_MUSD")
    opex = _safe_float(outputs, "OPEX_industrial_v388_MUSD_per_y")
    lcoe = _safe_float(outputs, "LCOE_lite_v388_USD_per_MWh")

    magnet_regime = str(outputs.get("magnet_regime_v388", outputs.get("magnet_regime", "")) or "")
    Bbin = str(outputs.get("B_peak_bin_v388", "") or "")

    dom = str(outputs.get("dominant_cost_driver_v388", "") or "")
    domf = _safe_float(outputs, "dominant_cost_frac_v388", default=float("nan"))

    caps = {
        "CAPEX_industrial_max_MUSD": _safe_float(outputs, "CAPEX_industrial_max_MUSD", default=float("nan")),
        "OPEX_industrial_max_MUSD_per_y": _safe_float(outputs, "OPEX_industrial_max_MUSD_per_y", default=float("nan")),
        "LCOE_lite_v388_max_USD_per_MWh": _safe_float(outputs, "LCOE_lite_v388_max_USD_per_MWh", default=float("nan")),
    }

    ctx = {
        "q_div_MW_m2": _safe_float(outputs, "q_div_MW_m2"),
        "B_peak_T": _safe_float(outputs, "B_coil_peak_T", "Bpeak_T"),
        "P_cryo_20K_MW": _safe_float(outputs, "P_cryo_20K_MW"),
        "P_th_MW": _safe_float(outputs, "P_th_MW", "P_th"),
        "inputs_present": bool(isinstance(inputs, dict) and len(inputs or {}) > 0),
    }

    if not _finite(lcoe):
        # Presentation: keep NaN if unavailable.
        lcoe = float("nan")

    return CostAuthorityCertificationV388(
        contract_sha256=_contract_sha256(),
        capex_MUSD=float(capex) if _finite(capex) else float("nan"),
        opex_MUSD_per_y=float(opex) if _finite(opex) else float("nan"),
        lcoe_USD_per_MWh=float(lcoe) if _finite(lcoe) else float("nan"),
        magnet_regime=str(magnet_regime),
        B_peak_bin=str(Bbin),
        dominant_driver=str(dom),
        dominant_frac=float(domf) if _finite(domf) else float("nan"),
        caps={k: float(v) for k, v in caps.items()},
        ctx={k: (float(v) if isinstance(v, (int, float)) and _finite(float(v)) else v) for k, v in ctx.items()},
    )


def certification_table_rows(cert: Dict[str, Any]) -> Dict[str, Any]:
    metrics = cert.get("metrics", {}) if isinstance(cert, dict) else {}
    return {
        "CAPEX_industrial (MUSD)": metrics.get("CAPEX_industrial_v388_MUSD", float("nan")),
        "OPEX_industrial (MUSD/y)": metrics.get("OPEX_industrial_v388_MUSD_per_y", float("nan")),
        "LCOE_lite (USD/MWh)": metrics.get("LCOE_lite_v388_USD_per_MWh", float("nan")),
        "Magnet regime": metrics.get("magnet_regime_v388", ""),
        "B_peak bin": metrics.get("B_peak_bin_v388", ""),
        "Dominant driver": metrics.get("dominant_cost_driver_v388", ""),
        "Dominant frac": metrics.get("dominant_cost_frac_v388", float("nan")),
    }
