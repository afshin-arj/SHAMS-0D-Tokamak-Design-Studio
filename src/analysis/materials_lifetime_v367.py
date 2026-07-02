"""Back-compat shim (Tier-3 B2a reconciliation).

Canonical implementation: repo-root ``analysis/materials_lifetime_v367.py``.
"""
from __future__ import annotations

from analysis._canonical_shim import load_canonical

_mod = load_canonical("materials_lifetime_v367")
compute_materials_lifetime_closure_v367 = _mod.compute_materials_lifetime_closure_v367

for _name in dir(_mod):
    if _name.startswith("_"):
        continue
    globals()[_name] = getattr(_mod, _name)
