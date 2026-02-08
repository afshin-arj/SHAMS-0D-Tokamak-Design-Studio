"""PROCESS Parity Layer (PPL).

This package provides *optional* PROCESS-like plant/accounting layers implemented
natively in SHAMS (no dependency on PROCESS).

These blocks are intended for **systems studies** and **optimization objectives**.
They sit *on top* of the frozen 0-D evaluator:

* The evaluator physics + constraints remain the source of truth.
* Parity blocks add transparent bookkeeping (plant closure), component proxies
  (e.g., magnets, cryo) and economics.

Contract
--------
* Pure functions: inputs/outputs in → derived quantities out.
* No hidden mutation of session state.
* Every block returns a small **assumptions** dict to make the layer auditable.
"""

from .plant_closure import parity_plant_closure
from .magnets import parity_magnets
from .cryo import parity_cryo
from .costing import parity_costing, parity_costing_envelope

__all__ = [
    "parity_plant_closure",
    "parity_magnets",
    "parity_cryo",
    "parity_costing",
    "parity_costing_envelope",
]

from .plant_closure import parity_plant_closure
from .magnets import parity_magnets
from .cryo import parity_cryo
from .costing import parity_costing, parity_costing_envelope
from .report_pack import build_parity_report_pack

__all__ = [
    "parity_plant_closure",
    "parity_magnets",
    "parity_cryo",
    "parity_costing",
    "parity_costing_envelope",
    "build_parity_report_pack",
]

from .validation_packs import ValidationPack, load_validation_packs, evaluate_pack_candidate, compare_to_reference
__all__ += ["ValidationPack", "load_validation_packs", "evaluate_pack_candidate", "compare_to_reference"]
