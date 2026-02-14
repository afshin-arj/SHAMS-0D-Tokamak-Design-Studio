from __future__ import annotations

"""Cartography 2.0 derived layers for Scan Lab.

This module is *post-processing only*: it consumes an atlas produced from the
frozen evaluator and adds deterministic classification + summaries.

Definitions
  - A cell is feasible if atlas['dominant'][i][j] == 'ok' (or atlas['feasible'][i][j] is True)
  - min_margin is the signed fractional margin of the dominant hard constraint

Classification
  - robust: feasible and min_margin >= robust_margin_min
  - fragile: feasible and min_margin < robust_margin_min
  - empty: not feasible
"""

from typing import Any, Dict, List
from collections import Counter
import math


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float('nan')


def classify_cells(atlas: Dict[str, Any], *, robust_margin_min: float = 0.10) -> Dict[str, Any]:
    feasible = atlas.get('feasible')
    dominant = atlas.get('dominant')
    min_margin = atlas.get('min_margin')
    if not isinstance(dominant, list) or not isinstance(min_margin, list):
        return {'ok': False, 'reason': 'missing_grids'}

    nx = len(dominant)
    ny = len(dominant[0]) if nx > 0 and isinstance(dominant[0], list) else 0

    labels: List[List[str]] = [["" for _ in range(ny)] for __ in range(nx)]
    for i in range(nx):
        for j in range(ny):
            dom = str(dominant[i][j])
            ok = bool(feasible[i][j]) if isinstance(feasible, list) else (dom == 'ok')
            mm = _safe_float(min_margin[i][j])
            if not ok:
                labels[i][j] = 'empty'
            else:
                labels[i][j] = 'robust' if (math.isfinite(mm) and mm >= robust_margin_min) else 'fragile'

    return {
        'ok': True,
        'robust_margin_min': float(robust_margin_min),
        'labels': labels,
        'schema_version': 'cartography2.v1',
    }


def mechanism_histogram(atlas: Dict[str, Any]) -> Dict[str, int]:
    dom = atlas.get('dominant')
    if not isinstance(dom, list):
        return {}
    c = Counter()
    for row in dom:
        if not isinstance(row, list):
            continue
        for x in row:
            s = str(x)
            if not s:
                continue
            c[s] += 1
    return dict(c)


def label_fractions(labels: List[List[str]]) -> Dict[str, float]:
    c = Counter()
    n = 0
    for row in labels:
        for x in row:
            c[str(x)] += 1
            n += 1
    if n <= 0:
        return {}
    return {k: v / n for k, v in c.items()}

# --- v227.0: mechanism group overlays (control-aware) ---

def mechanism_group(name: str) -> str:
    s = str(name).lower()
    # Control / dynamics contracts
    if 'vs control' in s or 'pf waveform' in s or 'sol radiation fraction required' in s:
        return 'CONTROL'
    # Exhaust / divertor
    if 'divertor' in s or 'q_parallel' in s or 'q||' in s or 'sol' in s:
        return 'EXHAUST'
    # MHD / limits
    if 'mhd' in s or 'beta' in s or 'q95' in s or 'greenwald' in s:
        return 'PLASMA_LIMITS'
    # Magnets / coils / build
    if 'tf ' in s or 'coil' in s or 'stress' in s or 'strain' in s or 'build' in s:
        return 'MAGNETS_BUILD'
    # Neutronics / wall / tbr
    if 'neutron' in s or 'tbr' in s or 'shield' in s:
        return 'NEUTRONICS'
    # Plant / power / economics
    if 'net electric' in s or 'capex' in s or 'cost' in s or 'recirc' in s:
        return 'PLANT_ECON'
    return 'OTHER'


def mechanism_group_histogram(atlas: Dict[str, Any]) -> Dict[str, int]:
    hist = mechanism_histogram(atlas)
    out: Dict[str, int] = {}
    for k, v in hist.items():
        if k == 'ok':
            continue
        g = mechanism_group(k)
        out[g] = int(out.get(g, 0) + int(v))
    return out
