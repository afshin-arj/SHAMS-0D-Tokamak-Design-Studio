from __future__ import annotations

"""Plant Economics & Cost Authority 2.0 (v383.0.0).

This is a governance-only, deterministic overlay.

Design goals:
- algebraic only (no iteration)
- audit-friendly outputs with in-repo contract fingerprint
- derived purely from the last Systems artifact (inputs+outputs)

The authority evaluates:
- structured CAPEX proxy
- structured OPEX proxy
- availability tier (A/B/C)
- capacity factor used
- LCOE-lite (USD/MWh)

It does NOT modify plasma truth, nor does it gate feasibility unless the
user explicitly sets caps (NaN disables caps).
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
                v = float(d.get(k))
                return v
            except Exception:
                continue
    return float(default)


def _finite(x: float) -> bool:
    return (x == x) and math.isfinite(x)


def _load_contract() -> Dict[str, Any]:
    here = Path(__file__).resolve()
    path = here.parents[2] / "contracts" / "economics_v383_contract.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _contract_sha256() -> str:
    here = Path(__file__).resolve()
    path = here.parents[2] / "contracts" / "economics_v383_contract.json"
    try:
        if path.exists():
            return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        pass
    return ""


CONTRACT: Dict[str, Any] = _load_contract()


@dataclass(frozen=True)
class PlantEconomicsCertificationV383:
    contract_sha256: str
    capex_MUSD: float
    opex_MUSD_per_y: float
    lcoe_USD_per_MWh: float
    tier: str
    capacity_factor: float
    net_MWh_per_year: float
    dominant_driver: str
    dominant_frac: float
    caps: Dict[str, float]
    ctx: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "economics_authority.v383",
            "economics_v383_contract_sha256": self.contract_sha256,
            "metrics": {
                "CAPEX_structured_v383_MUSD": self.capex_MUSD,
                "OPEX_structured_v383_MUSD_per_y": self.opex_MUSD_per_y,
                "LCOE_lite_v383_USD_per_MWh": self.lcoe_USD_per_MWh,
                "availability_tier_v383": self.tier,
                "capacity_factor_used_v383": self.capacity_factor,
                "net_electric_MWh_per_year_used_v383": self.net_MWh_per_year,
                "dominant_cost_driver_v383": self.dominant_driver,
                "dominant_cost_frac_v383": self.dominant_frac,
            },
            "caps": dict(self.caps),
            "ctx": dict(self.ctx),
        }


def evaluate_plant_economics_authority_v383(
    outputs: Dict[str, Any],
    inputs: Optional[Dict[str, Any]] = None,
    *,
    contract: Dict[str, Any] = CONTRACT,
) -> PlantEconomicsCertificationV383:
    """Evaluate v383 plant economics authority from a Systems artifact."""

    defaults = (contract.get("defaults") or {}) if isinstance(contract, dict) else {}
    capex = _safe_float(outputs, "CAPEX_structured_v383_MUSD", "CAPEX_component_proxy_MUSD", "CAPEX_proxy_MUSD")
    opex = _safe_float(outputs, "OPEX_structured_v383_MUSD_per_y", "OPEX_v360_total_MUSD_per_y", "OPEX_proxy_MUSD_per_y")
    lcoe = _safe_float(outputs, "LCOE_lite_v383_USD_per_MWh", "LCOE_proxy_v360_USD_per_MWh", "LCOE_proxy_USD_per_MWh")

    tier = str(outputs.get("availability_tier_v383", "")) or "B"
    cf = _safe_float(outputs, "capacity_factor_used_v383", default=float(defaults.get("v383_capacity_factor_B", 0.70)))
    net = _safe_float(outputs, "net_electric_MWh_per_year_used_v383", "net_electric_MWh_per_year_v368", "net_electric_MWh_per_year_v359")

    dom = str(outputs.get("dominant_cost_driver_v383", outputs.get("dominant_cost_driver", "")) or "")
    domf = _safe_float(outputs, "dominant_cost_frac_v383", "dominant_cost_frac", default=float("nan"))

    # Pass-through caps for audit visibility.
    caps = {
        "CAPEX_structured_max_MUSD": _safe_float(outputs, "CAPEX_structured_max_MUSD", default=float("nan")),
        "OPEX_structured_max_MUSD_per_y": _safe_float(outputs, "OPEX_structured_max_MUSD_per_y", default=float("nan")),
        "LCOE_lite_max_USD_per_MWh": _safe_float(outputs, "LCOE_lite_max_USD_per_MWh", default=float("nan")),
    }

    # Context: show which governance signals influenced tiering.
    ctx = {
        "disruption_proximity_index": _safe_float(outputs, "disruption_proximity_index"),
        "control_power_margin": _safe_float(outputs, "control_power_margin_cert_v378", "control_power_margin"),
        "volt_second_headroom": _safe_float(outputs, "volt_second_headroom_frac", "volt_second_headroom"),
        "thermal_quench_severity_W_per_m2": _safe_float(outputs, "thermal_quench_severity_W_per_m2", "thermal_quench_proxy"),
        "inputs_present": bool(isinstance(inputs, dict) and len(inputs or {}) > 0),
    }

    # Sanity: if lcoe is inf and net is finite, replace with nan for presentation.
    if not _finite(lcoe) and _finite(net) and net > 0:
        lcoe = float("nan")

    return PlantEconomicsCertificationV383(
        contract_sha256=_contract_sha256(),
        capex_MUSD=float(capex) if _finite(capex) else float("nan"),
        opex_MUSD_per_y=float(opex) if _finite(opex) else float("nan"),
        lcoe_USD_per_MWh=float(lcoe) if _finite(lcoe) else float("nan"),
        tier=str(tier),
        capacity_factor=float(cf) if _finite(cf) else float("nan"),
        net_MWh_per_year=float(net) if _finite(net) else float("nan"),
        dominant_driver=str(dom),
        dominant_frac=float(domf) if _finite(domf) else float("nan"),
        caps={k: float(v) for k, v in caps.items()},
        ctx={k: (float(v) if isinstance(v, (int, float)) and _finite(float(v)) else v) for k, v in ctx.items()},
    )


def certification_table_rows(cert: Dict[str, Any]) -> Dict[str, Any]:
    """Flattened table row for UI DataFrame rendering."""
    metrics = cert.get("metrics", {}) if isinstance(cert, dict) else {}
    return {
        "Tier": metrics.get("availability_tier_v383", ""),
        "CAPEX_structured (MUSD)": metrics.get("CAPEX_structured_v383_MUSD", float("nan")),
        "OPEX_structured (MUSD/y)": metrics.get("OPEX_structured_v383_MUSD_per_y", float("nan")),
        "LCOE_lite (USD/MWh)": metrics.get("LCOE_lite_v383_USD_per_MWh", float("nan")),
        "CF_used": metrics.get("capacity_factor_used_v383", float("nan")),
        "Net_MWh/y": metrics.get("net_electric_MWh_per_year_used_v383", float("nan")),
        "Dominant driver": metrics.get("dominant_cost_driver_v383", ""),
        "Dominant frac": metrics.get("dominant_cost_frac_v383", float("nan")),
    }
