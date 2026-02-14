from __future__ import annotations
"""Study Matrix + Batch Paper Packs (v127)

Build a deterministic study matrix (cases) from a baseline run artifact and export a
publishable bundle containing per-case paper packs + an index (csv/json/md) + master manifest.

Additive and safe:
- Uses existing point evaluator (hot_ion_point) + constraints + build_run_artifact.
- Uses existing post-processing (mission/explainability/evidence/traceability/study kit/paper pack).
- Does not change physics/solver logic.
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from io import BytesIO, StringIO
import json, time, hashlib, zipfile, csv, copy

from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from constraints.constraints import evaluate_constraints
from shams_io.run_artifact import build_run_artifact

from tools.mission_context import load_mission, apply_mission_overlays
from tools.explainability import build_explainability_report
from tools.evidence_graph import build_evidence_graph, build_traceability_table, traceability_csv
from tools.study_kit import build_study_kit_zip
from tools.study_orchestrator import build_paper_pack_zip

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def evaluate_point_inputs(
    *,
    inputs_dict: Dict[str, Any],
    solver_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate a point and return a run artifact dict."""
    inp = PointInputs.from_dict(inputs_dict)
    out = hot_ion_point(inp)
    cons = evaluate_constraints(out)
    art = build_run_artifact(inp.to_dict(), out, cons)
    # attach minimal solver/meta if provided (additive)
    if isinstance(solver_meta, dict):
        art.setdefault("meta", {})
        if isinstance(art.get("meta"), dict):
            art["meta"].update(solver_meta)
    return art

def build_cases_1d_sweep(
    *,
    baseline_run_artifact: Dict[str, Any],
    lever: str,
    values: List[float],
    missions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    base_inputs = baseline_run_artifact.get("inputs", {}) if isinstance(baseline_run_artifact.get("inputs"), dict) else {}
    missions = missions or [None]  # type: ignore
    cases: List[Dict[str, Any]] = []
    for m in missions:
        for v in values:
            inp = dict(base_inputs)
            inp[lever] = float(v)
            cases.append({
                "case_id": f"{lever}={v:g}" + (f"__{m}" if m else ""),
                "mission": m,
                "inputs_override": {lever: float(v)},
                "inputs": inp,
            })
    return cases

def build_study_matrix_bundle(
    *,
    baseline_run_artifact: Dict[str, Any],
    cases: List[Dict[str, Any]],
    outdir: str = "out_study_matrix_v127",
    version: str = "v127",
    include_explainability: bool = True,
    include_evidence: bool = True,
    include_study_kit: bool = True,
) -> Dict[str, Any]:
    if not (isinstance(baseline_run_artifact, dict) and baseline_run_artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("expected shams_run_artifact baseline")

    outp = Path(outdir)
    outp.mkdir(parents=True, exist_ok=True)
    packs_dir = outp / "paper_packs"
    packs_dir.mkdir(parents=True, exist_ok=True)

    created = _created_utc()
    rows: List[Dict[str, Any]] = []
    files: Dict[str, bytes] = {}

    for i, c in enumerate(cases):
        case_id = str(c.get("case_id") or f"case_{i:03d}")
        mission_name = c.get("mission")
        inputs = c.get("inputs")
        if not isinstance(inputs, dict):
            # derive from baseline + overrides
            base_inputs = baseline_run_artifact.get("inputs", {}) if isinstance(baseline_run_artifact.get("inputs"), dict) else {}
            inputs = dict(base_inputs)
            ov = c.get("inputs_override", {})
            if isinstance(ov, dict):
                inputs.update(ov)

        # Evaluate point (fresh run artifact)
        art = evaluate_point_inputs(inputs_dict=inputs, solver_meta={"label": "study_matrix_v127"})

        # Post-processing
        mission_rep = None
        if mission_name:
            mspec = load_mission(str(mission_name))
            mission_rep = apply_mission_overlays(run_artifact=art, mission=mspec, version="v121")

        expl_rep = None
        if include_explainability:
            expl_rep = build_explainability_report(run_artifact=art, mission_report=mission_rep, tolerance_envelope_report=None, version="v122")

        graph = None
        tab = None
        tcsv = None
        if include_evidence:
            graph = build_evidence_graph(run_artifact=art, mission_report=mission_rep, tolerance_envelope_report=None, explainability_report=expl_rep, version="v123")
            tab = build_traceability_table(run_artifact=art, mission_report=mission_rep, tolerance_envelope_report=None, explainability_report=expl_rep, version="v123")
            tcsv = traceability_csv(tab)

        kit_zip = None
        if include_study_kit:
            kit = build_study_kit_zip(
                run_artifact=art,
                mission_report=mission_rep,
                tolerance_envelope_report=None,
                explainability_report=expl_rep,
                evidence_graph=graph,
                traceability_table=tab,
                authority_pack_zip=None,
                optimizer_downstream_bundle_zip=None,
                decision_pack_zip=None,
                version="v123B",
            )
            kit_zip = kit.get("zip_bytes")

        pack = build_paper_pack_zip(
            baseline_run_artifact=art,
            mission_report=mission_rep,
            explainability_report=expl_rep,
            evidence_graph=graph,
            traceability_table=tab,
            traceability_csv=tcsv,
            feasibility_atlas_meta=None,
            atlas_bundle_zip=None,
            study_kit_zip=kit_zip,
            version="v125",
        )

        pack_bytes = pack["zip_bytes"]
        rel_pack_path = f"paper_packs/{case_id}/paper_pack.zip"
        files[rel_pack_path] = pack_bytes

        # Save row
        cs = art.get("constraints_summary", {}) if isinstance(art.get("constraints_summary"), dict) else {}
        outs = art.get("outputs", {}) if isinstance(art.get("outputs"), dict) else {}
        rows.append({
            "case_id": case_id,
            "mission": mission_name or "",
            "feasible": cs.get("feasible"),
            "worst_hard": cs.get("worst_hard"),
            "worst_hard_margin_frac": cs.get("worst_hard_margin_frac"),
            "Bt_T": inputs.get("Bt_T"),
            "R0_m": inputs.get("R0_m"),
            "a_m": inputs.get("a_m"),
            "Ip_MA": inputs.get("Ip_MA"),
            "Q": outs.get("Q"),
            "Pfus_MW": outs.get("Pfus_MW"),
            "Pnet_MW": outs.get("Pnet_MW"),
            "pack_path": rel_pack_path,
        })

    # Index CSV/JSON/MD
    index_csv_buf = StringIO()
    fieldnames = list(rows[0].keys()) if rows else ["case_id","mission","feasible","pack_path"]
    w = csv.DictWriter(index_csv_buf, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k) for k in fieldnames})
    index_csv = index_csv_buf.getvalue().encode("utf-8")
    files["study_index.csv"] = index_csv
    files["study_index.json"] = json.dumps({"kind":"shams_study_index","version":version,"created_utc":created,"rows":rows}, indent=2, sort_keys=True).encode("utf-8")

    # Summary MD
    ok = sum(1 for r in rows if r.get("feasible") is True)
    md = []
    md.append("# Study Summary (v127)\n")
    md.append(f"Generated UTC: {created}\n")
    md.append(f"Cases: {len(rows)} (feasible: {ok})\n")
    md.append("## Index\n- study_index.csv\n- study_index.json\n")
    md.append("## Per-case packs\nEach case has `paper_pack.zip` under `paper_packs/<case_id>/`.\n")
    files["study_summary.md"] = ("\n".join(md) + "\n").encode("utf-8")

    # Master manifest
    manifest = {
        "kind":"shams_study_matrix_manifest",
        "version": version,
        "created_utc": created,
        "files": {k: {"sha256": _sha256(v), "bytes": len(v)} for k,v in files.items()},
    }
    files["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    zbuf = BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k, v)

    return {"kind":"shams_study_matrix_bundle", "version": version, "created_utc": created, "cases": len(rows), "manifest": manifest, "zip_bytes": zbuf.getvalue()}
