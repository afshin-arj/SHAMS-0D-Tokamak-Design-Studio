from __future__ import annotations
"""Preference schema helpers (v114)

Preferences are *post-feasibility* annotations (no optimization).
They must be explicit, reversible, and audit-friendly.

A preference payload is a dict like:
{
  "kind": "shams_preferences",
  "version": "v114",
  "created_utc": "...",
  "weights": {
     "robustness": 1.0,
     "margin": 1.0,
     "boundary_clearance": 1.0,
     "size": 0.5
  },
  "rules": [
     {"type":"avoid", "metric":"worst_hard", "equals":"density_limit", "penalty": 0.2},
     {"type":"prefer_high", "metric":"Bt_T", "weight": 0.2}
  ],
  "notes": [...]
}

- weights: controls composite score (0..1) from derived metrics
- rules: optional transparent modifiers
"""

from typing import Any, Dict, List
import time

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def template_preferences(version: str = "v114") -> Dict[str, Any]:
    return {
        "kind": "shams_preferences",
        "version": version,
        "created_utc": _created_utc(),
        "weights": {
            "robustness": 1.0,
            "margin": 1.0,
            "boundary_clearance": 1.0,
            "size": 0.5,
        },
        "rules": [],
        "notes": [
            "Preferences are post-feasibility annotations. They do not affect physics or solver behavior.",
            "Weights should be interpreted as relative importance (all optional).",
        ],
    }

def validate_preferences(prefs: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if not isinstance(prefs, dict):
        return ["prefs_not_dict"]
    if prefs.get("kind") != "shams_preferences":
        errs.append("kind_mismatch")
    w = prefs.get("weights", {})
    if not isinstance(w, dict):
        errs.append("weights_not_dict")
    else:
        for k, v in w.items():
            if not isinstance(k, str):
                errs.append("weight_key_not_str")
            try:
                float(v)
            except Exception:
                errs.append(f"weight_{k}_not_numeric")
    r = prefs.get("rules", [])
    if r is not None and not isinstance(r, list):
        errs.append("rules_not_list")
    return errs
