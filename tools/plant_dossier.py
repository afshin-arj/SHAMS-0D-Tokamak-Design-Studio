from __future__ import annotations
from typing import Dict, Any
from pathlib import Path
import json, zipfile, hashlib

from src.plant.accounting import compute_plant_ledger, ledger_to_json

def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def build_plant_dossier(artifact: Dict[str, Any]) -> Dict[str, Any]:
    ledger = compute_plant_ledger(artifact)
    return {
        "schema_version": "plant.dossier.v1",
        "physics_registry_hash": artifact.get("physics_registry_hash", ""),
        "artifact_id": artifact.get("id", ""),
        "verdict": artifact.get("verdict", ""),
        "dominant_mechanism": artifact.get("dominant_mechanism", ""),
        "plant_ledger": ledger_to_json(ledger),
    }

def export_plant_dossier_zip(artifact: Dict[str, Any], out_zip: Path) -> Path:
    dossier = build_plant_dossier(artifact)
    art_bytes = json.dumps(artifact, sort_keys=True, indent=2).encode("utf-8")
    dos_bytes = json.dumps(dossier, sort_keys=True, indent=2).encode("utf-8")
    manifest = {
        "schema_version": "plant.dossier_zip_manifest.v1",
        "members": {
            "artifact.json": {"sha256": _sha256_bytes(art_bytes), "bytes": len(art_bytes)},
            "plant_dossier.json": {"sha256": _sha256_bytes(dos_bytes), "bytes": len(dos_bytes)},
        }
    }
    man_bytes = json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8")

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(zipfile.ZipInfo("artifact.json", date_time=(1980,1,1,0,0,0)), art_bytes)
        zf.writestr(zipfile.ZipInfo("plant_dossier.json", date_time=(1980,1,1,0,0,0)), dos_bytes)
        zf.writestr(zipfile.ZipInfo("manifest.json", date_time=(1980,1,1,0,0,0)), man_bytes)
    return out_zip
