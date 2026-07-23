"""Control Room Artifacts helpers — Phase 18."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from ui_nicegui.bootstrap import repo_root
from ui_nicegui.lib.cr_provenance_helpers import list_session_run_artifacts


def repo() -> Path:
    return Path(repo_root())


def collect_session_artifacts(session) -> List[Dict[str, Any]]:
    return list_session_run_artifacts(session)


def list_ui_run_dirs(*, limit: int = 40) -> List[Path]:
    root = repo() / "ui_runs"
    if not root.is_dir():
        return []
    dirs = [p for p in root.iterdir() if p.is_dir()]
    return sorted(dirs, key=lambda p: p.stat().st_mtime, reverse=True)[:limit]


def list_run_json_files(run_dir: Path) -> List[Path]:
    if not run_dir.is_dir():
        return []
    return sorted(run_dir.glob("*.json"))


def load_json_path(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_bytes(data: bytes) -> dict:
    obj = json.loads(data.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Expected JSON object")
    return obj


def artifact_summary(art: dict) -> Dict[str, Any]:
    meta = art.get("meta") or {}
    prov = art.get("provenance") or {}
    ledger = art.get("constraint_ledger") or {}
    atlas = art.get("no_solution_atlas") if isinstance(art.get("no_solution_atlas"), dict) else {}
    return {
        "schema": art.get("schema_version") or art.get("kind"),
        "label": meta.get("label") or art.get("run_id") or art.get("id"),
        "mode": meta.get("mode"),
        "git_commit": prov.get("git_commit"),
        "ledger_entries": len(ledger.get("entries") or []) if isinstance(ledger, dict) else 0,
        "has_model_set": bool(art.get("model_set")),
        "has_no_solution_atlas": bool(atlas.get("schema") == "no_solution_atlas.v1"),
        "atlas_verdict": atlas.get("verdict"),
        "atlas_dominant_mechanism": atlas.get("dominant_mechanism"),
    }


def ledger_rows(art: dict) -> List[dict]:
    ledger = art.get("constraint_ledger") or {}
    entries = ledger.get("entries") if isinstance(ledger, dict) else None
    if not isinstance(entries, list):
        cons = art.get("constraints")
        if isinstance(cons, list):
            return [c for c in cons if isinstance(c, dict)]
        return []
    return [e for e in entries if isinstance(e, dict)]


def export_artifact_bundle(art: dict) -> bytes:
    import io
    import zipfile

    payload = json.dumps(watermark_run_artifact_export(art), indent=2, sort_keys=True, default=str).encode(
        "utf-8"
    )
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("shams_run_artifact.json", payload)
        summary = artifact_summary(art)
        z.writestr("ARTIFACT_SUMMARY.json", json.dumps(summary, indent=2, sort_keys=True))
        atlas = art.get("no_solution_atlas")
        if isinstance(atlas, dict) and atlas.get("schema") == "no_solution_atlas.v1":
            z.writestr(
                "no_solution_atlas.json",
                json.dumps(atlas, indent=2, sort_keys=True, default=str).encode("utf-8"),
            )
    return bio.getvalue()


def watermark_run_artifact_export(art: Mapping[str, Any]) -> Dict[str, Any]:
    """PHYS-KPI-001: download copy with claim KPIs watermarked on INFEASIBLE artifacts."""
    from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_claim_kpi_map
    from ui_nicegui.lib.verdict_core import verdict_summary

    out: Dict[str, Any] = dict(art) if isinstance(art, Mapping) else {}
    outs = out.get("outputs") if isinstance(out.get("outputs"), Mapping) else {}
    vs = verdict_summary(dict(outs)) if outs else {}
    feasible = bool(vs.get("feasible")) if vs.get("loaded") else str(out.get("verdict") or "").upper() in (
        "FEASIBLE",
        "PASS",
        "VERIFIED",
        "OK",
    )
    if outs and not feasible:
        out["outputs"] = watermark_claim_kpi_map(outs, feasible=False, point_out=outs)
        kpis = out.get("kpis")
        if isinstance(kpis, Mapping):
            out["kpis"] = watermark_claim_kpi_map(kpis, feasible=False, point_out=outs)
        out["phys_kpi_note"] = (
            "PHYS-KPI-001: claim KPIs on INFEASIBLE artifacts are — (diagnostic) — not design claims."
        )
    return out
