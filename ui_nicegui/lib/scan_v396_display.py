"""Scan Lab UI-only helpers for optional v396 transport envelope fields."""
from __future__ import annotations

from typing import Any, Mapping, Optional


def _finite(x: Any) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    return v


def extract_v396_transport(out: Optional[Mapping[str, Any]]) -> Optional[dict[str, Any]]:
    """Return spread/tier when present on point or cell outputs; else None."""
    if not isinstance(out, Mapping):
        return None
    spread = _finite(out.get("transport_spread_ratio_v396"))
    tier = str(out.get("transport_credibility_tier_v396") or "").strip()
    if spread is None and not tier:
        return None
    return {
        "spread": spread,
        "tier": tier or None,
        "tau_min": _finite(out.get("tauE_envelope_min_s_v396")),
        "tau_max": _finite(out.get("tauE_envelope_max_s_v396")),
    }


def format_v396_caption(info: Mapping[str, Any]) -> str:
    """Plain caption for results / probe strips (PROXY screening, not a solver)."""
    bits: list[str] = []
    spread = info.get("spread")
    if isinstance(spread, float):
        bits.append(f"spread τE_max/τE_min={spread:.3g}")
    tier = info.get("tier")
    if tier:
        bits.append(f"tier={tier}")
    return " · ".join(bits) if bits else ""
