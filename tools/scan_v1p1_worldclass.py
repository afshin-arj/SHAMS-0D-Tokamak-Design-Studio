"""Scan Lab — v1.1+ interpretability additions (still 0‑D, non‑optimizing).

Deterministic utilities over already-evaluated Scan Lab reports.

These helpers are intentionally descriptive (no recommendation language).
"""

from __future__ import annotations

import json
import math
import platform
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def build_constraint_dictionary() -> Dict[str, Dict[str, str]]:
    """Return a small, high-signal constraint dictionary.

    UI may treat this as a glossary. Unknown constraints should fall back to
    generic text.
    """

    return {
        "q_div": {
            "physics": "Divertor heat flux limit in the power exhaust channel.",
            "engineering": "Often sets the exhaust / plasma-facing component envelope.",
            "shifts": "Boundaries move with power flow, geometry, and edge handling assumptions.",
        },
        "sigma_vm": {
            "physics": "Structural von Mises stress limit in key load-bearing components.",
            "engineering": "Often sets coil/case thickness and allowable fields/forces.",
            "shifts": "Boundaries move with field level, geometry, and allowable stress policy.",
        },
        "HTS margin": {
            "physics": "Superconductor operating margin to critical surface.",
            "engineering": "Often limits peak field / temperature operating point.",
            "shifts": "Boundaries move with B,T operating point and HTS performance assumptions.",
        },
        "TBR": {
            "physics": "Tritium breeding ratio requirement (blanket neutronics proxy).",
            "engineering": "Often limits blanket/shield thickness and plant layout assumptions.",
            "shifts": "Boundaries move with blanket fraction, materials, and policy thresholds.",
        },
        "q95": {
            "physics": "Edge safety factor constraint / operational stability proxy.",
            "engineering": "Often limits current, shape, and operational space.",
            "shifts": "Boundaries move with Ip, shaping, and equilibrium assumptions.",
        },
    }


def _safe_float(x: Any) -> Optional[float]:
    try:
        v = float(x)
    except Exception:
        return None
    if not math.isfinite(v):
        return None
    return v


def build_reproducibility_capsule(
    *,
    artifact: Optional[Dict[str, Any]] = None,
    report: Optional[Dict[str, Any]] = None,
    evaluator_fingerprint: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a publication-grade reproducibility capsule.

    This is a pure metadata summary meant to be exported alongside scan artifacts.
    """

    capsule: Dict[str, Any] = {
        "created_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "python": {
            "version": sys.version.split(" ")[0],
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "scan": {},
        "fingerprints": evaluator_fingerprint or {},
    }

    src = report or (artifact.get("report") if isinstance(artifact, dict) else None) or {}
    if isinstance(src, dict):
        capsule["scan"] = {
            "schema": (artifact or {}).get("schema") if isinstance(artifact, dict) else None,
            "intent": (artifact or {}).get("intent") if isinstance(artifact, dict) else src.get("intent"),
            "x_key": src.get("x_key"),
            "y_key": src.get("y_key"),
            "grid": {
                "nx": src.get("nx"),
                "ny": src.get("ny"),
            },
            "slice": src.get("slice"),
            "sampling": src.get("sampling"),
            "seed": src.get("seed"),
        }

    return capsule


def monotonicity_sanity_overlay(*, report: Dict[str, Any], intent: str) -> Dict[str, Any]:
    """Lightweight monotonicity/sanity overlay.

    Computes how often min_blocking_margin decreases along increasing x (row-wise)
    and increasing y (col-wise) among feasible points.

    Not a correctness check; flags *surprising* structure.
    """

    pts = report.get("points") or []
    # index by (i,j)
    by_ij: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for r in pts:
        try:
            i = int(r.get("i"))
            j = int(r.get("j"))
        except Exception:
            continue
        by_ij[(i, j)] = r

    def m(i: int, j: int) -> Optional[float]:
        r = by_ij.get((i, j))
        if not r:
            return None
        it = ((r.get("intent") or {}).get(intent) or {})
        if not bool(it.get("blocking_feasible")):
            return None
        return _safe_float(it.get("min_blocking_margin"))

    nx = int(report.get("nx") or 0)
    ny = int(report.get("ny") or 0)
    if nx <= 1 or ny <= 1:
        return {"ok": False, "reason": "grid_too_small"}

    checks_x = 0
    viol_x = 0
    for j in range(ny):
        for i in range(nx - 1):
            a = m(i, j)
            b = m(i + 1, j)
            if a is None or b is None:
                continue
            checks_x += 1
            if b < a:
                viol_x += 1

    checks_y = 0
    viol_y = 0
    for i in range(nx):
        for j in range(ny - 1):
            a = m(i, j)
            b = m(i, j + 1)
            if a is None or b is None:
                continue
            checks_y += 1
            if b < a:
                viol_y += 1

    return {
        "ok": True,
        "x": {
            "checks": checks_x,
            "violations": viol_x,
            "violation_rate": (viol_x / checks_x) if checks_x else None,
        },
        "y": {
            "checks": checks_y,
            "violations": viol_y,
            "violation_rate": (viol_y / checks_y) if checks_y else None,
        },
        "note": "Low rates suggest locally monotone structure in this slice; high rates suggest coupled effects.",
    }


def boundary_thickness_metric(*, report: Dict[str, Any], intent: str) -> Dict[str, Any]:
    """Estimate boundary thickness as a proxy.

    We call a cell part of a 'transition band' if its 8-neighborhood contains both
    feasible and infeasible points (blocking_feasible).

    Returns fraction of evaluated cells in the band.
    """

    pts = report.get("points") or []
    by_ij: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for r in pts:
        try:
            i = int(r.get("i"))
            j = int(r.get("j"))
        except Exception:
            continue
        by_ij[(i, j)] = r

    def feas(i: int, j: int) -> Optional[bool]:
        r = by_ij.get((i, j))
        if not r:
            return None
        it = ((r.get("intent") or {}).get(intent) or {})
        return bool(it.get("blocking_feasible"))

    nx = int(report.get("nx") or 0)
    ny = int(report.get("ny") or 0)
    if nx <= 0 or ny <= 0:
        return {"ok": False, "reason": "no_grid"}

    total = 0
    band = 0
    for i in range(nx):
        for j in range(ny):
            f0 = feas(i, j)
            if f0 is None:
                continue
            total += 1
            neigh = []
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ff = feas(i + di, j + dj)
                    if ff is None:
                        continue
                    neigh.append(ff)
            if neigh and (any(neigh) != all(neigh)):
                band += 1

    return {
        "ok": True,
        "evaluated_cells": total,
        "transition_cells": band,
        "transition_fraction": (band / total) if total else None,
        "note": "Proxy thickness of the feasibility boundary band in this 2D slice.",
    }


def explain_uncertainty_disagreement(*, report: Dict[str, Any], intent: str) -> Dict[str, Any]:
    """Explain disagreement between nominal feasibility and local uncertainty feasibility.

    Uses intent fields:
      - blocking_feasible (nominal)
      - local_p_feasible (if available; [0,1])

    Returns summary counts and top dominant constraints where flips occur.
    """

    pts = report.get("points") or []
    flips = 0
    considered = 0
    dom: Dict[str, int] = {}

    for r in pts:
        it = ((r.get("intent") or {}).get(intent) or {})
        nom = bool(it.get("blocking_feasible"))
        p = _safe_float(it.get("local_p_feasible"))
        if p is None:
            continue
        considered += 1
        worst = bool(p >= 0.999)  # interpret as "robust" for display
        if nom and not worst:
            flips += 1
            d = str(it.get("dominant_blocking") or "(unknown)")
            dom[d] = dom.get(d, 0) + 1

    top = sorted(dom.items(), key=lambda kv: (-kv[1], kv[0]))[:5]

    return {
        "ok": True,
        "considered": considered,
        "nominal_feasible_but_not_robust": flips,
        "top_dominants": top,
        "note": "Shows where nominal feasibility is sensitive under the local uncertainty lens (if available).",
    }


def to_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, indent=2, sort_keys=True).encode("utf-8")
