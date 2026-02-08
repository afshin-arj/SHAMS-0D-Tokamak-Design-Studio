from __future__ import annotations
"""Multi-Study Comparison Pack (v155)

Given multiple paper packs (paper_pack_v150.zip) or study registries, build a
comparison bundle that:
- collects registries
- extracts key metrics summaries (best-effort)
- creates an aggregate integrity manifest over included packs

This is downstream-only. It does not modify run artifacts.
"""

from typing import Any, Dict, List, Tuple, Optional
from pathlib import Path
from io import BytesIO
import json, zipfile, time, hashlib

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _json_bytes(o: Any) -> bytes:
    return json.dumps(o, indent=2, sort_keys=True, default=str).encode("utf-8")

def _read_pack_registry(pack_bytes: bytes) -> Dict[str, Any]:
    with zipfile.ZipFile(BytesIO(pack_bytes), "r") as z:
        try:
            b=z.read("study_registry_v149.json")
            return json.loads(b.decode("utf-8"))
        except Exception:
            return {}

def _extract_key_metrics(reg: Dict[str, Any]) -> Dict[str, Any]:
    # Best-effort: pull the first artifact ref and include title, version, and counts
    return {
        "title": reg.get("title"),
        "shams_version": reg.get("shams_version"),
        "date_utc": reg.get("date_utc"),
        "n_artifacts": len(reg.get("artifacts") or []) if isinstance(reg.get("artifacts"), list) else 0,
        "n_certificates": len(reg.get("certificates") or []) if isinstance(reg.get("certificates"), list) else 0,
        "n_figures": len(reg.get("figures") or []) if isinstance(reg.get("figures"), list) else 0,
        "n_tables": len(reg.get("tables") or []) if isinstance(reg.get("tables"), list) else 0,
    }

def build_multi_study_pack(paper_packs: List[Tuple[str, bytes]], policy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    created=_utc()
    files: Dict[str, bytes] = {}
    registry_refs=[]
    metrics=[]
    for name,b in paper_packs:
        files[f"packs/{name}"]=b
        reg=_read_pack_registry(b)
        files[f"registries/{Path(name).stem}_study_registry_v149.json"]=_json_bytes(reg)
        registry_refs.append({"name": name, "sha256": _sha_bytes(b), "bytes": len(b), "path": f"packs/{name}"})
        metrics.append(_extract_key_metrics(reg))

    # integrity
    rec={}
    for path,b in files.items():
        rec[path]={"sha256": _sha_bytes(b), "bytes": len(b)}
    manifest={
        "kind":"shams_integrity_manifest_multi",
        "version":"v155",
        "issued_utc": created,
        "policy": policy or {},
        "files": rec,
        "hashes": {"manifest_sha256": ""},
    }
    manifest["hashes"]["manifest_sha256"]=_sha_bytes(_json_bytes(manifest))

    report={
        "kind":"shams_multi_study_comparison",
        "version":"v155",
        "created_utc": created,
        "policy": policy or {},
        "packs": registry_refs,
        "metrics": metrics,
        "integrity": {"path":"integrity_manifest_multi_v155.json","sha256": manifest["hashes"]["manifest_sha256"]},
    }
    files["comparison_report_v155.json"]=_json_bytes(report)
    files["integrity_manifest_multi_v155.json"]=_json_bytes(manifest)

    zbuf=BytesIO()
    with zipfile.ZipFile(zbuf,"w",zipfile.ZIP_DEFLATED) as z:
        for path,b in files.items():
            z.writestr(path,b)

    return {"bundle": report, "manifest": manifest, "zip_bytes": zbuf.getvalue()}
