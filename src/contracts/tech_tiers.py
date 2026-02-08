from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Mapping

"""Technology readiness (TRL) contract tiers.

This module is GOVERNANCE-ONLY:
- No solvers, no iteration.
- It may be used to label assumptions and provide explicit suggested defaults
  for optional constraint caps in exploration layers.

Frozen truth is unaffected unless the user explicitly sets inputs that
participate in physics equations.
"""


# Minimal tier metadata. Keep conservative language and avoid false precision.
TIERS: Dict[str, Dict[str, Any]] = {
    "TRL3": {
        "tier": "TRL3",
        "description": "Early R&D; optimistic extrapolation risk high.",
        # Suggested defaults for optional caps (users may override explicitly).
        "suggested": {
            "f_recirc_max": 0.6,
            "P_nuc_tf_max_MW": 50.0,
            "TBR_min": 1.05,
        },
    },
    "TRL5": {
        "tier": "TRL5",
        "description": "Component validation; moderate extrapolation risk.",
        "suggested": {
            "f_recirc_max": 0.5,
            "P_nuc_tf_max_MW": 30.0,
            "TBR_min": 1.10,
        },
    },
    "TRL7": {
        "tier": "TRL7",
        "description": "System prototype; conservative design targeting.",
        "suggested": {
            "f_recirc_max": 0.4,
            "P_nuc_tf_max_MW": 20.0,
            "TBR_min": 1.15,
        },
    },
    "TRL9": {
        "tier": "TRL9",
        "description": "Operationally demonstrated; strict margins expected.",
        "suggested": {
            "f_recirc_max": 0.35,
            "P_nuc_tf_max_MW": 15.0,
            "TBR_min": 1.20,
        },
    },
}


def normalize_tech_tier(tier: str | None) -> str:
    if tier is None:
        return "TRL7"
    t = str(tier).strip().upper()
    return t if t in TIERS else "TRL7"


def compute_maturity_contract(inp: Any) -> Dict[str, Any]:
    """Compute the maturity contract dict for outputs.

    Parameters
    ----------
    inp:
        PointInputs-like object.

    Returns
    -------
    dict:
        Stable, JSON-serializable contract dictionary.
    """
    tier = normalize_tech_tier(getattr(inp, "tech_tier", "TRL7"))
    base = dict(TIERS.get(tier, TIERS["TRL7"]))

    # Include a small fingerprint of selected technology knobs for traceability.
    fingerprint: Dict[str, Any] = {}
    for k in (
        "magnet_technology",
        "hts_Jc_mult",
        "lambda_q_mult",
        "confinement_mult",
        "blanket_type",
        "multiplier_material",
        "li6_enrichment",
    ):
        try:
            v = getattr(inp, k)
        except Exception:
            continue
        try:
            # keep it JSON-friendly
            fingerprint[k] = v if isinstance(v, (int, float, str, bool)) else str(v)
        except Exception:
            fingerprint[k] = str(v)

    base["fingerprint"] = fingerprint
    return base


def suggested_defaults(tier: str) -> Mapping[str, Any]:
    """Return suggested defaults for a tier (does not mutate inputs)."""
    t = normalize_tech_tier(tier)
    return dict(TIERS[t].get("suggested", {}))
