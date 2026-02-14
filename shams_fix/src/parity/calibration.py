from __future__ import annotations

"""PROCESS Parity Layer v2: calibration helpers.

This module supports *benchmark calibration mode* in the UI:

* Compare parity-derived quantities against a reference table (e.g., published study values)
* Report absolute/relative deltas and tolerance pass/fail
* Provide simple, transparent local sensitivities for economics proxies

Notes
-----
These tools are **analysis lenses**. They do not change frozen truth.
"""

from dataclasses import replace
from typing import Any, Dict, List, Optional, Tuple

import math

from parity import parity_plant_closure, parity_magnets, parity_cryo, parity_costing


def compute_parity_bundle(inputs: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
    """Compute parity blocks (plant/magnets/cryo/costing)."""
    return {
        "plant": parity_plant_closure(inputs, outputs),
        "magnets": parity_magnets(inputs, outputs),
        "cryo": parity_cryo(inputs, outputs),
        "costing": parity_costing(inputs, outputs),
    }


def _get_nested(d: Dict[str, Any], path: str) -> Any:
    cur: Any = d
    for part in (path or "").split("."):
        if not part:
            continue
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def compare_to_reference(
    *,
    parity: Dict[str, Any],
    reference: Dict[str, Any],
    tolerances: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """Compare parity outputs to a reference dict.

    reference keys are *paths* into the parity dict, e.g.:
      "plant.derived.P_e_net_MW": 500

    tolerances are relative tolerances by key (default 5%).
    """
    tol_default = 0.05
    tolerances = tolerances or {}

    rows: List[Dict[str, Any]] = []
    for path, ref in (reference or {}).items():
        val = _get_nested(parity, str(path))
        try:
            v = float(val)
            r = float(ref)
            if not (math.isfinite(v) and math.isfinite(r)):
                raise ValueError("non-finite")
            delta = v - r
            rel = delta / max(abs(r), 1e-9)
            tol = float(tolerances.get(str(path), tol_default))
            ok = abs(rel) <= tol
        except Exception:
            v = val
            r = ref
            delta = None
            rel = None
            tol = float(tolerances.get(str(path), tol_default))
            ok = (v == r)
        rows.append(
            {
                "metric": str(path),
                "ref": r,
                "value": v,
                "delta": delta,
                "rel": rel,
                "tol_rel": tol,
                "ok": bool(ok),
            }
        )
    return rows


def economics_local_sensitivity(
    *,
    inputs: Any,
    outputs: Dict[str, Any],
    perturb_frac: float = 0.10,
    knobs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compute simple local sensitivities for the economics proxy.

    We perturb a small set of *declared* proxy knobs (input attributes) by +perturb_frac.
    This is not a gradient, only a transparent finite-difference indicator.
    """

    knobs = knobs or [
        "k_cost_magnet",
        "k_cost_blanket",
        "k_cost_bop",
        "k_cost_cryo",
        "fixed_charge_rate",
        "electricity_price_USD_per_MWh",
    ]

    base = parity_costing(inputs, outputs)
    base_d = base.get("derived", {})
    base_lcoe = float(base_d.get("LCOE_USD_per_MWh", float("nan")))
    base_capex = float(base_d.get("CAPEX_MUSD", float("nan")))

    rows: List[Dict[str, Any]] = []

    for k in knobs:
        try:
            if not hasattr(inputs, k):
                continue
            v0 = float(getattr(inputs, k))
            v1 = v0 * (1.0 + float(perturb_frac))
            inp2 = replace(inputs, **{k: v1})  # dataclass PointInputs
            p2 = parity_costing(inp2, outputs)
            d2 = p2.get("derived", {})
            l2 = float(d2.get("LCOE_USD_per_MWh", float("nan")))
            c2 = float(d2.get("CAPEX_MUSD", float("nan")))
            rows.append(
                {
                    "knob": k,
                    "base": v0,
                    "+10%": v1,
                    "ΔCAPEX_MUSD": c2 - base_capex if (math.isfinite(c2) and math.isfinite(base_capex)) else None,
                    "ΔLCOE_USD_per_MWh": l2 - base_lcoe if (math.isfinite(l2) and math.isfinite(base_lcoe)) else None,
                }
            )
        except Exception:
            continue

    return {
        "base": {"CAPEX_MUSD": base_capex, "LCOE_USD_per_MWh": base_lcoe},
        "perturb_frac": float(perturb_frac),
        "rows": rows,
    }
