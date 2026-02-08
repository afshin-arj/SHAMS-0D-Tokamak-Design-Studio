from __future__ import annotations
"""Design Study Kit (v123B)

Builds a publishable bundle aggregating the key outputs produced so far:
- run artifact
- mission report (if provided)
- tolerance envelope report (if provided)
- explainability report (if provided)
- evidence graph + traceability
- authority pack (if provided)
- downstream bundle / decision pack (if provided)

Additive export only.
"""

from typing import Any, Dict, Optional
import time, json, hashlib, zipfile
from io import BytesIO

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def build_study_kit_zip(
    *,
    run_artifact: Dict[str, Any],
    mission_report: Optional[Dict[str, Any]] = None,
    tolerance_envelope_report: Optional[Dict[str, Any]] = None,
    explainability_report: Optional[Dict[str, Any]] = None,
    evidence_graph: Optional[Dict[str, Any]] = None,
    traceability_table: Optional[Dict[str, Any]] = None,
    authority_pack_zip: Optional[bytes] = None,
    optimizer_downstream_bundle_zip: Optional[bytes] = None,
    decision_pack_zip: Optional[bytes] = None,
    version: str = "v123B",
) -> Dict[str, Any]:
    if not (isinstance(run_artifact, dict) and run_artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("expected shams_run_artifact")

    created = _created_utc()

    files: Dict[str, bytes] = {}
    files["README.md"] = ("""# SHAMS Design Study Kit

This bundle is a publishable aggregation of SHAMS artifacts for a single design study.
All files are read-only evidence outputs. No optimization is implied.

Contents:
- run_artifact.json
- optional: mission_report.json, tolerance_envelope_report.json, explainability_report.json
- evidence_graph.json + traceability.csv
- optional: authority_pack.zip, optimizer_downstream_bundle.zip, decision_pack.zip
- manifest.json (SHA256 integrity)

""").encode("utf-8")

    files["run_artifact.json"] = json.dumps(run_artifact, indent=2, sort_keys=True).encode("utf-8")

    if isinstance(mission_report, dict):
        files["mission_report.json"] = json.dumps(mission_report, indent=2, sort_keys=True).encode("utf-8")
    if isinstance(tolerance_envelope_report, dict):
        files["tolerance_envelope_report.json"] = json.dumps(tolerance_envelope_report, indent=2, sort_keys=True).encode("utf-8")
    if isinstance(explainability_report, dict):
        files["explainability_report.json"] = json.dumps(explainability_report, indent=2, sort_keys=True).encode("utf-8")
        files["explainability_report.txt"] = (explainability_report.get("narrative","") or "").encode("utf-8")
    if isinstance(evidence_graph, dict):
        files["evidence_graph.json"] = json.dumps(evidence_graph, indent=2, sort_keys=True).encode("utf-8")
    if isinstance(traceability_table, dict):
        files["traceability_table.json"] = json.dumps(traceability_table, indent=2, sort_keys=True).encode("utf-8")

    if isinstance(authority_pack_zip, (bytes, bytearray)):
        files["authority_pack.zip"] = bytes(authority_pack_zip)
    if isinstance(optimizer_downstream_bundle_zip, (bytes, bytearray)):
        files["optimizer_downstream_bundle.zip"] = bytes(optimizer_downstream_bundle_zip)
    if isinstance(decision_pack_zip, (bytes, bytearray)):
        files["decision_pack.zip"] = bytes(decision_pack_zip)

    manifest = {
        "kind":"shams_design_study_kit_manifest",
        "version": version,
        "created_utc": created,
        "files": {k: {"sha256": _sha256_bytes(v), "bytes": len(v)} for k,v in files.items()},
        "notes":[
            "Study kit is an additive evidence bundle intended for publication and handoff.",
        ],
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    files["manifest.json"] = manifest_bytes

    zbuf = BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k, v)

    return {"kind":"shams_design_study_kit", "version": version, "created_utc": created, "manifest": manifest, "zip_bytes": zbuf.getvalue()}
