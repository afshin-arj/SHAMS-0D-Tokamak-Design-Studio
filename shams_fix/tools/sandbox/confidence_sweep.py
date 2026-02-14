"""Reactor Design Forge — Confidence Sweep (v1)

Purpose
-------
Provide a reviewer-friendly, explicit uncertainty/assumption sweep that
helps users stop reaching for PROCESS as a "second opinion".

This module is intentionally conservative and audit-clean:
- It never modifies the frozen evaluator truth.
- It operates on *declared* perturbations applied to constraint margins
  (first-order) and to closure/economic proxies (scalars).

The output is descriptive (PASS/WARN/FAIL + first-kill tallies) and
exportable as JSON.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class SweepKnob:
    name: str
    deltas: Sequence[float]
    kind: str  # 'margin' | 'proxy'
    note: str = ""


DEFAULT_KNOBS: List[SweepKnob] = [
    SweepKnob(
        name="Margin perturbation",
        deltas=[-0.15, -0.10, -0.05, 0.0, 0.05, 0.10],
        kind="margin",
        note="Applies to signed margins: m' = m + d*|m| (first-order).",
    ),
    SweepKnob(
        name="Economics posture scalar",
        deltas=[-0.10, 0.0, 0.10],
        kind="proxy",
        note="Scales cost proxies (CAPEX/OPEX/LCOE) symmetrically (descriptive).",
    ),
    SweepKnob(
        name="Recirc uncertainty scalar",
        deltas=[-0.05, 0.0, 0.05],
        kind="proxy",
        note="Scales recirc electric proxy in closure bundle (descriptive).",
    ),
]


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _min_margin(records: List[Dict[str, Any]]) -> Optional[Tuple[str, float]]:
    name = None
    mm = None
    for r in records or []:
        m = r.get("signed_margin")
        if m is None:
            m = r.get("margin")
        mf = _safe_float(m)
        if mf is None:
            continue
        if mm is None or mf < mm:
            mm = mf
            name = str(r.get("name") or "?")
    if mm is None:
        return None
    return name or "?", float(mm)


def _apply_margin_delta(records: List[Dict[str, Any]], delta: float) -> List[float]:
    out = []
    for r in records or []:
        m = r.get("signed_margin")
        if m is None:
            m = r.get("margin")
        mf = _safe_float(m)
        if mf is None:
            continue
        mp = mf + float(delta) * abs(mf)
        out.append(mp)
    return out


def _proxy_scale(closure_bundle: Dict[str, Any], econ_scale: float, recirc_scale: float) -> Dict[str, Any]:
    cb = dict(closure_bundle or {})

    # Scale net/gross/recirc if present (proxy only).
    for k in ("gross_electric_MW", "recirc_electric_MW", "net_electric_MW"):
        v = _safe_float(cb.get(k))
        if v is None:
            continue
        if k == "recirc_electric_MW":
            cb[k] = v * (1.0 + float(recirc_scale))
        else:
            cb[k] = v

    # Scale envelopes proxies (descriptive only)
    env = cb.get("economics_envelopes")
    if isinstance(env, dict):
        env2 = {}
        for nm, e in env.items():
            if not isinstance(e, dict):
                env2[nm] = e
                continue
            e2 = dict(e)
            for ck in ("CAPEX_proxy", "OPEX_proxy", "LCOE_proxy"):
                vv = _safe_float(e.get(ck))
                if vv is None:
                    e2[ck] = None
                else:
                    e2[ck] = vv * (1.0 + float(econ_scale))
            # keep assumptions note
            env2[nm] = e2
        cb["economics_envelopes"] = env2

    cb["_confidence_sweep_proxy_note"] = "Scaled proxies only; frozen truth unchanged."
    return cb


def confidence_sweep(
    records: List[Dict[str, Any]],
    closure_bundle: Optional[Dict[str, Any]] = None,
    knobs: Optional[Sequence[SweepKnob]] = None,
    pass_frac_warn: float = 0.95,
    pass_frac_fail: float = 0.80,
) -> Dict[str, Any]:
    """Run the v1 Confidence Sweep.

    Returns a descriptive result:
    - pass_fraction across margin perturbations
    - first-kill tallies
    - proxy-scaled closure/economics headline changes

    PASS/WARN/FAIL logic:
    - PASS if min(pass_fraction) >= pass_frac_warn
    - WARN if min(pass_fraction) >= pass_frac_fail
    - FAIL otherwise
    """

    knobs = list(knobs or DEFAULT_KNOBS)

    if not records:
        return {
            "schema": "shams.reactor_design_forge.confidence_sweep.v1",
            "ok": False,
            "reason": "No constraint records provided.",
        }

    # Margin sweep
    margin_knob = next((k for k in knobs if k.kind == "margin"), None)
    deltas = list(margin_knob.deltas) if margin_knob else [-0.1, 0.0, 0.1]
    pass_fracs: List[float] = []
    first_kill: Dict[str, int] = {}

    for d in deltas:
        margins = _apply_margin_delta(records, float(d))
        if not margins:
            pass_fracs.append(0.0)
            continue
        n = len(margins)
        passes = sum(1 for m in margins if m >= 0.0)
        pass_fracs.append(passes / max(1, n))

        # first-kill under this perturbation = most negative margin after perturbation
        worst_name = None
        worst_val = None
        for r in records:
            m = r.get("signed_margin")
            if m is None:
                m = r.get("margin")
            mf = _safe_float(m)
            if mf is None:
                continue
            mp = mf + float(d) * abs(mf)
            if worst_val is None or mp < worst_val:
                worst_val = mp
                worst_name = str(r.get("name") or "?")
        if worst_name is not None:
            first_kill[worst_name] = int(first_kill.get(worst_name, 0)) + 1

    min_pass = min(pass_fracs) if pass_fracs else 0.0
    if min_pass >= pass_frac_warn:
        verdict = "PASS"
    elif min_pass >= pass_frac_fail:
        verdict = "WARN"
    else:
        verdict = "FAIL"

    # Proxy sweep headline (descriptive only)
    proxy_knobs = [k for k in knobs if k.kind == "proxy"]
    proxy_headlines = []
    cb = closure_bundle or {}

    econ_deltas = next((k.deltas for k in proxy_knobs if "Economics" in k.name), [0.0])
    recirc_deltas = next((k.deltas for k in proxy_knobs if "Recirc" in k.name), [0.0])

    for ed in econ_deltas:
        for rd in recirc_deltas:
            cb2 = _proxy_scale(cb, float(ed), float(rd))
            proxy_headlines.append(
                {
                    "economics_scale": float(ed),
                    "recirc_scale": float(rd),
                    "net_electric_MW": _safe_float(cb2.get("net_electric_MW")),
                    "recirc_electric_MW": _safe_float(cb2.get("recirc_electric_MW")),
                    "nominal_LCOE_proxy": _safe_float(
                        (cb2.get("economics_envelopes") or {}).get("Nominal", {}).get("LCOE_proxy")
                        if isinstance(cb2.get("economics_envelopes"), dict)
                        else None
                    ),
                }
            )

    mm = _min_margin(records)

    return {
        "schema": "shams.reactor_design_forge.confidence_sweep.v1",
        "ok": True,
        "reason": None,
        "verdict": verdict,
        "pass_fraction": pass_fracs,
        "margin_perturbations": deltas,
        "first_kill_tally": first_kill,
        "min_signed_margin": float(mm[1]) if mm else None,
        "min_margin_constraint": mm[0] if mm else None,
        "proxy_headlines": proxy_headlines,
        "notes": {
            "margin_note": margin_knob.note if margin_knob else "",
            "proxy_note": "Proxy scaling is descriptive only; it does not modify frozen truth.",
        },
    }
