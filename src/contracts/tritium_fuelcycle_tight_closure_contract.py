from __future__ import annotations

"""v350.0 — Tritium & Fuel Cycle Tight Closure (contract wrapper)

Deterministic algebraic ledger used by ``src.fuel_cycle.tritium_authority``.
This module fingerprints the governing contract and provides stable result
containers for authority stamping.

Author: © 2026 Afshin Arjhangmehr
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

_CONTRACT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "tritium_fuelcycle_tight_closure_contract.json"


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load_contract() -> Dict[str, Any]:
    return json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))


CONTRACT: Dict[str, Any] = _load_contract()
CONTRACT_SHA256: str = _sha256_file(_CONTRACT_PATH)


@dataclass(frozen=True)
class TritiumFuelCycleResult:
    """Authority outputs + validity ledger."""

    T_burn_kg_per_day: float
    T_inventory_reserve_kg: float
    T_in_vessel_required_kg: float
    T_startup_inventory_kg: float
    T_total_inventory_required_kg: float
    T_processing_required_g_per_day: float
    TBR_required_fuelcycle: float
    TBR_eff_fuelcycle: float
    TBR_self_sufficiency_required: float
    TBR_self_sufficiency_margin: float
    validity: Dict[str, str]
