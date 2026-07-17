"""Independence Phase 3.3 — SHAMS-only champion feasibility cases.

Reproducible templates labs can copy: frozen Evaluator, Design Intent policy
aligned with Point Designer, run artifacts + SHA-256 citation hashes.

L0 risk: none (consumes Evaluator only; no physics/constraint equation changes).
Does not invent PROCESS MFILE numbers or claim PROCESS retirement.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

try:
    from models.inputs import PointInputs  # type: ignore
    from models.reference_machines import REFERENCE_MACHINES  # type: ignore
    from evaluator.core import Evaluator  # type: ignore
    from constraints.constraints import evaluate_constraints  # type: ignore
    from shams_io.run_artifact import build_run_artifact  # type: ignore
except ImportError:  # pragma: no cover
    from src.models.inputs import PointInputs
    from src.models.reference_machines import REFERENCE_MACHINES
    from src.evaluator.core import Evaluator
    from src.constraints.constraints import evaluate_constraints
    from src.shams_io.run_artifact import build_run_artifact

try:
    from ui_nicegui.lib.pd_intent_policy import (  # type: ignore
        classify_failed_constraints,
        design_intent_key,
        hard_constraint_names_for_intent,
        ignored_constraint_names_for_intent,
        constraint_policy_snapshot,
    )
except ImportError:  # pragma: no cover
    from ui_nicegui.lib.pd_intent_policy import (  # type: ignore
        classify_failed_constraints,
        design_intent_key,
        hard_constraint_names_for_intent,
        ignored_constraint_names_for_intent,
        constraint_policy_snapshot,
    )

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES_PATH = _REPO_ROOT / "benchmarks" / "champions" / "cases.json"
CHAMPION_SCHEMA = "shams.champion_cases.v1"
# Frozen epoch for deterministic artifact timestamps (citation reproducibility).
_CHAMPION_EPOCH_UNIX = 0.0

_INTENT_SOFT = {
    "reactor": set(),
    "research": {"q_div", "P_SOL/R", "sigma_vm", "B_peak", "HTS margin", "NWL"},
}


def read_shams_version(repo_root: Optional[Path] = None) -> str:
    root = repo_root or _REPO_ROOT
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"


def load_champion_definitions(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load champion case definitions from JSON (skips README / meta keys)."""
    p = Path(path) if path else DEFAULT_CASES_PATH
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("champion cases JSON must be an object")
    cases: List[Dict[str, Any]] = []
    for case_id, body in raw.items():
        if case_id in ("README", "schema", "_meta") or not isinstance(body, dict):
            continue
        if body.get("enabled") is False:
            continue
        row = dict(body)
        row["case_id"] = str(case_id)
        cases.append(row)
    cases.sort(key=lambda r: str(r["case_id"]))
    return cases


def resolve_inputs(case: Dict[str, Any]) -> Dict[str, Any]:
    """Merge reference-machine preset + explicit overrides into a PointInputs dict."""
    ref_name = str(case.get("reference_machine") or "").strip()
    base: Dict[str, Any] = {}
    if ref_name:
        if ref_name not in REFERENCE_MACHINES:
            raise KeyError(f"Unknown reference_machine: {ref_name!r}")
        base.update(REFERENCE_MACHINES[ref_name])
    overrides = case.get("inputs") or {}
    if not isinstance(overrides, dict):
        raise TypeError("case.inputs must be a dict")
    base.update({k: v for k, v in overrides.items() if not str(k).startswith("_")})
    # Drop non-PointInputs keys early via PointInputs.from_dict
    pi = PointInputs.from_dict(base)
    return {k: getattr(pi, k) for k in pi.__dict__.keys()}


def _constraint_as_intent_dict(c: Any, severity: str) -> Dict[str, Any]:
    value = float(getattr(c, "value", float("nan")))
    limit = getattr(c, "limit", float("nan"))
    try:
        limit_f = float(limit)
    except Exception:
        limit_f = float("nan")
    return {
        "name": str(getattr(c, "name", "")),
        "value": value,
        "limit": limit_f if math.isfinite(limit_f) else None,
        "sense": str(getattr(c, "sense", "<=")),
        "passed": bool(getattr(c, "passed", True)),
        "severity": severity,
        "margin_frac": getattr(c, "margin_frac", None),
        "units": str(getattr(c, "units", "") or ""),
        "group": str(getattr(c, "group", "") or ""),
    }


def apply_design_intent_severities(
    constraints: Sequence[Any],
    *,
    design_intent: str,
) -> List[Dict[str, Any]]:
    """Remap constraint severities to Point Designer Design Intent policy.

    Non-finite values are omitted (not evaluated — do not gate feasibility).
    Research: only q95 hard; engineering soft; TBR ignored.
    Reactor: full reactor hard set (unknown failures stay hard).
    """
    k = design_intent_key(design_intent)
    hard = hard_constraint_names_for_intent(design_intent)
    ignore = ignored_constraint_names_for_intent(design_intent)
    soft = set(_INTENT_SOFT.get(k, set()))
    out: List[Dict[str, Any]] = []
    for c in constraints:
        try:
            value = float(getattr(c, "value", float("nan")))
        except Exception:
            continue
        if not math.isfinite(value):
            continue
        name = str(getattr(c, "name", ""))
        if name in ignore:
            sev = "ignored"
        elif name in soft or (k == "research" and name not in hard):
            sev = "diagnostic"
        elif name in hard or k == "reactor":
            sev = "hard"
        else:
            sev = "diagnostic"
        out.append(_constraint_as_intent_dict(c, sev))
    return out


def _stable_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def citation_sha256(payload: Dict[str, Any]) -> str:
    """SHA-256 of a timestamp-free citation payload."""
    return hashlib.sha256(_stable_json_bytes(payload)).hexdigest()


def evaluate_champion_case(
    case: Dict[str, Any],
    *,
    created_unix: float = _CHAMPION_EPOCH_UNIX,
) -> Dict[str, Any]:
    """Evaluate one champion case; return summary + run artifact + citation hash."""
    case_id = str(case["case_id"])
    design_intent = str(case.get("design_intent") or "Research")
    raw_expect = case.get("expect_hard_feasible", None)
    if raw_expect is None:
        expect_flag: Optional[bool] = None
    elif isinstance(raw_expect, bool):
        expect_flag = raw_expect
    else:
        expect_flag = str(raw_expect).strip().lower() in ("1", "true", "yes", "feasible")
    inputs = resolve_inputs(case)
    pi = PointInputs.from_dict(inputs)
    evr = Evaluator(label=f"champion:{case_id}", cache_enabled=False).evaluate(pi)
    if not evr.ok or not isinstance(evr.out, dict):
        raise RuntimeError(f"Evaluator failed for {case_id}: {evr.message}")
    outputs = dict(evr.out)
    raw_cons = evaluate_constraints(outputs)
    cons = apply_design_intent_severities(raw_cons, design_intent=design_intent)
    failed = [c["name"] for c in cons if not c.get("passed", True)]
    classified = classify_failed_constraints(failed, design_intent=design_intent)

    art = build_run_artifact(
        inputs=inputs,
        outputs=outputs,
        constraints=cons,
        meta={
            "created_unix": float(created_unix),
            "label": case_id,
            "mode": "champion",
            "notes": str(case.get("title") or case_id),
        },
    )
    hard_feasible = bool((art.get("kpis") or {}).get("feasible_hard"))
    atlas = art.get("no_solution_atlas")
    atlas_summary: Optional[Dict[str, Any]] = None
    if isinstance(atlas, dict):
        atlas_summary = {
            "schema": atlas.get("schema"),
            "verdict": atlas.get("verdict"),
            "dominant_mechanism": atlas.get("dominant_mechanism"),
            "dominant_constraint": atlas.get("dominant_constraint"),
        }

    cite_body = {
        "schema": CHAMPION_SCHEMA,
        "case_id": case_id,
        "shams_version": read_shams_version(),
        "design_intent": design_intent,
        "intent_key": design_intent_key(design_intent),
        "input_hash": art.get("input_hash"),
        "hard_feasible": hard_feasible,
        "classification": classified,
        "atlas": atlas_summary,
        "kpi_keys": {
            "Q_DT_eqv": outputs.get("Q_DT_eqv"),
            "q95": outputs.get("q95", outputs.get("q95_proxy")),
            "q_div_MW_m2": outputs.get("q_div_MW_m2"),
            "P_fus_MW": outputs.get("P_fus_MW", outputs.get("Pfus_DT_MW")),
        },
    }
    sha = citation_sha256(cite_body)

    summary = {
        "case_id": case_id,
        "title": str(case.get("title") or case_id),
        "family": str(case.get("family") or ""),
        "story": str(case.get("story") or ""),
        "design_intent": design_intent,
        "intent_key": design_intent_key(design_intent),
        "reference_machine": str(case.get("reference_machine") or ""),
        "hard_feasible": hard_feasible,
        "expect_hard_feasible": expect_flag,
        "ok_blocking": len(classified.get("blocking") or []) == 0,
        "classification": classified,
        "dominant_mechanism": (atlas_summary or {}).get("dominant_mechanism") if not hard_feasible else None,
        "dominant_constraint": (atlas_summary or {}).get("dominant_constraint") if not hard_feasible else None,
        "no_solution_atlas": atlas_summary,
        "citation_sha256": sha,
        "input_hash": art.get("input_hash"),
        "shams_version": read_shams_version(),
        "policy": constraint_policy_snapshot(design_intent),
        "kpis": {
            "Q_DT_eqv": outputs.get("Q_DT_eqv"),
            "q95": outputs.get("q95", outputs.get("q95_proxy")),
            "q_div_MW_m2": outputs.get("q_div_MW_m2"),
            "P_fus_MW": outputs.get("P_fus_MW", outputs.get("Pfus_DT_MW")),
            "H98": outputs.get("H98"),
        },
    }
    return {"summary": summary, "artifact": art, "citation_payload": cite_body}


def run_all_champions(
    *,
    cases_path: Optional[Path] = None,
    created_unix: float = _CHAMPION_EPOCH_UNIX,
) -> Dict[str, Any]:
    """Evaluate all champion cases; return pack summary (deterministic)."""
    cases = load_champion_definitions(cases_path)
    results: List[Dict[str, Any]] = []
    for case in cases:
        results.append(evaluate_champion_case(case, created_unix=created_unix))

    pack = {
        "schema": CHAMPION_SCHEMA,
        "shams_version": read_shams_version(),
        "n_cases": len(results),
        "n_hard_feasible": sum(1 for r in results if r["summary"]["hard_feasible"]),
        "n_infeasible": sum(1 for r in results if not r["summary"]["hard_feasible"]),
        "cases": [r["summary"] for r in results],
        "results": results,
    }
    pack["pack_sha256"] = citation_sha256(
        {
            "schema": CHAMPION_SCHEMA,
            "shams_version": pack["shams_version"],
            "cases": [
                {
                    "case_id": s["case_id"],
                    "hard_feasible": s["hard_feasible"],
                    "citation_sha256": s["citation_sha256"],
                    "dominant_mechanism": s.get("dominant_mechanism"),
                    "dominant_constraint": s.get("dominant_constraint"),
                }
                for s in pack["cases"]
            ],
        }
    )
    return pack


def write_champion_pack(
    outdir: Path,
    *,
    cases_path: Optional[Path] = None,
    created_unix: float = _CHAMPION_EPOCH_UNIX,
) -> Dict[str, Any]:
    """Run champions and write artifacts + summary.json under outdir."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    art_dir = outdir / "artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)

    pack = run_all_champions(cases_path=cases_path, created_unix=created_unix)
    for r in pack["results"]:
        case_id = r["summary"]["case_id"]
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in case_id)
        path = art_dir / f"{safe}.json"
        path.write_text(json.dumps(r["artifact"], indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        r["summary"]["artifact_path"] = str(path.relative_to(outdir)).replace("\\", "/")

    summary_doc = {
        "schema": CHAMPION_SCHEMA,
        "shams_version": pack["shams_version"],
        "pack_sha256": pack["pack_sha256"],
        "n_cases": pack["n_cases"],
        "n_hard_feasible": pack["n_hard_feasible"],
        "n_infeasible": pack["n_infeasible"],
        "cases": pack["cases"],
        "honesty": {
            "process_mfile_invented": False,
            "process_retired_claimed": False,
            "device_names": "class/like inspiration only — not measured device parity",
            "feasibility_basis": (
                "Point Designer Design Intent hard set (Research: q95; Reactor: full reactor hard set); "
                "non-finite constraint values omitted"
            ),
            "release_status": "CONDITIONAL — see docs/LIMITATIONS.md",
        },
    }
    (outdir / "summary.json").write_text(
        json.dumps(summary_doc, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    pack["summary_path"] = str(outdir / "summary.json")
    return pack
