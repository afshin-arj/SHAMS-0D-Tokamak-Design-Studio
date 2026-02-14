from __future__ import annotations
"""Literature Overlay (v112)

Adds a *user-supplied* reference overlay layer for SHAMS plots (topology/boundary).
No external downloads, no embedded external datasets.

Input format (JSON):
{
  "kind": "shams_literature_points",
  "version": "v112",
  "created_utc": "...",
  "points": [
    {
      "name": "ARC (Sorbom 2015)",
      "inputs": {"R0_m": 3.3, "Bt_T": 9.2, "Ip_MA": 7.8, ...},
      "meta": {"citation": "Sorbom et al., Fusion Eng. Des. 100 (2015) ..."}
    }
  ]
}

This module provides:
- validate_literature_points(payload): lightweight checks
- extract_xy_points(payload, kx, ky): for plotting overlays
"""

from typing import Any, Dict, List, Tuple, Optional
import time

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

def template_payload(version: str = "v112") -> Dict[str, Any]:
    return {
        "kind": "shams_literature_points",
        "version": version,
        "created_utc": _created_utc(),
        "points": [],
        "notes": [
            "User-supplied overlay points. SHAMS does not ship third-party datasets.",
            "Each point should include at least the lever keys you want to overlay (e.g., R0_m, Bt_T).",
        ],
    }

def validate_literature_points(payload: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if not isinstance(payload, dict):
        return ["payload_not_dict"]
    if payload.get("kind") != "shams_literature_points":
        errs.append("kind_mismatch")
    pts = payload.get("points")
    if pts is None:
        errs.append("missing_points")
        return errs
    if not isinstance(pts, list):
        errs.append("points_not_list")
        return errs
    for i, p in enumerate(pts[:5000]):
        if not isinstance(p, dict):
            errs.append(f"point_{i}_not_dict")
            continue
        if not isinstance(p.get("name"), str):
            errs.append(f"point_{i}_missing_name")
        inp = p.get("inputs")
        if not isinstance(inp, dict):
            errs.append(f"point_{i}_missing_inputs")
            continue
        # allow non-numeric values, but warn if none numeric
        numeric = any(_is_num(v) for v in inp.values())
        if not numeric:
            errs.append(f"point_{i}_no_numeric_inputs")
    return errs

def extract_xy_points(payload: Dict[str, Any], kx: str, ky: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not isinstance(payload, dict):
        return out
    pts = payload.get("points", [])
    if not isinstance(pts, list):
        return out
    for p in pts:
        if not isinstance(p, dict):
            continue
        name = p.get("name")
        inp = p.get("inputs", {})
        if not (isinstance(name, str) and isinstance(inp, dict)):
            continue
        if _is_num(inp.get(kx)) and _is_num(inp.get(ky)):
            out.append({"name": name, kx: float(inp[kx]), ky: float(inp[ky]), "meta": p.get("meta", {})})
    return out
