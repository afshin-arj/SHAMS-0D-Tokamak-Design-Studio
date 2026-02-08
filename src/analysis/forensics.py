from __future__ import annotations

"""Feasibility forensics (deterministic, audit-friendly).

This is additive-only tooling. It never modifies evaluator physics or constraints.

Outputs:
- constraint records with signed margins
- local signed-margin sensitivities to key knobs (central finite differences)
- dominant-constraint stability classification (how often the top blocker changes under perturbations)

Units:
- signed margins inherit the constraint value units
- sensitivities are in (margin units) per (knob units)
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple
import math

try:
    from ..models.inputs import PointInputs
    from ..physics.hot_ion import hot_ion_point
    from ..constraints.system import build_constraints_from_outputs, Constraint
except Exception:  # pragma: no cover
    from models.inputs import PointInputs
    from physics.hot_ion import hot_ion_point
    from constraints.system import build_constraints_from_outputs, Constraint

try:
    from ...tools.process_compat.process_compat import constraints_to_records, active_constraints
except Exception:  # pragma: no cover
    from tools.process_compat.process_compat import constraints_to_records, active_constraints


@dataclass(frozen=True)
class KnobSpec:
    name: str
    step_abs: Optional[float] = None
    step_rel: Optional[float] = None
    units: str = "-"

    def step_for(self, x: float) -> float:
        if self.step_abs is not None and math.isfinite(self.step_abs) and self.step_abs > 0:
            return float(self.step_abs)
        if self.step_rel is not None and math.isfinite(self.step_rel) and self.step_rel > 0:
            return float(self.step_rel) * max(abs(float(x)), 1e-12)
        # fallback
        return 1e-3 * max(abs(float(x)), 1.0)


DEFAULT_KNOBS: Tuple[KnobSpec, ...] = (
    KnobSpec("R0_m", step_rel=1e-3, units="m"),
    KnobSpec("a_m", step_rel=1e-3, units="m"),
    KnobSpec("kappa", step_rel=1e-3, units="-"),
    KnobSpec("Bt_T", step_rel=1e-3, units="T"),
    KnobSpec("Ip_MA", step_rel=1e-3, units="MA"),
    KnobSpec("Ti_keV", step_rel=1e-3, units="keV"),
    KnobSpec("fG", step_rel=1e-3, units="-"),
    KnobSpec("Paux_MW", step_rel=1e-3, units="MW"),
)


def _eval_constraints(pi: PointInputs, design_intent: Optional[str] = None) -> Tuple[Dict[str, Any], List[Constraint]]:
    out = hot_ion_point(pi)
    cons = build_constraints_from_outputs(out, design_intent=design_intent)
    return out, cons


def local_sensitivity(
    pi: PointInputs,
    *,
    knobs: Iterable[KnobSpec] = DEFAULT_KNOBS,
    design_intent: Optional[str] = None,
    top_k_constraints: int = 12,
) -> Dict[str, Any]:
    """Compute local sensitivities of constraint signed margins.

    Central FD: dm/dx ≈ (m(x+dx) - m(x-dx)) / (2 dx)

    Returns a JSON-serializable dict.
    """
    base_out, base_cons = _eval_constraints(pi, design_intent=design_intent)
    base_recs = constraints_to_records(base_cons)

    # pick a stable subset of constraints (all, but UI can display top-k)
    rec_map = {r.name: r for r in base_recs if r.name}
    # sort by signed margin (most limiting first)
    ranked = sorted([r for r in base_recs if r.name], key=lambda r: (float("inf") if (r.signed_margin != r.signed_margin) else r.signed_margin))
    focus = [r.name for r in ranked[:max(1, int(top_k_constraints))]]

    sens: Dict[str, Dict[str, float]] = {cn: {} for cn in focus}
    one_sided: Dict[str, Dict[str, Tuple[float, float]]] = {cn: {} for cn in focus}
    steps: Dict[str, float] = {}

    for ks in knobs:
        if not hasattr(pi, ks.name):
            continue
        x0 = float(getattr(pi, ks.name))
        if not math.isfinite(x0):
            continue
        dx = ks.step_for(x0)
        if dx <= 0 or not math.isfinite(dx):
            continue
        steps[ks.name] = dx

        # build perturbed inputs
        plus = pi.__dict__.copy(); plus[ks.name] = x0 + dx
        minus = pi.__dict__.copy(); minus[ks.name] = x0 - dx
        pi_p = PointInputs(**plus)
        pi_m = PointInputs(**minus)

        _, cons_p = _eval_constraints(pi_p, design_intent=design_intent)
        _, cons_m = _eval_constraints(pi_m, design_intent=design_intent)
        rec_p = {r.name: r for r in constraints_to_records(cons_p) if r.name}
        rec_m = {r.name: r for r in constraints_to_records(cons_m) if r.name}

        for cn in focus:
            mp = rec_p.get(cn)
            mm = rec_m.get(cn)
            if mp is None or mm is None:
                continue
            sp = float(mp.signed_margin)
            sm = float(mm.signed_margin)
            s0 = float(rec_map.get(cn).signed_margin) if rec_map.get(cn) is not None else float("nan")
            if not (math.isfinite(sp) and math.isfinite(sm)):
                continue
            sens[cn][ks.name] = (sp - sm) / (2.0 * dx)
            if math.isfinite(s0):
                d_plus = (sp - s0) / max(dx, 1e-30)
                d_minus = (s0 - sm) / max(dx, 1e-30)
                one_sided[cn][ks.name] = (float(d_plus), float(d_minus))

    # Dominant constraint stability: sample single-knob perturbations and count how often the top blocker changes.
    base_top = active_constraints(base_recs, top_k=1)[0].name if base_recs else ""
    changes = 0
    trials = 0
    for ks in knobs:
        if ks.name not in steps:
            continue
        x0 = float(getattr(pi, ks.name))
        dx = steps[ks.name]
        for sgn in (+1, -1):
            trials += 1
            pert = pi.__dict__.copy(); pert[ks.name] = x0 + sgn * dx
            pi_t = PointInputs(**pert)
            _, cons_t = _eval_constraints(pi_t, design_intent=design_intent)
            rec_t = constraints_to_records(cons_t)
            top_t = active_constraints(rec_t, top_k=1)[0].name if rec_t else ""
            if top_t and base_top and top_t != base_top:
                changes += 1

    fragility = float(changes) / float(trials) if trials > 0 else float("nan")
    stability_label = "stable" if (math.isfinite(fragility) and fragility <= 0.20) else ("fragile" if math.isfinite(fragility) else "unknown")

    # Tornado-style ranked impacts: expected |Δmargin| for the configured deterministic step.
    # This avoids unit-mixing and gives an intuitive "what knob matters" ordering.
    tornado: Dict[str, List[Dict[str, Any]]] = {}
    for cn in focus:
        rows: List[Dict[str, Any]] = []
        for k, dmdx in sens.get(cn, {}).items():
            dx = float(steps.get(k, float("nan")))
            if not (math.isfinite(dx) and math.isfinite(float(dmdx))):
                continue
            impact = abs(float(dmdx)) * dx
            rows.append(
                {
                    "knob": k,
                    "dmargin_per_unit": float(dmdx),
                    "step": dx,
                    "impact_abs": float(impact),
                    "sign": ("+" if float(dmdx) > 0 else ("-" if float(dmdx) < 0 else "0")),
                }
            )
        rows.sort(key=lambda r: (float("inf") if (r["impact_abs"] != r["impact_abs"]) else -r["impact_abs"]))
        tornado[cn] = rows

    # Deterministic leverage hints for the dominant constraint.
    # Note: this is not an optimizer; it simply reports local linearized levers.
    dominant = base_top
    dominant_rows = list(tornado.get(dominant, []))
    levers_help = [r for r in dominant_rows if float(r.get("dmargin_per_unit", 0.0)) > 0]
    levers_hurt = [r for r in dominant_rows if float(r.get("dmargin_per_unit", 0.0)) < 0]
    levers_help.sort(key=lambda r: -float(r.get("impact_abs", 0.0)))
    levers_hurt.sort(key=lambda r: -float(r.get("impact_abs", 0.0)))

    dominant_advice = {
        "dominant_constraint": dominant,
        "top_helping_knobs": [r["knob"] for r in levers_help[:3]],
        "top_hurting_knobs": [r["knob"] for r in levers_hurt[:3]],
    }

    # Lever confidence (0..1): combines dominant fragility and local slope consistency.
    # This is a deterministic quality indicator for interpreting the lever recipe.
    # - Fragility penalizes points where the dominant blocker changes under tiny perturbations.
    # - Slope consistency compares one-sided derivatives to the central derivative.
    lever_confidence = float("nan")
    lever_confidence_label = "unknown"
    try:
        if dominant:
            dom_rows = list(tornado.get(dominant, []) or [])
            # weighted average consistency across the highest-impact knobs
            w_sum = 0.0
            c_sum = 0.0
            for r in dom_rows[:6]:
                k = str(r.get("knob", ""))
                d = float(r.get("dmargin_per_unit", float("nan")))
                w = float(r.get("impact_abs", 0.0))
                if not (math.isfinite(d) and math.isfinite(w) and w > 0.0):
                    continue
                dpm = one_sided.get(dominant, {}).get(k)
                if not dpm:
                    continue
                d_plus, d_minus = float(dpm[0]), float(dpm[1])
                if not (math.isfinite(d_plus) and math.isfinite(d_minus)):
                    continue
                denom = abs(d) + 1e-12
                # 1 means perfectly consistent; 0 means wildly inconsistent
                c = 1.0 - min(1.0, abs(d_plus - d_minus) / denom)
                w_sum += w
                c_sum += w * c
            slope_consistency = (c_sum / w_sum) if w_sum > 0 else float("nan")
            frag_term = (1.0 - fragility) if math.isfinite(fragility) else float("nan")
            if math.isfinite(slope_consistency) and math.isfinite(frag_term):
                lever_confidence = max(0.0, min(1.0, float(slope_consistency) * float(frag_term)))
            if math.isfinite(lever_confidence):
                lever_confidence_label = "high" if lever_confidence >= 0.70 else ("medium" if lever_confidence >= 0.40 else "low")
    except Exception:
        lever_confidence = float("nan")
        lever_confidence_label = "unknown"

    notes: List[str] = []
    if dominant:
        if dominant_advice["top_helping_knobs"]:
            notes.append(
                f"Dominant blocker: {dominant}. Strongest local levers that *increase* its signed margin: "
                + ", ".join(dominant_advice["top_helping_knobs"])
                + "."
            )
        if dominant_advice["top_hurting_knobs"]:
            notes.append(
                f"Knobs that *decrease* {dominant} margin most strongly (watch for inadvertent regressions): "
                + ", ".join(dominant_advice["top_hurting_knobs"])
                + "."
            )
    if math.isfinite(fragility):
        notes.append(
            f"Dominant-constraint fragility fraction = {fragility:.2f} (<=0.20 stable; >0.20 fragile)."
        )

    return {
        "schema_version": "forensics.v1",
        "base": {
            "top_dominant": base_top,
            "fragility_fraction": fragility,
            "stability_label": stability_label,
        },
        "knob_steps": steps,
        "focus_constraints": focus,
        "sensitivities": sens,
        "tornado": tornado,
        "dominant_advice": dominant_advice,
        "lever_confidence": {
            "score": lever_confidence,
            "label": lever_confidence_label,
        },
        "notes": notes,
    }
