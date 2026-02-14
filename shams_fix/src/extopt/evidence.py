from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from tools.dossier_export import export_design_dossier_zip


def export_evidence_pack(artifact: Dict[str, Any], out_dir: Path, *, basename: str) -> Dict[str, Any]:
    """Export a deterministic evidence pack (zip) for a candidate.

    This is an I/O-only helper; it does not modify physics outputs.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_zip = out_dir / f"{basename}.zip"
    return export_design_dossier_zip(artifact, out_zip, basename=basename)
