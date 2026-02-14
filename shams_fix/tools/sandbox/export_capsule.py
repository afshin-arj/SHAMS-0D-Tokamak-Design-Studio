from __future__ import annotations
from typing import Any, Dict, Optional
from pathlib import Path
import io, json, zipfile, hashlib, time

def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def export_run_capsule_zip(
    *,
    capsule: Dict[str, Any],
    archive: Dict[str, Any],
    resistance_report: Optional[Dict[str, Any]] = None,
    out_path: Path,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    files = {}
    files["run_capsule.json"] = json.dumps(capsule, indent=2, sort_keys=True).encode("utf-8")
    files["archive.json"] = json.dumps(archive, indent=2, sort_keys=True).encode("utf-8")
    if resistance_report is not None:
        files["resistance_report.json"] = json.dumps(resistance_report, indent=2, sort_keys=True).encode("utf-8")

    manifest = {
        "schema": "shams.opt_sandbox.capsule_zip_manifest.v1",
        "created_ts": int(time.time()),
        "files": {name: {"sha256": _sha256_bytes(data), "bytes": len(data)} for name, data in files.items()},
    }
    files["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return out_path


def import_run_capsule_zip(in_path: Path) -> Dict[str, Any]:
    """Import a capsule zip created by :func:`export_run_capsule_zip`.

    Returns a dict with keys: capsule, archive, resistance_report (optional), manifest.
    """
    in_path = Path(in_path)
    out: Dict[str, Any] = {}
    with zipfile.ZipFile(in_path, "r") as z:
        names = set(z.namelist())
        def _read_json(name: str) -> Optional[Dict[str, Any]]:
            if name not in names:
                return None
            try:
                return json.loads(z.read(name).decode("utf-8"))
            except Exception:
                return None
        out["capsule"] = _read_json("run_capsule.json")
        out["archive"] = _read_json("archive.json")
        out["resistance_report"] = _read_json("resistance_report.json")
        out["manifest"] = _read_json("manifest.json")
    return out
