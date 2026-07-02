"""Back-compat shim (Tier-3 B2a reconciliation).

Canonical implementation: repo-root ``analysis/transport_envelope_v396.py``.
"""
from __future__ import annotations

from analysis._canonical_shim import load_canonical

_mod = load_canonical("transport_envelope_v396")
evaluate_transport_envelope_v396 = _mod.evaluate_transport_envelope_v396

for _name in dir(_mod):
    if _name.startswith("_"):
        continue
    globals()[_name] = getattr(_mod, _name)
