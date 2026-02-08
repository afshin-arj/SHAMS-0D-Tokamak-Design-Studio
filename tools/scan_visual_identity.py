"""Scan Lab visual identity (frozen semantics).

This module centralizes the constraint→color mapping for Scan Lab cartography.
The goal is scientific clarity and long-term consistency: the same constraint
should always appear with the same color across SHAMS versions.

Freeze rule:
- Do not change existing mappings post-freeze.
- New constraints may be appended with new colors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class VisualIdentity:
    version: str
    constraint_colors: Dict[str, str]
    fallback_palette: Tuple[str, ...]


# Canonical constraint names in SHAMS are typically short ("q_div", "sigma_vm", "TBR", etc.).
# We keep a conservative mapping and normalize lookups.
_CONSTRAINT_COLORS: Dict[str, str] = {
    # Core / always-seen
    "q_div": "#E45756",        # red
    "sigma_vm": "#4C78A8",     # blue
    "hts margin": "#F58518",   # orange
    "hts_margin": "#F58518",
    "tbr": "#54A24B",          # green
    "q95": "#B279A2",          # purple
    # Common alternates / label variants
    "hts": "#F58518",
    "stress": "#4C78A8",
    "wall": "#E45756",
}


_FALLBACK: Tuple[str, ...] = (
    "#E0E0E0",  # neutral
    "#4C78A8",
    "#F58518",
    "#54A24B",
    "#E45756",
    "#72B7B2",
    "#B279A2",
    "#FF9DA6",
    "#9D755D",
    "#BAB0AC",
    "#2F4B7C",
    "#7A5195",
    "#EF5675",
    "#FFA600",
)


VISUAL_IDENTITY = VisualIdentity(
    version="scanlab_visual_v1",
    constraint_colors=_CONSTRAINT_COLORS,
    fallback_palette=_FALLBACK,
)


def normalize_constraint_name(name: str) -> str:
    n = (name or "").strip().lower()
    n = n.replace("_", " ")
    # keep short aliases
    if n.startswith("hts") and "margin" in n:
        return "hts margin"
    if n.startswith("sigma"):
        return "sigma_vm"
    if n in ("tbr", "tbr min"):
        return "tbr"
    if n.startswith("q div"):
        return "q_div"
    return n


def color_for_constraint(name: str) -> str:
    key = normalize_constraint_name(name)
    if key in VISUAL_IDENTITY.constraint_colors:
        return VISUAL_IDENTITY.constraint_colors[key]
    # attempt partial matches
    for k, v in VISUAL_IDENTITY.constraint_colors.items():
        if k and k in key:
            return v
    # fallback: deterministic pick from palette
    idx = (sum(ord(c) for c in key) % max(len(VISUAL_IDENTITY.fallback_palette), 1))
    return VISUAL_IDENTITY.fallback_palette[idx]


def build_palette(labels: List[str]) -> List[str]:
    """Build a palette aligned with labels, using frozen mapping where possible."""
    return [color_for_constraint(l) for l in (labels or [])]
