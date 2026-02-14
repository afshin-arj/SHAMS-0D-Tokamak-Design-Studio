from __future__ import annotations
"""Study Orchestrator + Paper Pack (v125)

One-click, reproducible, publishable bundle:
- run artifact (baseline)
- mission overlay (v121) [optional]
- explainability (v122) [optional]
- evidence graph + traceability (v123) [optional]
- feasibility atlas (v124) [optional]
- study kit (v123B) [optional]
- methods appendix (auto-written)
- manifest with SHA256

All additive; no physics/solver changes.
"""

from typing import Any, Dict, Optional, Tuple
import time, json, hashlib, zipfile
from io import BytesIO

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def _json_bytes(d: Dict[str, Any]) -> bytes:
    return json.dumps(d, indent=2, sort_keys=True).encode("utf-8")

def build_methods_appendix(
    *,
    baseline_run_artifact: Dict[str, Any],
    mission_name: Optional[str] = None,
    atlas_config: Optional[Dict[str, Any]] = None,
    version: str = "v125",
) -> str:
    meta = baseline_run_artifact.get("meta", {}) if isinstance(baseline_run_artifact.get("meta"), dict) else {}
    solver = baseline_run_artifact.get("solver", {}) if isinstance(baseline_run_artifact.get("solver"), dict) else {}
    cs = baseline_run_artifact.get("constraints_summary", {}) if isinstance(baseline_run_artifact.get("constraints_summary"), dict) else {}
    lines = []
    lines.append("# METHODS APPENDIX (auto-generated)")
    lines.append("")
    lines.append(f"SHAMS release: {version}")
    lines.append(f"Generated UTC: {_created_utc()}")
    lines.append("")
    lines.append("## Baseline run")
    lines.append(f"- Run id: {baseline_run_artifact.get('id')}")
    lines.append(f"- Mode label: {meta.get('mode') or meta.get('label') or 'N/A'}")
    lines.append(f"- Solver message: {solver.get('message','N/A')}")
    lines.append(f"- Feasible: {cs.get('feasible')}")
    lines.append(f"- Worst hard: {cs.get('worst_hard')} (margin frac: {cs.get('worst_hard_margin_frac')})")
    lines.append(f"- Worst soft: {cs.get('worst_soft')} (margin frac: {cs.get('worst_soft_margin_frac')})")
    lines.append("")
    if mission_name:
        lines.append("## Mission overlay")
        lines.append(f"- Mission: {mission_name}")
        lines.append("")
    if atlas_config:
        lines.append("## Feasibility Boundary Atlas")
        lines.append(f"- Lever X: {atlas_config.get('lever_x')} range={atlas_config.get('x_range')} nx={atlas_config.get('nx')}")
        lines.append(f"- Lever Y: {atlas_config.get('lever_y')} range={atlas_config.get('y_range')} ny={atlas_config.get('ny')}")
        lines.append("")
    lines.append("## Reproducibility notes")
    lines.append("- This pack contains post-processed evidence outputs only.")
    lines.append("- SHAMS physics, constraints, and solver behavior are unchanged by this export.")
    lines.append("")
    return "\n".join(lines) + "\n"

def build_paper_pack_zip(
    *,
    baseline_run_artifact: Dict[str, Any],
    mission_report: Optional[Dict[str, Any]] = None,
    explainability_report: Optional[Dict[str, Any]] = None,
    evidence_graph: Optional[Dict[str, Any]] = None,
    traceability_table: Optional[Dict[str, Any]] = None,
    traceability_csv: Optional[bytes] = None,
    feasibility_atlas_meta: Optional[Dict[str, Any]] = None,
    atlas_bundle_zip: Optional[bytes] = None,
    study_kit_zip: Optional[bytes] = None,
    version: str = "v125",
) -> Dict[str, Any]:
    if not (isinstance(baseline_run_artifact, dict) and baseline_run_artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("expected shams_run_artifact baseline")

    created = _created_utc()
    files: Dict[str, bytes] = {}

    files["run_artifact.json"] = _json_bytes(baseline_run_artifact)

    mission_name = None
    if isinstance(mission_report, dict):
        files["mission_report.json"] = _json_bytes(mission_report)
        mission_name = mission_report.get("mission_name")

    if isinstance(explainability_report, dict):
        files["explainability_report.json"] = _json_bytes(explainability_report)
        files["explainability_report.txt"] = (explainability_report.get("narrative","") or "").encode("utf-8")

    if isinstance(evidence_graph, dict):
        files["evidence_graph.json"] = _json_bytes(evidence_graph)

    if isinstance(traceability_table, dict):
        files["traceability_table.json"] = _json_bytes(traceability_table)
    if isinstance(traceability_csv, (bytes, bytearray)):
        files["traceability.csv"] = bytes(traceability_csv)

    if isinstance(feasibility_atlas_meta, dict):
        files["feasibility_atlas_v124.json"] = _json_bytes(feasibility_atlas_meta)
    if isinstance(atlas_bundle_zip, (bytes, bytearray)):
        files["atlas_bundle_v124.zip"] = bytes(atlas_bundle_zip)

    if isinstance(study_kit_zip, (bytes, bytearray)):
        files["study_kit_v123B.zip"] = bytes(study_kit_zip)

    methods = build_methods_appendix(
        baseline_run_artifact=baseline_run_artifact,
        mission_name=mission_name,
        atlas_config=(feasibility_atlas_meta.get("grid") if isinstance(feasibility_atlas_meta, dict) else None),
        version=version,
    )
    files["METHODS_APPENDIX.md"] = methods.encode("utf-8")

    files["README.md"] = ("""# SHAMS Paper Pack (v125)

This bundle is a one-click, publishable aggregation of SHAMS artifacts for a single design study.

Contents (as available):
- run_artifact.json
- mission_report.json
- explainability_report.json / .txt
- evidence_graph.json
- traceability_table.json + traceability.csv
- feasibility_atlas_v124.json + atlas_bundle_v124.zip
- study_kit_v123B.zip
- METHODS_APPENDIX.md
- manifest.json (SHA256 integrity)

All outputs are additive evidence exports. No physics/constraints/solver behavior is changed.
""").encode("utf-8")

    manifest = {
        "kind":"shams_paper_pack_manifest",
        "version": version,
        "created_utc": created,
        "files": {k: {"sha256": _sha256_bytes(v), "bytes": len(v)} for k,v in files.items()},
        "notes":[
            "Paper pack is an additive export intended for publication and audit.",
        ],
    }
    files["manifest.json"] = _json_bytes(manifest)

    zbuf = BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k, v)

    return {"kind":"shams_paper_pack", "version": version, "created_utc": created, "manifest": manifest, "zip_bytes": zbuf.getvalue()}
