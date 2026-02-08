from __future__ import annotations
"""Run Integrity Lock (v152)

Provides stable hashes for run artifacts and a simple verify mechanism.
Designed to be used from the UI without modifying physics/solver behavior.

Objects:
- shams_run_integrity_lock (v152): stores sha256 of selected objects
"""

from typing import Any, Dict, List, Optional
import json, hashlib, time, uuid

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _json_bytes(o: Any) -> bytes:
    return json.dumps(o, indent=2, sort_keys=True, default=str).encode("utf-8")

def lock_run(
    run_id: str,
    run_artifact: Dict[str, Any],
    extras: Optional[List[Dict[str, Any]]] = None,
    policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not (isinstance(run_artifact, dict) and run_artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("run_artifact kind mismatch")

    files={}
    files["run_artifact.json"] = _json_bytes(run_artifact)
    if extras:
        for i,obj in enumerate(extras):
            files[f"extra_{i+1}.json"]=_json_bytes(obj)

    rec={}
    for name,b in files.items():
        rec[name]={"sha256": _sha_bytes(b), "bytes": len(b)}

    lock={
        "kind":"shams_run_integrity_lock",
        "version":"v152",
        "lock_id": str(uuid.uuid4()),
        "issued_utc": _utc(),
        "run_id": str(run_id),
        "policy": policy or {},
        "files": rec,
        "hashes":{"lock_sha256": ""},
    }
    lock["hashes"]["lock_sha256"]=_sha_bytes(_json_bytes(lock))
    return {"lock": lock, "file_bytes": files}

def verify_run(
    lock: Dict[str, Any],
    run_artifact: Dict[str, Any],
    extras: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if not (isinstance(lock, dict) and lock.get("kind") == "shams_run_integrity_lock"):
        raise ValueError("lock kind mismatch")
    files={}
    files["run_artifact.json"]=_json_bytes(run_artifact)
    if extras:
        for i,obj in enumerate(extras):
            files[f"extra_{i+1}.json"]=_json_bytes(obj)

    results=[]
    ok=True
    expected = lock.get("files") or {}
    if not isinstance(expected, dict):
        expected={}
    for name, meta in expected.items():
        b=files.get(name)
        if b is None:
            ok=False
            results.append({"name": name, "ok": False, "reason":"missing_current"})
            continue
        sha=_sha_bytes(b)
        if sha != meta.get("sha256"):
            ok=False
            results.append({"name": name, "ok": False, "reason":"sha_mismatch", "expected": meta.get("sha256"), "got": sha})
        else:
            results.append({"name": name, "ok": True})
    return {"ok": ok, "results": results}
