from __future__ import annotations
"""Audit Pack exporter (v103 consolidated).

Creates a single zip suitable for journal/regulator appendices:
- artifact(s)
- schemas used
- manifests (sha256)
- environment snapshot (python/platform + optional pip freeze)
- solver/telemetry blocks if present in artifacts

This is additive: does not modify physics or solver behavior.
"""

import io, json, zipfile, hashlib, sys, platform, subprocess, time
from pathlib import Path
from typing import Any, Dict, List, Optional

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def _safe_pip_freeze() -> str:
    try:
        p = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=False)
        if p.returncode == 0 and p.stdout:
            return p.stdout
    except Exception:
        pass
    return ""

def build_audit_pack_zip(
    *,
    version: str,
    artifacts: List[Dict[str, Any]],
    schema_dir: str = "schemas",
    include_pip_freeze: bool = True,
    extra_notes: str = "",
) -> bytes:
    buf = io.BytesIO()
    created_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    env = {
        "python": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
    }
    if include_pip_freeze:
        pf = _safe_pip_freeze()
        if pf:
            env["pip_freeze"] = pf

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # write artifacts
        for i, a in enumerate(artifacts or []):
            z.writestr(f"artifacts/artifact_{i+1}.json", json.dumps(a, indent=2, sort_keys=True))

        # schemas (best-effort)
        sd = Path(schema_dir)
        if sd.exists() and sd.is_dir():
            for p in sd.glob("*.json"):
                try:
                    z.write(p, arcname=f"schemas/{p.name}")
                except Exception:
                    pass

        # environment snapshot
        z.writestr("environment.json", json.dumps(env, indent=2, sort_keys=True))

        # manifest (hashes of in-zip json payloads we generated)
        # For files written with writestr, we can hash bytes directly by re-encoding.
        manifest = {
            "kind": "shams_audit_pack_manifest",
            "version": version,
            "created_utc": created_utc,
            "files": {},
            "notes": extra_notes,
        }
        # We don't have direct access to stored bytes, so re-hash canonical bytes for the generated json we know.
        for i, a in enumerate(artifacts or []):
            b = json.dumps(a, indent=2, sort_keys=True).encode("utf-8")
            manifest["files"][f"artifacts/artifact_{i+1}.json"] = {"sha256": _sha256_bytes(b), "bytes": len(b)}
        env_b = json.dumps(env, indent=2, sort_keys=True).encode("utf-8")
        manifest["files"]["environment.json"] = {"sha256": _sha256_bytes(env_b), "bytes": len(env_b)}

        z.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        z.writestr("README.txt", "SHAMS Audit Pack (v103)\nContains artifacts + schemas + environment + manifest.\n")
    return buf.getvalue()
