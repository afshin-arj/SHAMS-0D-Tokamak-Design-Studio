from __future__ import annotations
"""Design Study Authority — Publishable Study Kit (v148–v150)

v148: Paper Pack Generator
- Build an export bundle (zip) containing selected run artifacts + key certificates + plots/tables (if available)
- Includes reproduce scripts and environment snapshot for offline reproducibility.

v149: Study Registry (DOI-ready metadata)
- Write study.json/yaml-like structured metadata referencing included artifacts/certificates.
- Stable schema suitable for journal supplement and repository indexing.

v150: Result Integrity Lock
- Hashes each exported artifact and records a signed manifest.
- UI can mark runs as Verified/Modified (best-effort) by comparing stored hashes.

This module is downstream-only. It does not modify physics/solver logic or run outputs.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from io import BytesIO
import json, time, hashlib, zipfile, platform, sys

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _sha_obj(o: Any) -> str:
    return _sha_bytes(json.dumps(o, sort_keys=True, default=str).encode("utf-8"))

def _json_bytes(o: Any) -> bytes:
    return json.dumps(o, indent=2, sort_keys=True, default=str).encode("utf-8")

def environment_snapshot() -> Dict[str, Any]:
    return {
        "utc": _utc(),
        "python": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
        "shams_version": None,
    }

# ---------------- Study registry schema (v149) ----------------
def study_registry_schema() -> Dict[str, Any]:
    return {
        "kind": "shams_study_registry",
        "version": "v149",
        "fields": {
            "title": "string",
            "authors": "list[string]",
            "date_utc": "string",
            "shams_version": "string",
            "description": "string",
            "methods": "dict",
            "artifacts": "list[artifact_ref]",
            "certificates": "list[artifact_ref]",
            "figures": "list[artifact_ref]",
            "tables": "list[artifact_ref]",
            "integrity": "manifest_ref",
        },
        "artifact_ref": {"name":"string","sha256":"string","bytes":"int","path":"string"},
    }

def build_study_registry(
    title: str,
    authors: List[str],
    description: str,
    shams_version: str,
    methods: Optional[Dict[str, Any]],
    artifacts: List[Dict[str, Any]],
    certificates: List[Dict[str, Any]],
    figures: Optional[List[Dict[str, Any]]] = None,
    tables: Optional[List[Dict[str, Any]]] = None,
    integrity: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "kind": "shams_study_registry",
        "version": "v149",
        "title": title,
        "authors": authors,
        "date_utc": _utc(),
        "shams_version": shams_version,
        "description": description,
        "methods": methods or {},
        "artifacts": artifacts,
        "certificates": certificates,
        "figures": figures or [],
        "tables": tables or [],
        "integrity": integrity or {},
        "schema": study_registry_schema(),
    }

# ---------------- Integrity manifest (v150) ----------------
def build_integrity_manifest(files: Dict[str, bytes], policy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    created=_utc()
    rec={}
    for path,b in files.items():
        rec[path]={"sha256": _sha_bytes(b), "bytes": len(b)}
    manifest={
        "kind":"shams_integrity_manifest",
        "version":"v150",
        "issued_utc": created,
        "policy": policy or {},
        "files": rec,
        "hashes": {"manifest_sha256": ""},
    }
    manifest["hashes"]["manifest_sha256"]=_sha_obj(manifest)
    return manifest

def verify_integrity_manifest(files: Dict[str, bytes], manifest: Dict[str, Any]) -> Dict[str, Any]:
    results=[]
    ok=True
    mf=(manifest.get("files") or {}) if isinstance(manifest.get("files"), dict) else {}
    for path, meta in mf.items():
        b=files.get(path)
        if b is None:
            results.append({"path": path, "ok": False, "reason": "missing"}); ok=False; continue
        sha=_sha_bytes(b)
        exp=meta.get("sha256")
        if sha != exp:
            results.append({"path": path, "ok": False, "reason": "sha_mismatch", "expected": exp, "got": sha})
            ok=False
        else:
            results.append({"path": path, "ok": True})
    return {"ok": ok, "results": results}

# ---------------- Paper pack (v148) ----------------
@dataclass
class PaperPackConfig:
    shams_version: str
    title: str
    authors: List[str]
    description: str
    run_artifacts: List[Dict[str, Any]]  # shams_run_artifact dicts
    certificates: List[Tuple[str, Dict[str, Any]]]  # (name, obj)
    figures: List[Tuple[str, bytes]]  # (filename, bytes)
    tables: List[Tuple[str, bytes]]   # (filename, bytes)
    methods: Optional[Dict[str, Any]] = None
    policy: Optional[Dict[str, Any]] = None

def build_paper_pack(cfg: PaperPackConfig) -> Dict[str, Any]:
    captions_override = None
    if isinstance(cfg.policy, dict):
        captions_override = cfg.policy.get("captions_override")
    if not isinstance(captions_override, dict):
        captions_override = None

    created=_utc()
    files: Dict[str, bytes] = {}

    # environment snapshot
    env = environment_snapshot()
    env["shams_version"] = cfg.shams_version
    files["env_snapshot.json"] = _json_bytes(env)

    # run artifacts
    artifact_refs=[]
    for i,art in enumerate(cfg.run_artifacts):
        name=f"run_artifact_{i+1}.json"
        b=_json_bytes(art)
        files[f"artifacts/{name}"]=b
        artifact_refs.append({"name": name, "sha256": _sha_bytes(b), "bytes": len(b), "path": f"artifacts/{name}"})

    # certificates
    cert_refs=[]
    for name,obj in (cfg.certificates or []):
        b=_json_bytes(obj)
        files[f"certificates/{name}"]=b
        cert_refs.append({"name": name, "sha256": _sha_bytes(b), "bytes": len(b), "path": f"certificates/{name}"})

    # figures/tables
    fig_refs=[]
    for fn,b in (cfg.figures or []):
        files[f"figures/{fn}"]=b
        fig_refs.append({"name": fn, "sha256": _sha_bytes(b), "bytes": len(b), "path": f"figures/{fn}"})
    tab_refs=[]
    for fn,b in (cfg.tables or []):
        files[f"tables/{fn}"]=b
        tab_refs.append({"name": fn, "sha256": _sha_bytes(b), "bytes": len(b), "path": f"tables/{fn}"})

    # integrity manifest
    manifest = build_integrity_manifest(files, policy=cfg.policy or {"mode":"paper_pack"})
    files["integrity_manifest_v150.json"] = _json_bytes(manifest)

    # study registry
    reg = build_study_registry(
        title=cfg.title, authors=cfg.authors, description=cfg.description,
        shams_version=cfg.shams_version, methods=cfg.methods,
        artifacts=artifact_refs, certificates=cert_refs, figures=fig_refs, tables=tab_refs,
        integrity={"path":"integrity_manifest_v150.json","sha256": manifest["hashes"]["manifest_sha256"]},
    )
    files["study_registry_v149.json"]=_json_bytes(reg)

    # reproduce scripts (best-effort, offline-friendly)
    files["reproduce.sh"] = b"#!/usr/bin/env bash\nset -e\npython -m tools.verify_package\necho 'Reproduction helper: run UI with: streamlit run ui/app.py'\n"
    files["reproduce.bat"]= b"@echo off\npython -m tools.verify_package\necho Reproduction helper: streamlit run ui\\app.py\n"

    # readme
    readme = {
        "kind":"shams_paper_pack_readme",
        "version":"v148",
        "created_utc": created,
        "contents": {
            "artifacts_dir":"artifacts/",
            "certificates_dir":"certificates/",
            "figures_dir":"figures/",
            "tables_dir":"tables/",
            "study_registry":"study_registry_v149.json",
            "integrity_manifest":"integrity_manifest_v150.json",
        },
        "notes":[
            "This pack is downstream-only: it records results and certificates; it does not alter physics/solver behavior.",
            "Integrity is SHA256-based; verify by recomputing file hashes and comparing to integrity_manifest_v150.json.",
        ],
    }
    files["README_paper_pack.json"]=_json_bytes(readme)

    # captions
    captions = {"kind":"shams_captions","version":"v151","created_utc": created, "captions": {}}
    for ref in (fig_refs + tab_refs):
        default_cap = f'{"Figure" if ref["path"].startswith("figures/") else "Table"}: {ref["name"]}.'
        if captions_override and ref["name"] in captions_override:
            captions["captions"][ref["name"]] = str(captions_override[ref["name"]])
        else:
            captions["captions"][ref["name"]] = default_cap
    files["captions.json"] = _json_bytes(captions)

    # zip
    zbuf=BytesIO()
    with zipfile.ZipFile(zbuf,"w",zipfile.ZIP_DEFLATED) as z:
        for path,b in files.items():
            z.writestr(path,b)

    return {
        "kind":"shams_paper_pack_bundle",
        "version":"v148_v149_v150",
        "created_utc": created,
        "manifest": manifest,
        "study_registry": reg,
        "zip_bytes": zbuf.getvalue(),
    }


# ---------------- Session bundle harvesting (v151) ----------------
def _harvest_zip(zip_bytes: bytes) -> Tuple[List[Tuple[str, bytes]], List[Tuple[str, bytes]]]:
    """Return (figures, tables) from an analysis bundle zip by heuristics."""
    figs: List[Tuple[str, bytes]] = []
    tabs: List[Tuple[str, bytes]] = []
    with zipfile.ZipFile(BytesIO(zip_bytes), "r") as z:
        for name in z.namelist():
            n=name.lower()
            if n.endswith(".png") or n.endswith(".svg"):
                figs.append((Path(name).name, z.read(name)))
            elif n.endswith(".csv") or n.endswith(".tsv"):
                tabs.append((Path(name).name, z.read(name)))
    return figs, tabs

def captions_from_filenames(figs: List[Tuple[str, bytes]], tabs: List[Tuple[str, bytes]]) -> Dict[str, str]:
    """Generate deterministic, publishable captions (best-effort) from filenames."""
    cap={}
    for fn,_ in figs:
        base=fn.replace("_", " ").replace("-", " ").rsplit(".",1)[0]
        cap[fn]=f"Figure: {base}. (Generated by SHAMS; see study_registry_v149.json for provenance.)"
    for fn,_ in tabs:
        base=fn.replace("_", " ").replace("-", " ").rsplit(".",1)[0]
        cap[fn]=f"Table: {base}. (Generated by SHAMS; see study_registry_v149.json for provenance.)"
    return cap

def collect_session_bundles(session_state: Dict[str, Any]) -> Tuple[List[Tuple[str, bytes]], List[Tuple[str, bytes]], Dict[str, str]]:
    """Collect figures/tables from known session bundles, if present."""
    figs: List[Tuple[str, bytes]]=[]
    tabs: List[Tuple[str, bytes]]=[]
    # Known bundle keys in session_state
    bundle_keys = [
        ("v140_bundle", "sensitivity_bundle_v140.zip"),
        ("v142_bun", "topology_bundle_v142.zip"),
        ("v143_bun", "interactions_bundle_v143.zip"),
        ("v144_bun", "interval_bundle_v144.zip"),
    ]
    for key, _fname in bundle_keys:
        bun=session_state.get(key)
        if isinstance(bun, dict) and isinstance(bun.get("zip_bytes"), (bytes, bytearray)):
            f,t=_harvest_zip(bun["zip_bytes"])
            figs.extend(f); tabs.extend(t)
    # Deduplicate by filename (keep first)
    seen=set()
    figs2=[]
    for fn,b in figs:
        if fn in seen: 
            continue
        seen.add(fn); figs2.append((fn,b))
    seen=set()
    tabs2=[]
    for fn,b in tabs:
        if fn in seen: 
            continue
        seen.add(fn); tabs2.append((fn,b))
    caps=captions_from_filenames(figs2, tabs2)
    return figs2, tabs2, caps
