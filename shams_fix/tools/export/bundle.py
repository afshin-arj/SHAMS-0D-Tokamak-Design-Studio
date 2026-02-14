from __future__ import annotations
"""Unified Export Bundle (v94)"""
import io, json, zipfile, tempfile
from pathlib import Path
from typing import Any, Dict, Optional

def _zip_add_file(z: zipfile.ZipFile, path: Path, arcname: str):
    if path.exists() and path.is_file():
        z.write(str(path), arcname=arcname)

def build_export_bundle_bytes(
    repo_root: Path,
    point_artifact: Optional[Dict[str, Any]] = None,
    systems_artifact: Optional[Dict[str, Any]] = None,
    scan_artifact: Optional[Dict[str, Any]] = None,
    pareto_artifact: Optional[Dict[str, Any]] = None,
    opt_artifact: Optional[Dict[str, Any]] = None,
    feasible_search_artifact: Optional[Dict[str, Any]] = None,
    certified_search_artifact: Optional[Dict[str, Any]] = None,
    repair_evidence_artifact: Optional[Dict[str, Any]] = None,
    interval_refinement_artifact: Optional[Dict[str, Any]] = None,
    sandbox_run: Optional[Dict[str, Any]] = None,
    figures_pack_zip: Optional[bytes] = None,
    include_readme: bool = True,
    **_ignored_kwargs,
) -> bytes:
    """Build a single ZIP bundle containing the most recent artifacts + schemas + log.

    Backward/forward compatible: extra keyword args are ignored.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        _zip_add_file(z, repo_root / "VERSION", "VERSION")
        for p in repo_root.glob("PATCH_NOTES*"):
            _zip_add_file(z, p, p.name)

        # Global activity log (best-effort)
        try:
            _zip_add_file(z, repo_root / "runs" / "activity_log_current.log", "activity.log")
        except Exception:
            pass

        schdir = repo_root / "schemas"
        if schdir.exists():
            for p in schdir.glob("*.json"):
                _zip_add_file(z, p, f"schemas/{p.name}")

        if point_artifact is not None:
            z.writestr("artifact_point.json", json.dumps(point_artifact, indent=2, sort_keys=True))
        if systems_artifact is not None:
            z.writestr("systems_artifact.json", json.dumps(systems_artifact, indent=2, sort_keys=True))
        if feasible_search_artifact is not None:
            z.writestr("feasible_search.json", json.dumps(feasible_search_artifact, indent=2, sort_keys=True))
        if certified_search_artifact is not None:
            z.writestr("certified_search.json", json.dumps(certified_search_artifact, indent=2, sort_keys=True))
        if repair_evidence_artifact is not None:
            z.writestr("repair_evidence.json", json.dumps(repair_evidence_artifact, indent=2, sort_keys=True))
        if interval_refinement_artifact is not None:
            z.writestr("interval_refinement.json", json.dumps(interval_refinement_artifact, indent=2, sort_keys=True))
        if scan_artifact is not None:
            z.writestr("scan_artifact.json", json.dumps(scan_artifact, indent=2, sort_keys=True))
        if pareto_artifact is not None:
            z.writestr("pareto_artifact.json", json.dumps(pareto_artifact, indent=2, sort_keys=True))
        if opt_artifact is not None:
            z.writestr("opt_artifact.json", json.dumps(opt_artifact, indent=2, sort_keys=True))
        if sandbox_run is not None:
            z.writestr("sandbox_run.json", json.dumps(sandbox_run, indent=2, sort_keys=True))

        if isinstance(figures_pack_zip, (bytes, bytearray)) and len(figures_pack_zip) > 0:
            z.writestr("paper_figures_pack.zip", bytes(figures_pack_zip))

        # Capsule (best-effort, from Point Designer artifact)
        if point_artifact is not None:
            try:
                from tools.export.capsule import export_capsule
                tmp = Path(tempfile.mkdtemp(prefix="shams_bundle_capsule_"))
                export_capsule(point_artifact, str(tmp / "capsule"))
                capdir = tmp / "capsule"
                for p2 in capdir.rglob("*"):
                    if p2.is_file():
                        z.write(str(p2), arcname=f"capsule/{p2.relative_to(capdir)}")
            except Exception:
                pass

        # manifest (best-effort)
        try:
            from tools.export.manifest import build_manifest
            inline = {}
            if isinstance(figures_pack_zip, (bytes, bytearray)):
                inline["paper_figures_pack.zip"] = bytes(figures_pack_zip)
            manifest = build_manifest(version="v178", export_kind="unified_bundle", files={}, inline_bytes=inline)
            z.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        except Exception:
            pass

        if include_readme:
            z.writestr(
                "README.txt",
                "SHAMS Unified Export Bundle\n"
                "- artifact_point.json (if available)\n"
                "- systems_artifact.json (if available)\n"
                "- feasible_search.json (if available)\n"
                "- certified_search.json / repair_evidence.json / interval_refinement.json (if available)\n"
                "- scan_artifact.json / pareto_artifact.json / opt_artifact.json (if available)\n"
                "- activity.log (best-effort)\n",
            )
    return buf.getvalue()
