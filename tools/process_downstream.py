from __future__ import annotations
"""PROCESS Downstream Interoperability (v108)

Goal: make PROCESS a downstream consumer by exporting SHAMS results into a
PROCESS-like tabular summary + bundle.

This is NOT code reuse from PROCESS. It's an interoperability export format.
Additive only.
"""

from typing import Any, Dict, List, Optional
import csv
import json
import time
import zipfile
from io import BytesIO

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256_bytes(b: bytes) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def _get(d: Dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if isinstance(d, dict) and k in d:
            return d.get(k)
    return None

def _collect_row(artifact: Dict[str, Any]) -> Dict[str, Any]:
    inputs = artifact.get("inputs", {}) if isinstance(artifact.get("inputs"), dict) else {}
    outputs = artifact.get("outputs", {}) if isinstance(artifact.get("outputs"), dict) else {}
    cs = artifact.get("constraints_summary", {}) if isinstance(artifact.get("constraints_summary"), dict) else {}
    # PROCESS-ish core columns (minimal and stable)
    row = {
        "id": artifact.get("id"),
        "feasible": bool(cs.get("feasible")) if "feasible" in cs else None,
        "worst_hard": cs.get("worst_hard"),
        "worst_hard_margin_frac": cs.get("worst_hard_margin_frac"),
        # geometry / plasma current / field
        "R0_m": _get(outputs, "R0_m", "R0"),
        "a_m": _get(outputs, "a_m", "a"),
        "kappa": _get(inputs, "kappa"),
        "Bt_T": _get(inputs, "Bt_T"),
        "Ip_MA": _get(outputs, "Ip_MA", "Ip"),
        "q95_proxy": _get(outputs, "q95_proxy", "q95"),
        # power / performance (best-effort)
        "Pfus_total_MW": _get(outputs, "Pfus_total_MW"),
        "Pfus_DT_MW": _get(outputs, "Pfus_DT_MW"),
        "P_net_min_MW": _get(outputs, "P_net_min_MW"),
        "q_div_MW_m2": _get(outputs, "q_div_MW_m2"),
    }
    return row

def build_process_downstream_bundle(
    payloads: List[Dict[str, Any]],
    *,
    version: str = "v108",
    source_run_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a zip bundle with a PROCESS-like CSV + JSON manifest."""
    created = _created_utc()
    source_run_ids = source_run_ids or []

    run_artifacts = [p for p in (payloads or []) if isinstance(p, dict) and p.get("kind") == "shams_run_artifact"]
    rows = [_collect_row(a) for a in run_artifacts]

    # CSV bytes
    fieldnames = sorted({k for r in rows for k in r.keys()}) if rows else ["id"]
    import io
    sbuf = io.StringIO()
    w = csv.DictWriter(sbuf, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    csv_bytes = sbuf.getvalue().encode("utf-8")

    summary = {
        "kind": "shams_process_downstream_summary",
        "created_utc": created,
        "version": version,
        "n_run_artifacts": len(run_artifacts),
        "source_run_ids": source_run_ids,
        "columns": fieldnames,
    }
    summary_bytes = json.dumps(summary, indent=2, sort_keys=True).encode("utf-8")

    md = []
    md.append("# SHAMS → PROCESS Downstream Export")
    md.append("")
    md.append(f"- Created (UTC): {created}")
    md.append(f"- Version: {version}")
    md.append(f"- Run artifacts exported: {len(run_artifacts)}")
    md.append("")
    md.append("## Files")
    md.append("")
    md.append("- `process_compat_table.csv` — PROCESS-like tabular summary from SHAMS artifacts")
    md.append("- `process_downstream_summary.json` — metadata manifest")
    md.append("")
    md.append("## Notes")
    md.append("")
    md.append("- This is an interoperability export only; no PROCESS code or models are reused.")
    md.append("- Column set is intentionally minimal and stable; additional columns can be added additively.")
    md_bytes = ("\n".join(md) + "\n").encode("utf-8")

    files = {
        "process_compat_table.csv": csv_bytes,
        "process_downstream_summary.json": summary_bytes,
        "PROCESS_DOWNSTREAM_README.md": md_bytes,
    }

    zbuf = BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    zip_bytes = zbuf.getvalue()

    return {
        "kind": "shams_process_downstream_bundle",
        "created_utc": created,
        "version": version,
        "summary": summary,
        "files": {k: {"bytes": len(v), "sha256": _sha256_bytes(v)} for k, v in files.items()},
        "zip_bytes": zip_bytes,
        "zip_sha256": _sha256_bytes(zip_bytes),
    }
