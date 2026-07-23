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
    # Honor explicit infeasibility stamps (sparse fixtures / export nests may not
    # rebuild a full constraint ledger via verdict_summary).
    if outs.get("hard_feasible") is False or outs.get("feasible") is False:
        feasible = False
    if out.get("feasible") is False or out.get("governance_feasible") is False:
        feasible = False
    verdict_u = str(out.get("verdict") or outs.get("verdict") or "").strip().upper()
    if verdict_u in ("INFEASIBLE", "FAIL", "NO-SOLUTION", "NO_SOLUTION", "REJECTED"):
        feasible = False
    failed = outs.get("constraints_failed") or outs.get("failed_hard") or outs.get("failed_blocking")
    if isinstance(failed, (list, tuple)) and len(failed) > 0:
        feasible = False
    if outs and not feasible:
        out["outputs"] = watermark_claim_kpi_map(outs, feasible=False, point_out=outs)
        kpis = out.get("kpis")
        if isinstance(kpis, Mapping):
            out["kpis"] = watermark_claim_kpi_map(kpis, feasible=False, point_out=outs)
        # Mirror case_deck_panel: watermark tables.v1 plasma / power_balance claim cells.
        tables = out.get("tables")
        if isinstance(tables, Mapping):
            t2 = dict(tables)
            v1 = tables.get("v1") or tables
            if isinstance(v1, Mapping):
                v1d = dict(v1)
                for section in ("plasma", "power_balance"):
                    block = v1.get(section)
                    if isinstance(block, Mapping):
                        v1d[section] = watermark_claim_kpi_map(
                            block, feasible=False, point_out=outs
                        )
                if "v1" in tables:
                    t2["v1"] = v1d
                else:
                    t2.update(v1d)
            out["tables"] = t2
        out["phys_kpi_note"] = (
            "PHYS-KPI-001: claim KPIs on INFEASIBLE artifacts are — (diagnostic) — not design claims."
        )
    # Nested scenario_delta can still carry raw changed_kpis claim FoMs.
    sd = out.get("scenario_delta")
    if isinstance(sd, Mapping):
        from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_scenario_delta_export
        from ui_nicegui.lib.verdict_core import verdict_summary as _vs

        base_outs = sd.get("baseline_outputs") if isinstance(sd.get("baseline_outputs"), Mapping) else {}
        scen_outs = sd.get("scenario_outputs") if isinstance(sd.get("scenario_outputs"), Mapping) else {}
        vs_base = _vs(dict(base_outs)) if base_outs else {}
        vs_scen = _vs(dict(scen_outs)) if scen_outs else {}
        feas_base = bool(vs_base.get("feasible")) if vs_base.get("loaded") else feasible
        feas_scen = bool(vs_scen.get("feasible")) if vs_scen.get("loaded") else feasible
        # Sparse nests often lack a constraint ledger; verdict_summary can spuriously
        # report FEASIBLE from Q alone. Under an INFEASIBLE parent, stamp both sides
        # unless the nest explicitly asserts hard feasibility.
        if not feasible:
            if not (
                isinstance(base_outs, Mapping)
                and (base_outs.get("hard_feasible") is True or base_outs.get("feasible") is True)
            ):
                feas_base = False
            if not (
                isinstance(scen_outs, Mapping)
                and (scen_outs.get("hard_feasible") is True or scen_outs.get("feasible") is True)
            ):
                feas_scen = False
        out["scenario_delta"] = watermark_scenario_delta_export(
            sd, feasible_base=feas_base, feasible_scenario=feas_scen
        )
    return out
