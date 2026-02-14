from __future__ import annotations

import copy
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore

from physics.hot_ion import hot_ion_point
from constraints.constraints import evaluate_constraints
from constraints.bookkeeping import summarize as summarize_constraints
from shams_io.run_artifact import build_run_artifact

from .spec import PhaseSpec


def _merged_policy(base_out: Dict[str, Any], overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    try:
        pol = base_out.get("_policy_contract") if isinstance(base_out, dict) else None
        base = pol if isinstance(pol, dict) else {}
    except Exception:
        base = {}
    merged = dict(base or {})
    if overrides:
        merged.update(dict(overrides))
    return merged


def _phase_eval(base_inputs: PointInputs, base_out: Dict[str, Any], phase: PhaseSpec, *, label_prefix: str) -> Dict[str, Any]:
    base_d = asdict(base_inputs)
    for k, v in (phase.input_overrides or {}).items():
        if k in base_d:
            base_d[k] = v
    inp = PointInputs(**base_d)

    out = hot_ion_point(inp)
    policy = _merged_policy(base_out if isinstance(base_out, dict) else {}, phase.policy_overrides)
    cons = evaluate_constraints(out, policy=policy)
    summary = summarize_constraints(cons).to_dict()

    art = build_run_artifact(
        inputs=dict(inp.__dict__),
        outputs=dict(out),
        constraints=cons,
        meta={"mode": "phase_envelope", "label": f"{label_prefix}:{phase.name}"},
        solver={"message": "phase_envelope_quasi_static"},
        economics=dict((out or {}).get("_economics", {})) if isinstance(out, dict) else {},
    )
    art["phase"] = phase.to_dict()
    art["phase_constraints_summary"] = summary
    return art


def run_phase_envelope_for_point(
    base_inputs: PointInputs,
    phases: List[PhaseSpec],
    *,
    label_prefix: str = "phase",
) -> Dict[str, Any]:
    """Run ordered quasi-static phases and return an envelope summary.

    Worst-phase is defined as:
      - any infeasible (hard fail) phase dominates feasible phases
      - among infeasible phases, pick the one with most negative worst_hard_margin_frac
      - if all feasible, pick the one with smallest worst_hard_margin_frac (closest to boundary)

    Returns
    -------
    dict with keys:
      - schema_version
      - phases_ordered: list of phase artifacts (one per phase)
      - worst_phase: selected phase name
      - worst_phase_index
      - envelope_verdict: PASS / FAIL
      - envelope_summary: condensed metrics
    """
    if not phases:
        raise ValueError("phases must be non-empty")

    base_out = hot_ion_point(base_inputs)
    phase_arts: List[Dict[str, Any]] = []
    scores: List[Tuple[int, float]] = []  # (infeasible_flag, worst_margin)

    for ph in phases:
        art = _phase_eval(base_inputs, base_out, ph, label_prefix=label_prefix)
        phase_arts.append(art)
        cs = (art.get("constraints_summary") or {}) if isinstance(art, dict) else {}
        feasible = bool(cs.get("feasible", False))
        worst = cs.get("worst_hard_margin_frac", None)
        try:
            w = float(worst) if worst is not None else 0.0
        except Exception:
            w = 0.0
        scores.append((0 if feasible else 1, w))

    # Determine worst phase by the rule above.
    # Sort key: infeasible first (1), then smallest margin (most negative)
    ranked = sorted(list(enumerate(scores)), key=lambda t: (-t[1][0], t[1][1]))
    worst_idx = int(ranked[0][0])
    worst_art = phase_arts[worst_idx]
    worst_name = str((worst_art.get("phase") or {}).get("name", f"phase_{worst_idx}"))

    envelope_feasible = all(bool((a.get("constraints_summary") or {}).get("feasible", False)) for a in phase_arts)
    envelope_verdict = "PASS" if envelope_feasible else "FAIL"

    # Condensed envelope summary (stable keys for UI)
    def _kpi(a: Dict[str, Any], k: str) -> Any:
        try:
            return (a.get("kpis") or {}).get(k)
        except Exception:
            return None

    envelope_summary = {
        "schema_version": "phase_envelope_summary.v1",
        "n_phases": int(len(phase_arts)),
        "envelope_verdict": envelope_verdict,
        "worst_phase": worst_name,
        "worst_phase_index": worst_idx,
        "worst_phase_worst_hard_margin_frac": (worst_art.get("constraints_summary") or {}).get("worst_hard_margin_frac"),
        "worst_phase_worst_hard": (worst_art.get("constraints_summary") or {}).get("worst_hard"),
        # A tiny KPI subset for fast read
        "worst_phase_kpis": {
            "Q_DT_eqv": _kpi(worst_art, "Q_DT_eqv"),
            "H98": _kpi(worst_art, "H98"),
            "P_net_e_MW": _kpi(worst_art, "P_net_e_MW"),
            "TBR": _kpi(worst_art, "TBR"),
        },
    }

    return {
        "schema_version": "phase_envelope.v1",
        "label_prefix": str(label_prefix),
        "base_inputs": dict(base_inputs.__dict__),
        "phases_ordered": phase_arts,
        "worst_phase": worst_name,
        "worst_phase_index": worst_idx,
        "envelope_verdict": envelope_verdict,
        "envelope_summary": envelope_summary,
    }
