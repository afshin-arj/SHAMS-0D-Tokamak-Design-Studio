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
    var_names = {str(v["name"]) for v in variables}
    # Anchor all non-swept fields so batch eval can construct PointInputs.
    fixed_inputs = {k: v for k, v in base.items() if k not in var_names}
    return {
        "schema": "shams_campaign.v1",
        "name": "campaign_v363",
        "intent": "concept",
        "evaluator_label": "hot_ion_point",
        "variables": variables,
        "fixed_inputs": fixed_inputs,
        "generator": {"mode": "sobol", "n": 16, "seed": 123},
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
        from src.campaign.eval import evaluate_campaign_candidates, write_results_jsonl
    except ImportError:
        from campaign.eval import evaluate_campaign_candidates, write_results_jsonl  # type: ignore
    from ui_nicegui.evaluate import ui_evaluator

    td = Path(tempfile.gettempdir()) / "shams_campaigns"
    td.mkdir(parents=True, exist_ok=True)
    out_jsonl = td / f"{spec.name}_results_v363.jsonl"
    ev = ui_evaluator(origin="NiceGUI:SystemSuite:Campaign", cache_enabled=False)
    rows, summary = evaluate_campaign_candidates(spec, candidates, evaluator=ev)
    write_results_jsonl(rows, out_jsonl, include_artifact=bool(getattr(spec, "include_full_artifact", False)))
    preview: List[dict] = []
    for r in rows:
        preview.append({
            "cid": r.cid,
            "inputs": dict(r.inputs or {}),
            "feasible_hard": bool(r.feasible_hard),
            "verdict": str(r.verdict),
            "dominant_mechanism": str(r.dominant_mechanism),
            "worst_hard_margin": r.worst_hard_margin,
            **{k: v for k, v in (r.inputs or {}).items()},
        })
    return summary, watermark_campaign_preview_rows(preview), out_jsonl.read_bytes()


def watermark_campaign_preview_rows(rows: List[dict]) -> List[dict]:
    """PHYS-KPI-001: suppress claim KPI cells on hard-infeasible campaign preview rows."""
    from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table, is_claim_kpi_key

    out: List[dict] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        feas = bool(r.get("feasible_hard"))
        if feas:
            out.append(dict(r))
            continue
        rr = dict(r)
        for k, v in list(rr.items()):
            if is_claim_kpi_key(str(k)):
                rr[k] = format_claim_kpi_for_table(str(k), v, feasible=False)
        out.append(rr)
    return out


def watermark_campaign_jsonl_bytes(data: bytes) -> bytes:
    """PHYS-KPI-001: download-time watermark of campaign JSONL (session bytes stay raw).

    Dict rows with ``feasible_hard`` False (or ``feasible`` False) have claim KPI
    keys replaced via ``format_claim_kpi_for_table`` — same rule as
    ``watermark_campaign_preview_rows``. Non-JSON lines are kept as-is.
    """
    import json

    from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table, is_claim_kpi_key

    if not data:
        return b""
    raw = data.decode("utf-8", errors="replace")
    out_lines: List[str] = []
    for line in raw.splitlines(keepends=False):
        stripped = line.strip()
        if not stripped:
            out_lines.append(line)
            continue
        try:
            obj = json.loads(stripped)
        except (TypeError, ValueError, json.JSONDecodeError):
            out_lines.append(line)
            continue
        if not isinstance(obj, dict):
            out_lines.append(json.dumps(obj, default=str, ensure_ascii=False))
            continue
        if "feasible_hard" in obj:
            infeasible = not bool(obj.get("feasible_hard"))
        elif "feasible" in obj:
            infeasible = not bool(obj.get("feasible"))
        else:
            infeasible = False
        if infeasible:
            rr = dict(obj)
            for k, v in list(rr.items()):
                if is_claim_kpi_key(str(k)):
                    rr[k] = format_claim_kpi_for_table(str(k), v, feasible=False)
            out_lines.append(json.dumps(rr, default=str, ensure_ascii=False))
        else:
            out_lines.append(json.dumps(obj, default=str, ensure_ascii=False))
    body = "\n".join(out_lines)
    if raw.endswith("\n") and body:
        body += "\n"
    return body.encode("utf-8")


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
    """Run selected parity cases via the frozen harness (UI wrapper).

    Copies requested case files into a temp cases_dir so the runner discovers
    only those cases, then returns the suite summary dict.
    """
    import shutil

    try:
        from src.parity_harness.runner import run_benchmark_suite
    except ImportError:
        from parity_harness.runner import run_benchmark_suite  # type: ignore
    from ui_nicegui.evaluate import ui_evaluator

    td = Path(tempfile.mkdtemp(prefix="shams_parity_"))
    cases_dir = td / "cases"
    out_dir = td / "out"
    cases_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    for p in case_paths:
        src = Path(p)
        if src.is_file():
            shutil.copy2(src, cases_dir / src.name)
    ev = ui_evaluator(origin="NiceGUI:SystemSuite:Parity", cache_enabled=False)
    return run_benchmark_suite(
        suite=str(suite),
        cases_dir=cases_dir,
        out_dir=out_dir,
        process_dir=None,
        generate_delta_dossiers=False,
        include_profile_contracts=True,
        profile_contracts_preset=str(preset),
        profile_contracts_tier=str(tier),
        process_outputs_by_case=process_outputs_by_case or {},
        evaluator=ev,
    )


def parity_zip_bytes(report: dict) -> bytes:
    """Build a reviewer pack ZIP without importing the Streamlit tool module."""
    import io
    import zipfile

    buf = io.BytesIO()
    readme = (
        "SHAMS — PROCESS Benchmark & Parity Harness 3.0 (v364)\n\n"
        "This ZIP is a reviewer pack generated by SHAMS NiceGUI System Suite.\n"
        "SHAMS truth is frozen and deterministic.\n"
    )
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("README_REVIEWER_PACK.txt", readme)
        z.writestr("parity_report.json", json.dumps(report, indent=2, sort_keys=True))
        cases = report.get("cases", {}) if isinstance(report.get("cases"), dict) else {}
        for cid, blob in cases.items():
            if not isinstance(blob, dict):
                continue
            z.writestr(
                f"cases/{cid}/shams_artifact.json",
                json.dumps(blob.get("shams_artifact", {}), indent=2, sort_keys=True),
            )
            z.writestr(
                f"cases/{cid}/process_map.json",
                json.dumps(blob.get("process_map", {}), indent=2, sort_keys=True),
            )
            z.writestr(
                f"cases/{cid}/delta_dossier.json",
                json.dumps(blob.get("delta_dossier", {}), indent=2, sort_keys=True),
            )
            md = blob.get("delta_dossier_md", "")
            if isinstance(md, str) and md.strip():
                z.writestr(f"cases/{cid}/delta_dossier.md", md)
    return buf.getvalue()
