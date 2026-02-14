from __future__ import annotations

"""Campaign batch evaluation (v363.0).

Evaluates candidate inputs deterministically using the frozen evaluator.
Optionally attaches Profile Contracts 2.0 results (v362) for each candidate.

This module is suitable for both headless CLI execution and UI invocation.

© 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json

try:
    from ..models.inputs import PointInputs  # type: ignore
    from ..evaluator.core import Evaluator  # type: ignore
    from ..constraints.system import build_constraints_from_outputs  # type: ignore
    from ..shams_io.run_artifact import build_run_artifact  # type: ignore
    from ..analysis.profile_contracts_v362 import evaluate_profile_contracts_v362  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore
    from evaluator.core import Evaluator  # type: ignore
    from constraints.system import build_constraints_from_outputs  # type: ignore
    from shams_io.run_artifact import build_run_artifact  # type: ignore
    from analysis.profile_contracts_v362 import evaluate_profile_contracts_v362  # type: ignore

from .spec import CampaignSpec


def _annotate_summary_fields(art: Dict[str, Any], *, intent: str) -> Dict[str, Any]:
    kpis = art.get("kpis", {}) if isinstance(art.get("kpis"), dict) else {}
    feasible = bool(kpis.get("feasible_hard", False))
    art["intent"] = str(intent)
    art["verdict"] = "PASS" if feasible else "FAIL"

    dom_constraint = ""
    dom_mech = ""
    worst = None
    try:
        worst = float(kpis.get("min_hard_margin"))
    except Exception:
        worst = None
    try:
        ledger = art.get("constraint_ledger", {}) if isinstance(art.get("constraint_ledger"), dict) else {}
        top = ledger.get("top_blockers", []) if isinstance(ledger.get("top_blockers"), list) else []
        if top:
            t0 = top[0] if isinstance(top[0], dict) else {}
            dom_constraint = str(t0.get("name", ""))
            dom_mech = str(t0.get("mechanism_group", t0.get("mechanism", "")) or "")
    except Exception:
        pass

    art["dominant_constraint"] = dom_constraint
    art["dominant_mechanism"] = dom_mech
    art["worst_hard_margin"] = worst
    return art


@dataclass(frozen=True)
class CampaignEvalRow:
    cid: str
    inputs: Dict[str, Any]
    feasible_hard: bool
    verdict: str
    dominant_mechanism: str
    worst_hard_margin: Optional[float]
    artifact: Optional[Dict[str, Any]]


def evaluate_campaign_candidates(
    spec: CampaignSpec,
    candidates: List[Dict[str, Any]],
    *,
    include_full_artifact: Optional[bool] = None,
) -> Tuple[List[CampaignEvalRow], Dict[str, Any]]:
    inc_full = bool(spec.include_full_artifact if include_full_artifact is None else include_full_artifact)

    ev = Evaluator(label=str(spec.evaluator_label), cache_enabled=False)

    rows: List[CampaignEvalRow] = []
    mech_hist: Dict[str, int] = {}

    for cand in candidates:
        cid = str(cand.get("cid", "")) or ""
        merged = dict(spec.fixed_inputs)
        for k, v in cand.items():
            if k == "cid":
                continue
            merged[k] = v

        pi = PointInputs(**merged)
        evr = ev.evaluate(pi)
        if not evr.ok:
            art: Dict[str, Any] = {
                "schema_version": "shams_run_artifact.v1",
                "kind": "shams_run_artifact",
                "inputs": merged,
                "outputs": {},
                "constraints": [],
                "kpis": {"feasible_hard": False, "min_hard_margin": float("nan")},
                "error": evr.message,
            }
        else:
            out = evr.out
            cons = build_constraints_from_outputs(out, design_intent=spec.intent)
            art = build_run_artifact(inputs=merged, outputs=out, constraints=cons)

        art = _annotate_summary_fields(art, intent=spec.intent)

        # Profile contracts overlay (v362)
        try:
            pc = spec.profile_contracts
            pc_rep = evaluate_profile_contracts_v362(pi, preset=str(pc.preset), tier=str(pc.tier))
            art["profile_contracts_v362"] = pc_rep.to_dict() if hasattr(pc_rep, "to_dict") else dict(pc_rep)  # type: ignore
        except Exception as ex:
            art["profile_contracts_v362"] = {
                "schema_version": "profile_contracts_v362_error.v1",
                "error": str(ex),
            }

        kpis = art.get("kpis", {}) if isinstance(art.get("kpis"), dict) else {}
        feas = bool(kpis.get("feasible_hard", False))
        verdict = str(art.get("verdict", "FAIL"))
        mech = str(art.get("dominant_mechanism", "")) or "(none)"
        mech_hist[mech] = int(mech_hist.get(mech, 0)) + 1
        worst = art.get("worst_hard_margin", None)
        try:
            worst_f = float(worst) if worst is not None else None
        except Exception:
            worst_f = None

        rows.append(
            CampaignEvalRow(
                cid=cid,
                inputs=merged,
                feasible_hard=feas,
                verdict=verdict,
                dominant_mechanism=mech,
                worst_hard_margin=worst_f,
                artifact=art if inc_full else None,
            )
        )

    summary = {
        "schema": "shams_campaign_summary.v1",
        "campaign": spec.name,
        "intent": spec.intent,
        "evaluator_label": spec.evaluator_label,
        "n_total": len(rows),
        "n_feasible": int(sum(1 for r in rows if r.feasible_hard)),
        "pass_rate": float(sum(1 for r in rows if r.feasible_hard)) / float(len(rows) or 1),
        "dominant_mechanism_hist": mech_hist,
    }

    return rows, summary


def write_results_jsonl(rows: List[CampaignEvalRow], out_path: Path, *, include_artifact: bool = True) -> None:
    out_path = Path(out_path)
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            d = {
                "schema": "shams_campaign_result.v1",
                "cid": r.cid,
                "inputs": r.inputs,
                "feasible_hard": bool(r.feasible_hard),
                "verdict": r.verdict,
                "dominant_mechanism": r.dominant_mechanism,
                "worst_hard_margin": r.worst_hard_margin,
            }
            if include_artifact and r.artifact is not None:
                d["artifact"] = r.artifact
            f.write(json.dumps(d, sort_keys=True) + "\n")
