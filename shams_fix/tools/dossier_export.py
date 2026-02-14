from __future__ import annotations

"""Design dossier exporter (Paper Mode v2).

Exports a deterministic evidence bundle suitable for reviewer submission.
This is an I/O utility: it does not change physics.

Author: © 2026 Afshin Arjhangmehr
"""

import csv
import io
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import zipfile


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()


def export_design_dossier_zip(
    artifact: Dict[str, Any],
    out_zip_path: Path,
    *,
    basename: str = "design_dossier",
) -> Dict[str, Any]:
    """Write a dossier zip and return a manifest dict."""

    out_zip_path.parent.mkdir(parents=True, exist_ok=True)

    files: List[Dict[str, str]] = []

    def add_bytes(zf: zipfile.ZipFile, name: str, data: bytes) -> None:
        zf.writestr(name, data)
        files.append({"name": name, "sha256": _sha256_bytes(data), "bytes": str(len(data))})

    def add_json(zf: zipfile.ZipFile, name: str, obj: Any) -> None:
        add_bytes(zf, name, _stable_json(obj).encode("utf-8"))

    def add_constraints_csv(zf: zipfile.ZipFile, name: str) -> None:
        cs = artifact.get("constraints")
        if not isinstance(cs, list) or not cs:
            return
        buf = io.StringIO()
        fieldnames = sorted({k for row in cs if isinstance(row, dict) for k in row.keys()})
        w = csv.DictWriter(buf, fieldnames=fieldnames)
        w.writeheader()
        for row in cs:
            if isinstance(row, dict):
                w.writerow(row)
        add_bytes(zf, name, buf.getvalue().encode("utf-8"))

    summary = {
        "software": artifact.get("software"),
        "shams_version": artifact.get("shams_version"),
        "intent": artifact.get("intent"),
        "verdict": artifact.get("verdict"),
        "dominant_mechanism": artifact.get("dominant_mechanism"),
        "worst_margin": artifact.get("worst_hard_margin"),
        "citation_completeness": artifact.get("citation_completeness"),
        "experimental_evidence": artifact.get("experimental_evidence_summary"),
    }

    md_lines = [
        f"# SHAMS Design Dossier",
        f"\n- Software: {summary.get('software')}",
        f"- Version: {summary.get('shams_version')}",
        f"- Intent: {summary.get('intent')}",
        f"- Verdict: {summary.get('verdict')}",
        f"- Dominant mechanism: {summary.get('dominant_mechanism')}",
        f"- Worst hard margin: {summary.get('worst_margin')}",
        "\n## Governance",
        _stable_json({
            "citation_completeness": summary.get("citation_completeness"),
            "experimental_evidence": summary.get("experimental_evidence"),
        }),
    ]

    manifest = {
        "schema": "design_dossier_manifest.v2",
        "basename": basename,
        "files": files,
    }

    with zipfile.ZipFile(out_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        add_json(zf, f"{basename}/dossier.json", artifact)
        add_bytes(zf, f"{basename}/summary.md", "\n".join(md_lines).encode("utf-8"))
        add_constraints_csv(zf, f"{basename}/constraints.csv")
        add_json(zf, f"{basename}/summary.json", summary)
        # write manifest last so it includes prior files
        manifest_bytes = _stable_json({**manifest, "files": files}).encode("utf-8")
        add_bytes(zf, f"{basename}/manifest.json", manifest_bytes)

    return {**manifest, "out_zip": str(out_zip_path)}
