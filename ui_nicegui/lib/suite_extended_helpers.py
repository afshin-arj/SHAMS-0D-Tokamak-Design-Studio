"""System Suite extended panels — Campaign Pack & Benchmark Parity."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ui_nicegui.bootstrap import repo_root


def default_campaign_template(point_inputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base = dict(point_inputs or {})
    suggested: List[str] = []
    for k in ("R0_m", "a_m", "B0_T", "Ip_MA", "P_aux_MW", "kappa", "delta", "Bt_T", "Paux_MW"):
        if k in base:
            suggested.append(k)
    if not suggested:
        for k, v in base.items():
            if isinstance(v, (int, float)):
                suggested.append(k)
            if len(suggested) >= 5:
                break
    variables = []
    for k in suggested:
        v = base.get(k)
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        span = 0.15 * (abs(fv) if abs(fv) > 1e-12 else 1.0)
        variables.append({"name": k, "kind": "float", "lo": fv - span, "hi": fv + span})
    return {
        "schema": "shams_campaign.v1",
        "name": "campaign_v363",
        "intent": "concept",
        "evaluator_label": "hot_ion_point",
        "variables": variables,
        "fixed_inputs": {},
        "generator": {"mode": "sobol", "n": 64, "seed": 123},
        "profile_contracts": {"tier": "both", "preset": "C16"},
        "include_full_artifact": False,
    }


def parse_campaign_spec(spec_text: str):
    try:
        from src.campaign.spec import CampaignSpec, validate_campaign_spec
    except ImportError:
        from campaign.spec import CampaignSpec, validate_campaign_spec  # type: ignore
    d = json.loads(spec_text)
    spec = CampaignSpec.from_dict(d)
    validate_campaign_spec(spec)
    return spec


def generate_campaign_candidates(spec) -> list:
    try:
        from src.campaign.generate import generate_candidates
    except ImportError:
        from campaign.generate import generate_candidates  # type: ignore
    return generate_candidates(spec)


def export_campaign_zip(spec) -> bytes:
    try:
        from src.campaign.export import export_campaign_bundle
    except ImportError:
        from campaign.export import export_campaign_bundle  # type: ignore
    td = Path(tempfile.gettempdir()) / "shams_campaigns"
    td.mkdir(parents=True, exist_ok=True)
    out_zip = td / f"{spec.name}_campaign_bundle_v363.zip"
    export_campaign_bundle(spec, repo_root=Path(repo_root()), out_zip=out_zip)
    return out_zip.read_bytes()


def evaluate_campaign_batch(spec, candidates: list) -> Tuple[dict, list, bytes]:
    try:
        from src.campaign.eval import evaluate_campaign_candidates
    except ImportError:
        from campaign.eval import evaluate_campaign_candidates  # type: ignore
    td = Path(tempfile.gettempdir()) / "shams_campaigns"
    td.mkdir(parents=True, exist_ok=True)
    out_jsonl = td / f"{spec.name}_results_v363.jsonl"
    summary, rows = evaluate_campaign_candidates(spec, candidates=candidates, out_jsonl=out_jsonl)
    return summary, rows, out_jsonl.read_bytes()


def list_parity_cases(suite: str) -> List[Tuple[str, Path]]:
    try:
        from src.parity_harness.case_io import discover_cases
    except ImportError:
        from parity_harness.case_io import discover_cases  # type: ignore
    cases_dir = Path(repo_root()) / "benchmarks" / "cases"
    paths = discover_cases(cases_dir, suite=str(suite))
    out: List[Tuple[str, Path]] = []
    for p in paths:
        cid = p.stem.replace(f"{suite}_", "")
        out.append((cid, p))
    return out


def load_parity_case(path: Path) -> dict:
    try:
        from src.parity_harness.case_io import load_case
    except ImportError:
        from parity_harness.case_io import load_case  # type: ignore
    return load_case(path).to_dict()


def run_parity_suite(
    *,
    suite: str,
    case_paths: List[Path],
    preset: str = "C8",
    tier: str = "both",
    process_outputs_by_case: Optional[dict] = None,
) -> dict:
    try:
        from src.parity_harness.runner import run_benchmark_suite
    except ImportError:
        from parity_harness.runner import run_benchmark_suite  # type: ignore
    return run_benchmark_suite(
        suite=str(suite),
        case_paths=case_paths,
        profile_contracts_preset=str(preset),
        profile_contracts_tier=str(tier),
        process_outputs_by_case=process_outputs_by_case or {},
    )


def parity_zip_bytes(report: dict) -> bytes:
    from tools.benchmark_parity_harness_v364 import _pack_zip

    return _pack_zip(report)
