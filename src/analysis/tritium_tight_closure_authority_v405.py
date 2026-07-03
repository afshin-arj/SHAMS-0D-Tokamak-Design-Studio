"""Tritium tight-closure authority overlay (PHYS-005)."""
from __future__ import annotations

from typing import Any, Dict

try:
    from fuel_cycle.tritium_authority import compute_tritium_authority  # type: ignore
except ImportError:
    from ..fuel_cycle.tritium_authority import compute_tritium_authority  # type: ignore


def evaluate_tritium_tight_closure_authority_v405(out: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    """Post-truth fuel-cycle overlay; echoes caps for registry constraints."""
    inp_dict = dict(getattr(inp, "__dict__", {}))
    patch = compute_tritium_authority(out, inp_dict)
    patch["include_tritium_tight_closure"] = float(bool(getattr(inp, "include_tritium_tight_closure", False)))
    return patch
