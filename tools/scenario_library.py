from __future__ import annotations

"""UQ-lite Scenario Library (v246.0).

This library provides *fixed*, deterministic scenario factor presets keyed to:
- authority tier (proxy / parametric / external)
- machine intent (research / reactor)

These are intended for the *external* optimizer client selection layer:
- They do not modify physics truth.
- They provide reviewer-safe sensitivity screening via a deterministic scenario cube.

Factor semantics
----------------
Each entry is a multiplicative factor pair [lo, hi] applied to a numeric PointInputs key.

Guiding principle: tighter bounds for higher-authority inputs (external) and
more aggressive envelopes for research-intent exploratory studies.

© 2026 Afshin Arjhangmehr
"""

from typing import Dict, List, Literal

Authority = Literal["proxy", "parametric", "external"]
Intent = Literal["research", "reactor"]

# Keys chosen to be broadly present across SHAMS PointInputs evolutions.
_BASE_KEYS = ("Paux_MW", "fG", "Ti_keV", "Te_keV", "Zeff", "H98")

_PRESETS: Dict[str, Dict[str, Dict[str, List[float]]]] = {
    "research": {
        "proxy": {
            "Paux_MW": [0.90, 1.10],
            "fG": [0.92, 1.08],
            "Ti_keV": [0.92, 1.08],
            "Te_keV": [0.92, 1.08],
            "Zeff": [0.95, 1.10],
            "H98": [0.92, 1.08],
        },
        "parametric": {
            "Paux_MW": [0.93, 1.07],
            "fG": [0.95, 1.05],
            "Ti_keV": [0.95, 1.05],
            "Te_keV": [0.95, 1.05],
            "Zeff": [0.97, 1.07],
            "H98": [0.95, 1.05],
        },
        "external": {
            "Paux_MW": [0.96, 1.04],
            "fG": [0.97, 1.03],
            "Ti_keV": [0.97, 1.03],
            "Te_keV": [0.97, 1.03],
            "Zeff": [0.98, 1.05],
            "H98": [0.97, 1.03],
        },
    },
    "reactor": {
        "proxy": {
            "Paux_MW": [0.93, 1.07],
            "fG": [0.95, 1.05],
            "Ti_keV": [0.95, 1.05],
            "Te_keV": [0.95, 1.05],
            "Zeff": [0.97, 1.07],
            "H98": [0.95, 1.05],
        },
        "parametric": {
            "Paux_MW": [0.95, 1.05],
            "fG": [0.97, 1.03],
            "Ti_keV": [0.97, 1.03],
            "Te_keV": [0.97, 1.03],
            "Zeff": [0.98, 1.05],
            "H98": [0.97, 1.03],
        },
        "external": {
            "Paux_MW": [0.97, 1.03],
            "fG": [0.98, 1.02],
            "Ti_keV": [0.98, 1.02],
            "Te_keV": [0.98, 1.02],
            "Zeff": [0.99, 1.03],
            "H98": [0.98, 1.02],
        },
    },
}


def preset_names() -> List[str]:
    return [
        "proxy (research)",
        "parametric (research)",
        "external (research)",
        "proxy (reactor)",
        "parametric (reactor)",
        "external (reactor)",
    ]


def get_preset(name: str) -> Dict[str, List[float]]:
    """Return a scenario_factors dict for a preset name.

    Unknown names return a conservative minimal default.
    """
    n = str(name).strip().lower()
    # parse
    intent: Intent = "research" if "research" in n else ("reactor" if "reactor" in n else "research")
    authority: Authority = "proxy"
    for a in ("external", "parametric", "proxy"):
        if a in n:
            authority = a  # type: ignore
            break
    try:
        d = _PRESETS[intent][authority]
        return {k: [float(v[0]), float(v[1])] for k, v in d.items()}
    except Exception:
        return {"Paux_MW": [0.95, 1.05], "fG": [0.95, 1.05], "Ti_keV": [0.95, 1.05]}
