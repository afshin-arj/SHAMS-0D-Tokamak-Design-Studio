from __future__ import annotations
"""Design Study Authority Pack (v167)

Goal:
- Produce a single publishable bundle (zip) that contains all audit-grade artifacts for a study:
  protocol (v165), lock + replay (v166), completion pack (v163), sensitivity (v164), and certificate (v160 if present),
  plus the underlying run artifact.
- Works offline: accepts artifacts via file paths OR accepts already-loaded dicts.

Output:
- a zip bytes object and a manifest JSON describing contents and hashes.

Safety:
- Packaging only. No physics/solver changes.
"""

from typing import Any, Dict, Optional, List, Tuple
import json, time, hashlib, io, zipfile

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _canon_json(o: Any) -> bytes:
    return json.dumps(o, indent=2, sort_keys=True, default=str).encode("utf-8")

def _sha_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _as_bytes_json(o: Any) -> bytes:
    return _canon_json(o)

def _maybe(o: Any) -> Optional[Dict[str,Any]]:
    return o if isinstance(o, dict) else None

def build_authority_pack(
    *,
    run_artifact: Optional[Dict[str,Any]] = None,
    study_protocol_v165: Optional[Dict[str,Any]] = None,
    repro_lock_v166: Optional[Dict[str,Any]] = None,
    replay_report_v166: Optional[Dict[str,Any]] = None,
    completion_pack_v163: Optional[Dict[str,Any]] = None,
    sensitivity_v164: Optional[Dict[str,Any]] = None,
    certificate_v160: Optional[Dict[str,Any]] = None,
    policy: Optional[Dict[str,Any]] = None,
) -> Dict[str,Any]:
    policy = policy if isinstance(policy, dict) else {}
    issued=_utc()
    # files mapping (name -> bytes)
    files={}

    def add_json(name: str, obj: Optional[Dict[str,Any]]):
        if isinstance(obj, dict):
            files[name]=_as_bytes_json(obj)

    add_json("run_artifact.json", run_artifact)
    add_json("study_protocol_v165.json", study_protocol_v165)
    add_json("repro_lock_v166.json", repro_lock_v166)
    add_json("replay_report_v166.json", replay_report_v166)
    add_json("completion_pack_v163.json", completion_pack_v163)
    add_json("sensitivity_v164.json", sensitivity_v164)
    add_json("certificate_v160.json", certificate_v160)

    # basic README
    readme = []
    readme.append("# SHAMS Design Study Authority Pack (v167)")
    readme.append("")
    readme.append(f"- Issued: {issued}")
    readme.append(f"- Generator: {policy.get('generator','ui')}")
    readme.append("")
    readme.append("## Contents")
    for k in sorted(files.keys()):
        readme.append(f"- {k}")
    readme.append("")
    readme.append("## Verification")
    readme.append("All JSON files are canonicalized and hashed in manifest.json (SHA-256).")
    readme.append("Replay validity is recorded in replay_report_v166.json.")
    files["README.md"]="\n".join(readme).encode("utf-8")

    # manifest
    manifest={
        "kind":"shams_authority_pack_manifest",
        "version":"v167",
        "issued_utc": issued,
        "generator": policy.get("generator","ui"),
        "files": [],
    }
    for name,b in sorted(files.items()):
        manifest["files"].append({
            "name": name,
            "sha256": _sha_bytes(b),
            "bytes": len(b),
        })
    man_bytes=_as_bytes_json(manifest)
    files["manifest.json"]=man_bytes

    # zip bytes
    bio=io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name,b in files.items():
            z.writestr(name, b)
    zip_bytes=bio.getvalue()
    pack={
        "kind":"shams_authority_pack",
        "version":"v167",
        "issued_utc": issued,
        "integrity": {"zip_sha256": _sha_bytes(zip_bytes)},
        "payload": {
            "manifest": manifest,
            "zip_bytes_b64": None,  # not included to avoid huge JSON; use UI/CLI to write zip
        },
    }
    return {"pack": pack, "zip_bytes": zip_bytes, "manifest": manifest}

