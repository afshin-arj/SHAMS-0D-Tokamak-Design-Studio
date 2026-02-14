from __future__ import annotations

"""Golden scans (institutional memory) for Scan Lab.

Golden scans serve three purposes:
1) Teaching: canonical landscapes that build intuition.
2) QA: deterministic regression checks for Scan Lab plumbing.
3) Demos: one-click "show me the map" experiences.

They are **not** recommendations and must never be auto-applied.
"""

from dataclasses import replace
from typing import Any, Dict, List


def _safe_replace(inp, **kw):
    try:
        return replace(inp, **kw)
    except Exception:
        d = dict(getattr(inp, "__dict__", {}) or {})
        d.update(kw)
        return type(inp)(**d)


def build_golden_scan_presets(*, base_inputs) -> List[Dict[str, Any]]:
    """Return a list of golden scan presets.

    Each preset defines:
      - label
      - intent(s)
      - x/y keys
      - x/y ranges (relative to base)
      - optional base override (still within 0-D PointInputs)
    """
    b = base_inputs

    # If base is missing expected attributes, fall back gracefully.
    R0 = float(getattr(b, "R0_m", 2.5) or 2.5)
    a = float(getattr(b, "a_m", 0.8) or 0.8)
    Bt = float(getattr(b, "Bt_T", 10.0) or 10.0)
    Ip = float(getattr(b, "Ip_MA", 8.0) or 8.0)
    fG = float(getattr(b, "fG", 0.8) or 0.8)
    Paux = float(getattr(b, "Paux_MW", 30.0) or 30.0)

    presets: List[Dict[str, Any]] = []

    # 1) ITER-like teaching map: Ip vs R0 under Reactor intent
    presets.append(
        {
            "id": "GOLDEN|REACTOR|MAP|IP_R0|LARGE_LTS",
            "label": "GOLDEN | REACTOR | Ip vs R0 | Large-machine (LTS/ITER-like)",
            "note": "Canonical large-machine landscape (Reactor lens). Dominance shows stress vs exhaust vs q95 boundaries.",
            "intents": ["Reactor"],
            "x_key": "Ip_MA",
            "y_key": "R0_m",
            "x_range": [max(0.2, 0.6 * Ip), 1.4 * Ip],
            "y_range": [max(0.5, 0.75 * R0), 1.25 * R0],
            "n_x": 31,
            "n_y": 25,
            "base_override": {
                # Keep it conservative and slow (large R0, moderate Bt)
                "Bt_T": max(5.0, 0.7 * Bt),
                "Paux_MW": max(20.0, Paux),
                "fG": min(0.95, max(0.6, fG)),
            },
        }
    )

    # 2) Compact high-field: Bt vs R0 under Reactor intent
    presets.append(
        {
            "id": "GOLDEN|REACTOR|MAP|BT_R0|COMPACT_HTS",
            "label": "GOLDEN | REACTOR | Bt vs R0 | Compact high-field (HTS)",
            "note": "Compact high-field landscape (Reactor lens). Shows magnet/HTS limits vs size; ARC/SPARC intuition.",
            "intents": ["Reactor"],
            "x_key": "Bt_T",
            "y_key": "R0_m",
            "x_range": [max(2.0, 0.6 * Bt), 1.35 * Bt],
            "y_range": [max(0.6, 0.55 * R0), 1.05 * R0],
            "n_x": 31,
            "n_y": 25,
            "base_override": {
                "Ip_MA": max(4.0, 0.9 * Ip),
                "a_m": max(0.25, 0.85 * a),
            },
        }
    )

    # 3) Research extreme: Ip vs fG under Research vs Reactor intents
    presets.append(
        {
            "id": "GOLDEN|INTENT_SPLIT|MAP|IP_FG|RESEARCH_EXTREMES",
            "label": "GOLDEN | INTENT-SPLIT | Ip vs fG | Research extremes",
            "note": "Intent split demonstration: Research-feasible regions can remain large when Reactor feasibility collapses.",
            "intents": ["Research", "Reactor"],
            "x_key": "Ip_MA",
            "y_key": "fG",
            "x_range": [max(0.2, 0.5 * Ip), 1.8 * Ip],
            "y_range": [0.25, 1.15],
            "n_x": 33,
            "n_y": 24,
            "base_override": {
                "R0_m": max(0.9, 0.9 * R0),
                "Bt_T": max(3.0, 0.75 * Bt),
                "Paux_MW": max(5.0, 0.6 * Paux),
            },
        }
    )

    # Attach realized base inputs for each preset (so UI can show exact values)
    out: List[Dict[str, Any]] = []
    for p in presets:
        bo = dict(p.get("base_override") or {})
        inp2 = _safe_replace(b, **bo) if bo else b
        p2 = dict(p)
        p2["base_inputs"] = inp2
        out.append(p2)
    return out
