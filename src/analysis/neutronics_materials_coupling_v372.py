"""Back-compat shim (Tier-3 B2a reconciliation).

Canonical implementation: repo-root ``analysis/neutronics_materials_coupling_v372.py``.
"""
from __future__ import annotations

from analysis._canonical_shim import load_canonical

_mod = load_canonical("neutronics_materials_coupling_v372")
evaluate_neutronics_materials_coupling_v372 = _mod.evaluate_neutronics_materials_coupling_v372

for _name in dir(_mod):
    if _name.startswith("_"):
        continue
    globals()[_name] = getattr(_mod, _name)
