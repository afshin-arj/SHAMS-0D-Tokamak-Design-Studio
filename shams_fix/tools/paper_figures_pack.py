from __future__ import annotations
"""Paper Figures Pack (v93)

Builds a zip of paper-ready figures derived from a run artifact.
Offline-friendly, best-effort.
"""
import io, zipfile, tempfile
from pathlib import Path
from typing import Dict, Any

def build_figures_pack_bytes(artifact: Dict[str, Any]) -> bytes:
    tmpdir = Path(tempfile.mkdtemp(prefix="shams_figpack_"))
    figdir = tmpdir / "figures"
    figdir.mkdir(parents=True, exist_ok=True)

    # Radial build PNG+SVG best-effort
    try:
        from src.shams_io.plotting import plot_radial_build_dual_export
        plot_radial_build_dual_export(artifact, str(figdir / "radial_build"))
    except Exception:
        try:
            from src.shams_io.plotting import plot_radial_build_from_artifact
            plot_radial_build_from_artifact(artifact, str(figdir / "radial_build.png"))
        except Exception:
            pass

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", "SHAMS Paper Figures Pack (v93)\nContains best-effort paper-ready figures (PNG/SVG).\n")
        for p in figdir.glob("*"):
            if p.is_file():
                z.write(str(p), arcname=f"figures/{p.name}")
    return buf.getvalue()
