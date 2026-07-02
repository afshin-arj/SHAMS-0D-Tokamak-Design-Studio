"""Back-compat shim (Tier-3 B2a reconciliation).

Canonical implementation: repo-root ``analysis/materials_lifetime_v384.py``.
"""
from __future__ import annotations

from analysis._canonical_shim import load_canonical

_mod = load_canonical("materials_lifetime_v384")
compute_materials_lifetime_tightening_v384 = _mod.compute_materials_lifetime_tightening_v384

for _name in dir(_mod):
    if _name.startswith("_"):
        continue
    globals()[_name] = getattr(_mod, _name)
