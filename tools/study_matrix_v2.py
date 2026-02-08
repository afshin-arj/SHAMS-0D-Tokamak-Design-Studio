from __future__ import annotations
"""Study Matrix Builder v2 (v132)

Adds:
- 2D/3D multi-lever sweep case generation
- Derived columns computed from per-case run artifacts (safe, post-process)
- Exports a study bundle compatible with v127/v128/v129 consumers (same layout)

Uses same pipeline as v127 (evaluate_point_inputs + paper pack).
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import json, math, time, hashlib, zipfile, csv
from io import BytesIO, StringIO

from tools.study_matrix import evaluate_point_inputs
from tools.mission_context import load_mission, apply_mission_overlays
from tools.explainability import build_explainability_report
from tools.evidence_graph import build_evidence_graph, build_traceability_table, traceability_csv
from tools.study_kit import build_study_kit_zip
from tools.study_orchestrator import build_paper_pack_zip

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def linspace(a: float, b: float, n: int) -> List[float]:
    if n <= 1:
        return [float(a)]
    return [float(a) + (float(b)-float(a))*i/(n-1) for i in range(n)]

def build_cases_multi_sweep(
    *,
    baseline_run_artifact: Dict[str, Any],
    sweeps: List[Dict[str, Any]],
    missions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """sweeps: [{lever, min, max, n}]"""
    base_inputs = baseline_run_artifact.get("inputs", {}) if isinstance(baseline_run_artifact.get("inputs"), dict) else {}
    missions = missions or [None]  # type: ignore

    levers=[]
    grids=[]
    for s in sweeps:
        lever=str(s.get("lever"))
        n=int(s.get("n", 5))
        vmin=float(s.get("min"))
        vmax=float(s.get("max"))
        levers.append(lever)
        grids.append(linspace(vmin, vmax, n))

    cases=[]
    for m in missions:
        for vals in _product(*grids):
            inp=dict(base_inputs)
            ov={}
            parts=[]
            for lever,v in zip(levers, vals):
                ov[lever]=float(v)
                inp[lever]=float(v)
                parts.append(f"{lever}={v:g}")
            cid="__".join(parts) + (f"__{m}" if m else "")
            cases.append({"case_id": cid, "mission": m, "inputs_override": ov, "inputs": inp})
    return cases

def _product(*args):
    if not args:
        yield tuple()
        return
    import itertools
    for t in itertools.product(*args):
        yield t

def build_study_matrix_bundle_v2(
    *,
    baseline_run_artifact: Dict[str, Any],
    cases: List[Dict[str, Any]],
    outdir: str = "out_study_matrix_v132",
    version: str = "v132",
    include_explainability: bool = True,
    include_evidence: bool = True,
    include_study_kit: bool = True,
    derived: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Derived: list of derived columns to compute: 'Pnet_per_R0', 'Q_per_Bt', 'margin_penalty'"""
    if not (isinstance(baseline_run_artifact, dict) and baseline_run_artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("expected shams_run_artifact baseline")
    derived = derived or []

    outp = Path(outdir)
    outp.mkdir(parents=True, exist_ok=True)
    created = _created_utc()

    files: Dict[str, bytes] = {}
    rows: List[Dict[str, Any]] = []

    for i, c in enumerate(cases):
        case_id = str(c.get("case_id") or f"case_{i:03d}")
        mission_name = c.get("mission")
        inputs = c.get("inputs")
        if not isinstance(inputs, dict):
            inputs = dict(baseline_run_artifact.get("inputs", {}) or {})
            ov = c.get("inputs_override", {})
            if isinstance(ov, dict):
                inputs.update(ov)

        art = evaluate_point_inputs(inputs_dict=inputs, solver_meta={"label": "study_matrix_v132"})

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
        rel_pack_path = f"paper_packs/{case_id}/paper_pack.zip"
        files[rel_pack_path] = pack["zip_bytes"]

        cs = art.get("constraints_summary", {}) if isinstance(art.get("constraints_summary"), dict) else {}
        outs = art.get("outputs", {}) if isinstance(art.get("outputs"), dict) else {}

        row = {
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
        }

        # derived metrics (safe)
        if "Pnet_per_R0" in derived:
            try:
                if outs.get("Pnet_MW") is not None and inputs.get("R0_m") not in (None,0):
                    row["Pnet_per_R0"] = float(outs["Pnet_MW"]) / float(inputs["R0_m"])
            except Exception:
                row["Pnet_per_R0"] = None
        if "Q_per_Bt" in derived:
            try:
                if outs.get("Q") is not None and inputs.get("Bt_T") not in (None,0):
                    row["Q_per_Bt"] = float(outs["Q"]) / float(inputs["Bt_T"])
            except Exception:
                row["Q_per_Bt"] = None
        if "margin_penalty" in derived:
            try:
                m = cs.get("worst_hard_margin_frac")
                row["margin_penalty"] = (0.0 if m is None else float(m))
            except Exception:
                row["margin_penalty"] = None

        rows.append(row)

    # index csv/json/md
    index_csv_buf = StringIO()
    fieldnames = list(rows[0].keys()) if rows else ["case_id","mission","feasible","pack_path"]
    w = csv.DictWriter(index_csv_buf, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k) for k in fieldnames})
    files["study_index.csv"] = index_csv_buf.getvalue().encode("utf-8")
    files["study_index.json"] = json.dumps({"kind":"shams_study_index","version":version,"created_utc":created,"rows":rows}, indent=2, sort_keys=True).encode("utf-8")

    ok = sum(1 for r in rows if r.get("feasible") is True)
    files["study_summary.md"] = (f"# Study Summary ({version})\n\nGenerated UTC: {created}\n\nCases: {len(rows)} (feasible: {ok})\n\n").encode("utf-8")

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
