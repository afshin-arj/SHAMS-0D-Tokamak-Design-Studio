from __future__ import annotations
"""Design Handoff Pack (v116)

Purpose:
- Produce an engineering-ready, publishable handoff bundle from a SHAMS run artifact.
- Additive only; no physics/solver changes.

Bundle contents (handoff_pack.zip):
- evaluated_run_artifact.json  (full provenance)
- design_inputs.yaml           (human-editable inputs)
- constraints_breakdown.csv    (per-constraint pass/margin/magnitude)
- summary.json                 (short summary)
- figures/                     (PNG/SVG if available or generated)
- README.md                    (reproduce instructions)
- manifest.json                (SHA256 hashes + sizes)

Notes:
- If figure exports are not provided, we generate radial build PNG+SVG as a baseline.
"""

from typing import Any, Dict, Optional, Tuple, List
import json
import time
import hashlib
import csv
import io
from io import BytesIO
from pathlib import Path
import zipfile

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def _as_yaml(inputs: Dict[str, Any]) -> str:
    """Minimal YAML writer without external deps."""
    lines: List[str] = []
    lines.append("# SHAMS design inputs (v116)")
    for k in sorted(inputs.keys()):
        v = inputs[k]
        if isinstance(v, (int, float)) or v is None:
            lines.append(f"{k}: {v}")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            s = str(v).replace("\n", " ")
            if any(c in s for c in [":", "#", "{", "}", "[", "]", ","]):
                s = s.replace('"', '\"')
                lines.append(f'{k}: "{s}"')
            else:
                lines.append(f"{k}: {s}")
    lines.append("")
    return "\n".join(lines)

def _constraints_csv(artifact: Dict[str, Any]) -> bytes:
    cons = artifact.get("constraints", [])
    rows: List[Dict[str, Any]] = []
    if isinstance(cons, list):
        for c in cons:
            if not isinstance(c, dict):
                continue
            rows.append({
                "name": c.get("name"),
                "passed": c.get("passed"),
                "margin_frac": c.get("margin_frac"),
                "limit": c.get("limit"),
                "value": c.get("value"),
                "units": c.get("units"),
                "kind": c.get("kind"),
            })
    # fallback from summary only
    if not rows:
        cs = artifact.get("constraints_summary", {})
        if isinstance(cs, dict):
            rows.append({
                "name": cs.get("worst_hard"),
                "passed": cs.get("feasible"),
                "margin_frac": cs.get("worst_hard_margin_frac"),
                "limit": None,
                "value": None,
                "units": None,
                "kind": "summary_only",
            })
    # write csv
    fieldnames = ["name","passed","margin_frac","limit","value","units","kind"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")

def _summary(artifact: Dict[str, Any]) -> Dict[str, Any]:
    cs = artifact.get("constraints_summary", {})
    inp = artifact.get("inputs", {})
    out = {
        "kind":"shams_handoff_summary",
        "created_utc": _created_utc(),
        "artifact_id": artifact.get("id"),
        "feasible": cs.get("feasible") if isinstance(cs, dict) else None,
        "worst_hard": cs.get("worst_hard") if isinstance(cs, dict) else None,
        "worst_hard_margin_frac": cs.get("worst_hard_margin_frac") if isinstance(cs, dict) else None,
        "key_inputs": {k: inp.get(k) for k in ["R0_m","a_m","kappa","Bt_T","Ip_MA","Ti_keV","fG","Paux_MW"] if isinstance(inp, dict)},
    }
    return out

def _readme(artifact: Dict[str, Any]) -> str:
    return """# SHAMS Design Handoff Pack

This package contains a SHAMS-evaluated design point and supporting artifacts for reproducibility.

## Files
- evaluated_run_artifact.json: full run artifact (inputs, outputs, constraints, metadata)
- design_inputs.yaml: human-editable inputs for re-running
- constraints_breakdown.csv: constraint pass/margin summary
- figures/: radial build visuals
- manifest.json: file hashes for integrity

## Reproduce
1) Create an environment and install requirements (see repository README).
2) Run the point evaluation by loading `design_inputs.yaml` into your preferred workflow, or manually paste values into UI.
3) Compare results to `evaluated_run_artifact.json` and `constraints_breakdown.csv`.

## Notes
- SHAMS is authority: this artifact is a validated evaluation result.
"""

def build_handoff_pack(
    *,
    artifact: Dict[str, Any],
    version: str = "v116",
    figures: Optional[Dict[str, bytes]] = None,
) -> Dict[str, Any]:
    if not (isinstance(artifact, dict) and artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("expected shams_run_artifact dict")

    created = _created_utc()
    inputs = artifact.get("inputs", {}) if isinstance(artifact.get("inputs"), dict) else {}
    art_bytes = json.dumps(artifact, indent=2, sort_keys=True).encode("utf-8")
    yaml_str = _as_yaml(inputs)
    yaml_bytes = yaml_str.encode("utf-8")
    csv_bytes = _constraints_csv(artifact)
    summary_bytes = json.dumps(_summary(artifact), indent=2, sort_keys=True).encode("utf-8")
    readme_bytes = _readme(artifact).encode("utf-8")

    fig_map: Dict[str, bytes] = {}
    if isinstance(figures, dict):
        for k,v in figures.items():
            if isinstance(k, str) and isinstance(v, (bytes, bytearray)):
                fig_map[k] = bytes(v)

    # If missing, generate baseline radial build figures
    if not fig_map:
        try:
            from shams_io.plotting import plot_radial_build_dual_export
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                base = Path(td) / "radial_build"
                plot_radial_build_dual_export(artifact, str(base))
                png = base.with_suffix(".png")
                svg = base.with_suffix(".svg")
                if png.exists():
                    fig_map["figures/radial_build.png"] = png.read_bytes()
                if svg.exists():
                    fig_map["figures/radial_build.svg"] = svg.read_bytes()
        except Exception:
            pass

    manifest = {
        "kind": "shams_handoff_pack_manifest",
        "version": version,
        "created_utc": created,
        "source_artifact_id": artifact.get("id"),
        "files": {
            "evaluated_run_artifact.json": {"sha256": _sha256_bytes(art_bytes), "bytes": len(art_bytes)},
            "design_inputs.yaml": {"sha256": _sha256_bytes(yaml_bytes), "bytes": len(yaml_bytes)},
            "constraints_breakdown.csv": {"sha256": _sha256_bytes(csv_bytes), "bytes": len(csv_bytes)},
            "summary.json": {"sha256": _sha256_bytes(summary_bytes), "bytes": len(summary_bytes)},
            "README.md": {"sha256": _sha256_bytes(readme_bytes), "bytes": len(readme_bytes)},
        },
        "notes": [
            "Engineering handoff bundle. Additive export; does not alter physics/solvers.",
        ],
    }
    for fn, fb in fig_map.items():
        manifest["files"][fn] = {"sha256": _sha256_bytes(fb), "bytes": len(fb)}

    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    manifest["files"]["manifest.json"] = {"sha256": _sha256_bytes(manifest_bytes), "bytes": len(manifest_bytes)}

    zbuf = BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("evaluated_run_artifact.json", art_bytes)
        z.writestr("design_inputs.yaml", yaml_bytes)
        z.writestr("constraints_breakdown.csv", csv_bytes)
        z.writestr("summary.json", summary_bytes)
        z.writestr("README.md", readme_bytes)
        for fn, fb in fig_map.items():
            z.writestr(fn, fb)
        z.writestr("manifest.json", manifest_bytes)

    return {
        "kind": "shams_handoff_pack",
        "version": version,
        "created_utc": created,
        "manifest": manifest,
        "zip_bytes": zbuf.getvalue(),
    }
