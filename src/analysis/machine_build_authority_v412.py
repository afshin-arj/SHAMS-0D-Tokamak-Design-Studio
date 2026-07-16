from __future__ import annotations

"""Machine-build / radial closure authority v412 — DEMO-like stack narrative.

Purpose
-------
MATCH-as-overlay deepening of PROCESS-class *machine-build* coverage:
layer-stack consistency, clearances / build gaps, inboard closure, optional
cryostat gap and outboard envelope proxy — without putting build iteration
into L0.

Hard laws
---------
- Algebraic, single-pass, deterministic. No solvers, no iteration, no smoothing.
- Does **not** mutate L0 truth equations; governance overlay only.
- Reads already-computed radial-build outputs from ``hot_ion_point``.
- Screening / proxy tier — not a replacement for CAD / detailed build codes.
- No invented PROCESS MFILE reference numbers.

Inputs (expected)
-----------------
From ``inp``:
- include_machine_build_authority_v412
- optional caps: machine_build_closure_margin_min_v412,
  machine_build_inboard_margin_min_m_v412, machine_build_gap_min_m_v412,
  machine_build_layer_surplus_min_m_v412
- layer thicknesses / mins (t_*_m, t_*_min_m), gap_to_cryostat_m_v392
- R0_m, a_m, delta (for outboard envelope proxy)

From ``out`` (already computed by L0 radial stack):
- radial_stack, inboard_space_m, inboard_build_total_m, inboard_margin_m
- spent_noncoil_m, R_coil_inner_m, radial_build_ok, stack_ok

Author
------
© 2026 Afshin Arjhangmehr
"""

import math
from typing import Any, Dict, List, Optional, Tuple


AUTHORITY_ID = "machine_build_authority_v412"
OVERLAY_VERSION = "v412.0.0"
SCREENING_TIER = "proxy"


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else float(default)
    except (TypeError, ValueError):
        return float(default)


def _finite(x: float) -> bool:
    return x == x and math.isfinite(x)


def _tier_from_margin(m: float, fragile: float = 0.05) -> str:
    if not _finite(m):
        return "unknown"
    if m < 0.0:
        return "deficit"
    if m < fragile:
        return "near_limit"
    return "comfortable"


def _min_finite(values: List[float]) -> float:
    finite = [v for v in values if _finite(v)]
    return min(finite) if finite else float("nan")


def _layer_ledger(out: Dict[str, Any], inp: Any) -> Tuple[List[Dict[str, Any]], float, str]:
    """Per-layer thickness vs min consistency; returns ledger, min surplus margin frac, dominant."""
    stack = out.get("radial_stack")
    rows: List[Dict[str, Any]] = []
    if not isinstance(stack, list) or not stack:
        # Reconstruct from inputs if L0 stack missing (still algebraic).
        names = (
            ("First wall", "t_fw_m", "t_fw_min_m", "fw"),
            ("Blanket", "t_blanket_m", "t_blanket_min_m", "blanket"),
            ("Shield", "t_shield_m", "t_shield_min_m", "shield"),
            ("Vacuum vessel", "t_vv_m", "t_vv_min_m", "vessel"),
            ("Gap", "t_gap_m", "t_gap_min_m", "gap"),
            ("TF winding pack", "t_tf_wind_m", "t_tf_wind_min_m", "coil"),
            ("TF structure", "t_tf_struct_m", "t_tf_struct_min_m", "structure"),
        )
        stack = []
        for name, tkey, mkey, kind in names:
            stack.append(
                {
                    "name": name,
                    "thickness_m": _f(getattr(inp, tkey, 0.0), 0.0),
                    "min_thickness_m": _f(getattr(inp, mkey, 0.0), 0.0),
                    "kind": kind,
                }
            )

    margins: List[Tuple[str, float]] = []
    for layer in stack:
        if not isinstance(layer, dict):
            continue
        name = str(layer.get("name", "unknown"))
        t = _f(layer.get("thickness_m"), 0.0)
        tmin = _f(layer.get("min_thickness_m"), 0.0)
        if not _finite(t):
            t = 0.0
        if not _finite(tmin) or tmin < 0.0:
            tmin = 0.0
        surplus = t - tmin
        ok = bool(surplus >= 0.0) if tmin > 0.0 else True
        rows.append(
            {
                "name": name,
                "kind": str(layer.get("kind", "")),
                "thickness_m": float(t),
                "min_thickness_m": float(tmin),
                "surplus_m": float(surplus),
                "ok": bool(ok),
            }
        )
        if tmin > 0.0:
            # Fractional headroom vs declared minimum thickness.
            margins.append((name, t / tmin - 1.0))

    if margins:
        dom_name, dom_m = min(margins, key=lambda km: km[1])
        return rows, float(dom_m), str(dom_name)
    return rows, float("nan"), "none"


def _aspect_inboard(out: Dict[str, Any]) -> Tuple[float, float]:
    """Return (margin_frac, margin_m) for inboard stack closure."""
    space = _f(out.get("inboard_space_m"))
    spent = _f(out.get("inboard_build_total_m"))
    margin_m = _f(out.get("inboard_margin_m"))
    if not _finite(margin_m) and _finite(space) and _finite(spent):
        margin_m = space - spent
    if _finite(space) and space > 0.0 and _finite(spent) and spent > 0.0:
        return space / spent - 1.0, float(margin_m) if _finite(margin_m) else float("nan")
    if _finite(space) and space > 0.0 and _finite(margin_m):
        return margin_m / space, float(margin_m)
    return float("nan"), float(margin_m) if _finite(margin_m) else float("nan")


def _aspect_coil_bore(out: Dict[str, Any]) -> float:
    """Fractional headroom of TF coil inner radius vs inboard space."""
    Rci = _f(out.get("R_coil_inner_m"))
    space = _f(out.get("inboard_space_m"))
    if _finite(Rci) and _finite(space) and space > 0.0:
        return Rci / space  # >0 comfortable packing; ≤0 means stack doesn't close to coil
    if _finite(Rci):
        return 1.0 if Rci > 0.0 else -1.0
    return float("nan")


def _aspect_gap(out: Dict[str, Any], inp: Any, gap_min_cap: float) -> Tuple[float, float]:
    """Build-gap clearance: t_gap vs optional min (cap or layer min)."""
    stack = out.get("radial_stack")
    t_gap = float("nan")
    t_gap_min = _f(getattr(inp, "t_gap_min_m", 0.0), 0.0)
    if isinstance(stack, list):
        for layer in stack:
            if isinstance(layer, dict) and str(layer.get("kind", "")).lower() == "gap":
                t_gap = _f(layer.get("thickness_m"))
                tmin_layer = _f(layer.get("min_thickness_m"), 0.0)
                if _finite(tmin_layer) and tmin_layer > 0.0:
                    t_gap_min = max(t_gap_min if _finite(t_gap_min) else 0.0, tmin_layer)
                break
    if not _finite(t_gap):
        t_gap = _f(getattr(inp, "t_gap_m", float("nan")))
    if _finite(gap_min_cap) and gap_min_cap > 0.0:
        t_gap_min = gap_min_cap
    if _finite(t_gap) and _finite(t_gap_min) and t_gap_min > 0.0:
        return t_gap / t_gap_min - 1.0, float(t_gap)
    if _finite(t_gap):
        return float("nan"), float(t_gap)
    return float("nan"), float("nan")


def _outboard_envelope(inp: Any, out: Dict[str, Any], build_total_m: float) -> Dict[str, float]:
    """Symmetric outboard envelope proxy (same layer sum + optional cryostat gap)."""
    R0 = _f(getattr(inp, "R0_m", out.get("R0_m")))
    a = _f(getattr(inp, "a_m", out.get("a_m")))
    delta = _f(getattr(inp, "delta", out.get("delta")), 0.0)
    if not _finite(delta):
        delta = 0.0
    d = min(max(delta, 0.0), 0.8)
    cryo = _f(getattr(inp, "gap_to_cryostat_m_v392", float("nan")))
    if not _finite(cryo):
        cryo = 0.0
    if not (_finite(R0) and _finite(a) and _finite(build_total_m)):
        return {
            "machine_v412_outboard_plasma_edge_m": float("nan"),
            "machine_v412_outboard_build_m": float("nan"),
            "machine_v412_outboard_R_outer_m": float("nan"),
            "machine_v412_cryostat_gap_m": float(cryo) if _finite(cryo) else float("nan"),
        }
    plasma_edge = R0 + a * (1.0 + d)
    R_outer = plasma_edge + max(0.0, build_total_m) + max(0.0, cryo)
    return {
        "machine_v412_outboard_plasma_edge_m": float(plasma_edge),
        "machine_v412_outboard_build_m": float(max(0.0, build_total_m)),
        "machine_v412_outboard_R_outer_m": float(R_outer),
        "machine_v412_cryostat_gap_m": float(cryo),
    }


def compute(inp: Any, out: Dict[str, Any]) -> Dict[str, Any]:
    fragile = _f(out.get("fragile_margin_frac"), _f(getattr(inp, "fragile_margin_frac", 0.05)))
    if not _finite(fragile):
        fragile = 0.05

    gap_min_cap = _f(getattr(inp, "machine_build_gap_min_m_v412", float("nan")))
    layer_surplus_min = _f(getattr(inp, "machine_build_layer_surplus_min_m_v412", float("nan")))
    inboard_margin_min_m = _f(getattr(inp, "machine_build_inboard_margin_min_m_v412", float("nan")))
    closure_margin_min = _f(getattr(inp, "machine_build_closure_margin_min_v412", float("nan")))

    layers, layer_margin_frac, layer_dom = _layer_ledger(out, inp)
    inboard_frac, inboard_m = _aspect_inboard(out)
    coil_frac = _aspect_coil_bore(out)
    gap_frac, t_gap = _aspect_gap(out, inp, gap_min_cap)

    # Optional absolute inboard floor → fractional margin vs that floor
    inboard_vs_floor = float("nan")
    if _finite(inboard_m) and _finite(inboard_margin_min_m):
        # Positive when margin exceeds declared minimum clearance [m].
        denom = max(abs(inboard_margin_min_m), 1e-9) if inboard_margin_min_m != 0.0 else 1e-9
        inboard_vs_floor = (inboard_m - inboard_margin_min_m) / denom

    # Optional layer surplus floor [m] across layers that declare a min
    layer_surplus_vs_floor = float("nan")
    if _finite(layer_surplus_min) and layers:
        surpluses = [float(r["surplus_m"]) for r in layers if float(r.get("min_thickness_m", 0.0) or 0.0) > 0.0]
        if surpluses:
            worst = min(surpluses)
            denom = max(abs(layer_surplus_min), 1e-9) if layer_surplus_min != 0.0 else 1e-9
            layer_surplus_vs_floor = (worst - layer_surplus_min) / denom

    aspects: List[Tuple[str, float]] = []
    if _finite(inboard_frac):
        aspects.append(("inboard_closure", inboard_frac))
    if _finite(coil_frac):
        # R_coil_inner / inboard_space: packing headroom screen (1.0 = empty bore).
        aspects.append(("coil_bore", min(coil_frac, 1.0)))
    if _finite(gap_frac):
        aspects.append(("build_gap", gap_frac))
    if _finite(layer_margin_frac):
        aspects.append(("layer_mins", layer_margin_frac))
    if _finite(inboard_vs_floor):
        aspects.append(("inboard_floor", inboard_vs_floor))
    if _finite(layer_surplus_vs_floor):
        aspects.append(("layer_surplus_floor", layer_surplus_vs_floor))

    # Coil bore: when R_coil_inner <= 0, force deficit
    Rci = _f(out.get("R_coil_inner_m"))
    if _finite(Rci) and Rci <= 0.0:
        aspects = [(k, m) for k, m in aspects if k != "coil_bore"]
        aspects.append(("coil_bore", -1.0))

    finite = [(k, m) for k, m in aspects if _finite(m)]
    system_margin = _min_finite([m for _, m in finite])
    if finite:
        dom_k, dom_m = min(finite, key=lambda km: km[1])
    else:
        dom_k, dom_m = "unknown", float("nan")

    build_total = _f(out.get("inboard_build_total_m"))
    if not _finite(build_total) and layers:
        build_total = sum(float(r.get("thickness_m", 0.0) or 0.0) for r in layers)

    envelope = _outboard_envelope(inp, out, build_total if _finite(build_total) else float("nan"))

    stack_ok = _f(out.get("stack_ok"))
    rb_ok = _f(out.get("radial_build_ok"))
    closure_ok = bool(
        (_finite(inboard_m) and inboard_m >= 0.0)
        and (_finite(Rci) and Rci > 0.0)
        and all(bool(r.get("ok", True)) for r in layers)
    )

    patch: Dict[str, Any] = {
        "machine_v412_enabled": True,
        "machine_v412_authority_id": AUTHORITY_ID,
        "machine_v412_overlay_version": OVERLAY_VERSION,
        "machine_v412_screening_tier": SCREENING_TIER,
        "machine_v412_provenance": (
            "algebraic radial / machine-build closure narrative from L0 inboard stack "
            "+ layer min consistency + gap/clearance + outboard envelope proxy; "
            "not PROCESS MFILE parity"
        ),
        "machine_v412_system_margin": float(system_margin),
        "machine_v412_system_tier": _tier_from_margin(system_margin, fragile),
        "machine_v412_dominant_aspect": str(dom_k),
        "machine_v412_dominant_aspect_margin": float(dom_m),
        "machine_v412_closure_ok": bool(closure_ok),
        "machine_v412_inboard_margin_m": float(inboard_m) if _finite(inboard_m) else float("nan"),
        "machine_v412_inboard_closure_margin": float(inboard_frac) if _finite(inboard_frac) else float("nan"),
        "machine_v412_inboard_space_m": _f(out.get("inboard_space_m")),
        "machine_v412_inboard_build_total_m": float(build_total) if _finite(build_total) else float("nan"),
        "machine_v412_R_coil_inner_m": float(Rci) if _finite(Rci) else float("nan"),
        "machine_v412_coil_bore_margin": float(coil_frac) if _finite(coil_frac) else float("nan"),
        "machine_v412_gap_thickness_m": float(t_gap) if _finite(t_gap) else float("nan"),
        "machine_v412_gap_clearance_margin": float(gap_frac) if _finite(gap_frac) else float("nan"),
        "machine_v412_layer_mins_margin": float(layer_margin_frac) if _finite(layer_margin_frac) else float("nan"),
        "machine_v412_layer_dominant": str(layer_dom),
        "machine_v412_n_layers": int(len(layers)),
        "machine_v412_layers_ok": bool(all(bool(r.get("ok", True)) for r in layers)),
        "machine_v412_layer_ledger": layers,
        "machine_v412_stack_ok_echo": float(stack_ok) if _finite(stack_ok) else float("nan"),
        "machine_v412_radial_build_ok_echo": float(rb_ok) if _finite(rb_ok) else float("nan"),
        # Optional caps echoed for constraint layer (NaN disables)
        "machine_build_closure_margin_min_v412": float(closure_margin_min),
        "machine_build_inboard_margin_min_m_v412": float(inboard_margin_min_m),
        "machine_build_gap_min_m_v412": float(gap_min_cap),
        "machine_build_layer_surplus_min_m_v412": float(layer_surplus_min),
        "machine_v412_units": {
            "margins": "fraction (space/spent - 1, thickness/min - 1, or signed floor headroom)",
            "lengths": "m",
            "R": "m",
        },
        "machine_v412_narrative": (
            f"Inboard margin={inboard_m:.4g} m; dominant={dom_k}; "
            f"tier={_tier_from_margin(system_margin, fragile)}; "
            f"layers={len(layers)}; PROXY machine-build screen"
            if _finite(inboard_m)
            else f"Dominant={dom_k}; tier={_tier_from_margin(system_margin, fragile)}; PROXY machine-build screen"
        ),
    }
    patch.update(envelope)
    return patch


def evaluate_machine_build_authority_v412(out: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    """Deterministic radial / machine-build overlay. Does not re-solve physics.

    When disabled, returns ``{}`` so default evaluator outputs (and goldens) are
    unchanged — L0 numeric truth and artifact key sets stay frozen.
    """
    enabled = bool(getattr(inp, "include_machine_build_authority_v412", False))
    if not enabled:
        return {}
    patch = compute(inp, out)
    patch["include_machine_build_authority_v412"] = True
    return patch
