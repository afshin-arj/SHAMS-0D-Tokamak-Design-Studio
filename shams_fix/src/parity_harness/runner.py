from __future__ import annotations

"""Benchmark runner for PROCESS parity harness (v364.0).

Runs a suite of benchmark cases through the frozen evaluator and produces:
- per-case SHAMS run artifacts
- optional PROCESS mapping artifacts (intent map)
- delta dossiers when PROCESS outputs are supplied

Determinism: no randomized operations; file ordering is stable.

© 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
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

from .case_io import BenchmarkCase, load_case, discover_cases
from .process_map import map_shams_to_process_like
from .delta_dossier import build_delta_dossier


@dataclass(frozen=True)
class BenchmarkRunConfig:
    suite: str = "v364"
    include_profile_contracts: bool = True
    profile_contracts_tier: str = "robust"
    profile_contracts_preset: str = "C16"
    include_intent_map: bool = True


def run_suite(
    cases_dir: Path,
    out_dir: Path,
    *,
    cfg: Optional[BenchmarkRunConfig] = None,
    process_outputs_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    cfg = cfg or BenchmarkRunConfig()
    cases_dir = Path(cases_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ev = Evaluator(label=f"bench_{cfg.suite}", cache_enabled=False)

    case_paths = discover_cases(cases_dir, suite=cfg.suite)
    results: List[Dict[str, Any]] = []

    for p in case_paths:
        c = load_case(p)
        r = run_case(c, ev, out_dir, cfg=cfg, process_outputs_dir=process_outputs_dir)
        results.append(r)

    summary = {
        "schema": "shams_benchmark_suite_result.v1",
        "suite": cfg.suite,
        "n_cases": len(results),
        "cases": results,
    }
    (out_dir / "suite_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def run_case(
    case: BenchmarkCase,
    ev: Evaluator,
    out_dir: Path,
    *,
    cfg: BenchmarkRunConfig,
    process_outputs_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    out_dir = Path(out_dir)
    case_dir = out_dir / case.case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    pi = PointInputs(**case.inputs)
    evr = ev.evaluate(pi)
    if not evr.ok:
        art: Dict[str, Any] = {
            "schema_version": "shams_run_artifact.v1",
            "kind": "shams_run_artifact",
            "inputs": case.inputs,
            "outputs": {},
            "constraints": [],
            "kpis": {"feasible_hard": False, "min_hard_margin": float("nan")},
            "error": evr.message,
        }
    else:
        out = evr.out
        cons = build_constraints_from_outputs(out, design_intent=f"benchmark::{case.case_id}")
        art = build_run_artifact(inputs=case.inputs, outputs=out, constraints=cons)

    # Profile contracts overlay (v362)
    if cfg.include_profile_contracts:
        try:
            pc_rep = evaluate_profile_contracts_v362(pi, preset=str(cfg.profile_contracts_preset), tier=str(cfg.profile_contracts_tier))
            art["profile_contracts_v362"] = pc_rep.to_dict() if hasattr(pc_rep, "to_dict") else dict(pc_rep)  # type: ignore
        except Exception as ex:
            art["profile_contracts_v362"] = {"schema": "profile_contracts_v362_error.v1", "error": str(ex)}

    # Optional PROCESS intent map
    intent_map = None
    if cfg.include_intent_map:
        try:
            intent_map = map_shams_to_process_like(case.inputs)
        except Exception as ex:
            intent_map = {"schema": "shams_process_map_error.v1", "error": str(ex)}

    (case_dir / "shams_artifact.json").write_text(json.dumps(art, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if intent_map is not None:
        (case_dir / "process_intent_map.json").write_text(json.dumps(asdict(intent_map), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Optional delta dossier if PROCESS outputs exist
    dossier = None
    if process_outputs_dir is not None:
        proc_path = Path(process_outputs_dir) / f"{case.case_id}.json"
        if proc_path.exists():
            try:
                proc = json.loads(proc_path.read_text(encoding="utf-8"))
            except Exception:
                proc = None
            dossier = build_delta_dossier(
                case=case,
                shams_artifact=art,
                process_outputs=proc,
                process_intent_map=intent_map,
            )
            (case_dir / "delta_dossier.json").write_text(json.dumps(dossier, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            (case_dir / "delta_dossier.md").write_text(dossier.get("markdown", ""), encoding="utf-8")

    return {
        "case_id": case.case_id,
        "label": case.label,
        "path": str(case_dir),
        "has_process": bool(dossier is not None),
        "feasible_hard": bool(((art.get("kpis") or {}).get("feasible_hard")) if isinstance(art.get("kpis"), dict) else False),
    }

# Convenience wrapper used by UI/tests

def run_benchmark_suite(
    *,
    suite: str = "v364",
    cases_dir: Path,
    out_dir: Path,
    process_dir: Path | None = None,
    generate_delta_dossiers: bool = False,
    include_profile_contracts: bool = True,
    profile_contracts_tier: str = "robust",
    profile_contracts_preset: str = "C16",
    include_intent_map: bool = True,
    process_outputs_by_case: dict[str, dict] | None = None,
) -> dict:
    """Run a deterministic parity harness suite.

    `process_dir` optionally points to JSON files named '<suite>_<case_id>.json'.
    `process_outputs_by_case` is an optional in-memory override used by the UI.
    """
    cfg = BenchmarkRunConfig(
        suite=str(suite),
        include_profile_contracts=bool(include_profile_contracts),
        profile_contracts_tier=str(profile_contracts_tier),
        profile_contracts_preset=str(profile_contracts_preset),
        include_intent_map=bool(include_intent_map),
    )

    # If the UI provides an in-memory PROCESS blob for a single case, write it to a temp dir
    # under out_dir so the normal loader path is used (audit-friendly, deterministic).
    process_outputs_dir = Path(process_dir) if process_dir is not None else None
    if process_outputs_by_case:
        tmp_proc = Path(out_dir) / "_process_inputs"
        tmp_proc.mkdir(parents=True, exist_ok=True)
        for cid, blob in process_outputs_by_case.items():
            (tmp_proc / f"{cfg.suite}_{cid}.json").write_text(
                __import__("json").dumps(blob, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        process_outputs_dir = tmp_proc

    summary = run_suite(
        cases_dir=Path(cases_dir),
        out_dir=Path(out_dir),
        cfg=cfg,
        process_outputs_dir=process_outputs_dir,
    )

    if generate_delta_dossiers:
        # Delta dossiers are generated per-case during run if process outputs exist; this flag
        # is retained for interface stability.
        pass

    return summary
