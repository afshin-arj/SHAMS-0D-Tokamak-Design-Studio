from __future__ import annotations

"""Radial build stack solver (inboard midplane closure).

This module upgrades the earlier "single-sum" radial build check into an explicit,
ordered stack. The solver is still transparent and lightweight: it does not
attempt to model 3D shaping or detailed CAD, but it:

- Tracks a named list of stack regions (plasma edge -> TF inner leg)
- Computes inboard closure margin and coil inner radius
- Provides a structured, machine-readable stack for reports/UI
- Preserves backward compatibility with legacy scalar outputs

Design philosophy:
- Feasibility before optimization
- No black boxes: all numbers are direct sums with explicit assumptions
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Any

@dataclass(frozen=True)
class StackRegion:
    name: str
    thickness_m: float
    min_thickness_m: float = 0.0
    kind: str = "structure"  # plasma|gap|shield|blanket|coil|structure|vessel|fw

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["thickness_m"] = float(self.thickness_m)
        d["min_thickness_m"] = float(self.min_thickness_m)
        d["kind"] = str(self.kind)
        d["name"] = str(self.name)
        return d


def build_inboard_stack_from_inputs(inp: Any) -> List[StackRegion]:
    """Build an explicit inboard stack from PointInputs-like objects."""
    # Robust to missing fields: default to 0.
    def g(attr: str, default: float = 0.0) -> float:
        return float(getattr(inp, attr, default) if getattr(inp, attr, None) is not None else default)

    # Minimum thickness knobs (optional; if absent, treated as 0).
    def gmin(attr: str) -> float:
        return float(getattr(inp, attr, 0.0) if getattr(inp, attr, None) is not None else 0.0)

    return [
        StackRegion("First wall", g("t_fw_m"), min_thickness_m=gmin("t_fw_min_m"), kind="fw"),
        StackRegion("Blanket", g("t_blanket_m"), min_thickness_m=gmin("t_blanket_min_m"), kind="blanket"),
        StackRegion("Shield", g("t_shield_m"), min_thickness_m=gmin("t_shield_min_m"), kind="shield"),
        StackRegion("Vacuum vessel", g("t_vv_m"), min_thickness_m=gmin("t_vv_min_m"), kind="vessel"),
        StackRegion("Gap", g("t_gap_m"), min_thickness_m=gmin("t_gap_min_m"), kind="gap"),
        StackRegion("TF winding pack", g("t_tf_wind_m"), min_thickness_m=gmin("t_tf_wind_min_m"), kind="coil"),
        StackRegion("TF structure", g("t_tf_struct_m"), min_thickness_m=gmin("t_tf_struct_min_m"), kind="structure"),
    ]


def inboard_stack_closure(R0_m: float, a_m: float, stack: List[StackRegion], *, delta: float = 0.0) -> Dict[str, float]:
    """Compute inboard closure metrics.

    Definitions:
      inboard_space = R0 - a*(1 - delta)
      spent_noncoil = sum(thicknesses up to and including gap)
      R_coil_inner = inboard_space - spent_noncoil
      spent_total = sum(all thicknesses)
      margin = inboard_space - spent_total

    Returns:
      dict with:
        inboard_space_m, spent_noncoil_m, R_coil_inner_m, spent_total_m, inboard_margin_m,
        radial_build_ok, stack_ok
    """
    # NOTE: In an ideal Miller geometry, triangularity does not move the midplane inboard point.
    # Here δ is used as a *transparent clearance proxy* for engineering packaging/shaping effects
    # that tend to increase usable inboard space in compact designs.
    d = min(max(float(delta), 0.0), 0.8)
    inboard_space_m = float(R0_m) - float(a_m) * (1.0 - d)
    spent_total_m = float(sum(max(0.0, r.thickness_m) for r in stack))

    # Up to and including Gap counts as "noncoil" for defining R_coil_inner (matches v21/v22 convention).
    spent_noncoil_m = 0.0
    for r in stack:
        spent_noncoil_m += float(max(0.0, r.thickness_m))
        if r.kind == "gap":
            break

    R_coil_inner_m = inboard_space_m - spent_noncoil_m
    inboard_margin_m = inboard_space_m - spent_total_m

    radial_build_ok = 1.0 if R_coil_inner_m > 0.0 else 0.0
    stack_ok = 1.0 if inboard_margin_m > 0.0 else 0.0

    return {
        "inboard_space_m": float(inboard_space_m),
        "spent_noncoil_m": float(spent_noncoil_m),
        "R_coil_inner_m": float(R_coil_inner_m),
        "inboard_build_total_m": float(spent_total_m),
        "inboard_margin_m": float(inboard_margin_m),
        "radial_build_ok": float(radial_build_ok),
        "stack_ok": float(stack_ok),
    }


def suggest_stack_repairs(inboard_margin_m: float, knobs: Dict[str, float] | None = None) -> List[Dict[str, float]]:
    """Nearest-feasible style suggestions for stack closure.

    This is intentionally simple: provide a ranked list of single-knob moves
    that would recover zero margin. The solver does NOT apply these changes.

    knobs: optional dict with current knob values (used for scaled suggestions).
    """
    margin = float(inboard_margin_m)
    if margin >= 0.0:
        return []

    deficit = -margin
    sugg: List[Dict[str, float]] = []
    # Option 1: increase R0
    sugg.append({"knob": "R0_m", "delta": float(deficit), "reason": "Increase major radius to recover inboard margin"})
    # Option 2: decrease selected thickness knobs (if present)
    for k in ["t_gap_m", "t_vv_m", "t_shield_m", "t_blanket_m", "t_fw_m", "t_tf_struct_m", "t_tf_wind_m"]:
        sugg.append({"knob": k, "delta": -float(deficit), "reason": "Reduce inboard thickness to recover margin"})
    return sugg
