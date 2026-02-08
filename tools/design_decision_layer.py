from __future__ import annotations
"""Design Decision Layer (v113)

Goal:
- Convert SHAMS exploration outputs (v110 boundary atlas, v111 design family, v109 dominance) into
  *defensible candidate objects* + comparison tables + an exportable decision pack.
- Additive only: operates on existing payloads; does not change physics or solvers.

Key outputs:
- shams_design_candidate objects:
  - inputs
  - component_index (best-effort)
  - robustness metrics:
      * feasible_fraction in local family
      * worst constraint distribution
      * boundary distance estimates (2D lever-pair plane; best-effort)
  - causality:
      * dominant constraints (component-level, if available)
      * top failure modes near component (if available)
  - literature context:
      * whether overlay contains this lever pair, and nearest distance (best-effort)

- design_decision_pack.zip:
  - candidates.json
  - comparison_table.csv
  - DESIGN_DECISION_REPORT.md
  - manifest.json (hashes, versions)
"""

from typing import Any, Dict, List, Optional, Tuple
import time
import math
import json
import hashlib
import csv
import io

from tools.literature_overlay import extract_xy_points


def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _artifact_feasible(a: Dict[str, Any]) -> Optional[bool]:
    cs = a.get("constraints_summary")
    if isinstance(cs, dict) and "feasible" in cs:
        return bool(cs.get("feasible"))
    cons = a.get("constraints", [])
    if isinstance(cons, list) and cons:
        return not any(isinstance(c, dict) and c.get("passed") is False for c in cons)
    return None


def _worst_hard(a: Dict[str, Any]) -> Tuple[Optional[str], Optional[float]]:
    cs = a.get("constraints_summary")
    if isinstance(cs, dict):
        return cs.get("worst_hard"), cs.get("worst_hard_margin_frac")
    # fallback from constraints list
    cons = a.get("constraints", [])
    worst_name = None
    worst_mf = None
    if isinstance(cons, list):
        for c in cons:
            if not isinstance(c, dict):
                continue
            mf = c.get("margin_frac")
            if _is_num(mf):
                mf = float(mf)
                if (worst_mf is None) or (mf < worst_mf):
                    worst_mf = mf
                    worst_name = c.get("name")
    return worst_name, worst_mf


def _lookup_component_info(component_report: Optional[Dict[str, Any]], component_index: Optional[int]) -> Dict[str, Any]:
    if not (isinstance(component_report, dict) and isinstance(component_index, int)):
        return {}
    comps = component_report.get("components", [])
    if not isinstance(comps, list):
        return {}
    for c in comps:
        if isinstance(c, dict) and c.get("component_index") == component_index:
            return c
    return {}


def _nearest_boundary_distance_2d(
    atlas_v2: Optional[Dict[str, Any]],
    inputs: Dict[str, Any],
    kx: str,
    ky: str,
) -> Optional[float]:
    if not (isinstance(atlas_v2, dict) and isinstance(inputs, dict)):
        return None
    slices = atlas_v2.get("slices", [])
    if not isinstance(slices, list):
        return None
    if not (_is_num(inputs.get(kx)) and _is_num(inputs.get(ky))):
        return None
    x = float(inputs[kx]); y = float(inputs[ky])
    best = None
    for sl in slices:
        if not isinstance(sl, dict):
            continue
        if sl.get("lever_x") != kx or sl.get("lever_y") != ky:
            continue
        lines = sl.get("boundary_polylines", [])
        if not isinstance(lines, list):
            continue
        for line in lines:
            if not isinstance(line, list):
                continue
            for p in line:
                if isinstance(p, dict) and _is_num(p.get(kx)) and _is_num(p.get(ky)):
                    d = math.hypot(float(p[kx]) - x, float(p[ky]) - y)
                    if best is None or d < best:
                        best = d
    return best


def _nearest_overlay_distance_2d(
    overlay: Optional[Dict[str, Any]],
    inputs: Dict[str, Any],
    kx: str,
    ky: str,
) -> Optional[float]:
    if not (isinstance(overlay, dict) and isinstance(inputs, dict)):
        return None
    if not (_is_num(inputs.get(kx)) and _is_num(inputs.get(ky))):
        return None
    pts = extract_xy_points(overlay, kx, ky)
    if not pts:
        return None
    x = float(inputs[kx]); y = float(inputs[ky])
    best = None
    for p in pts:
        d = math.hypot(float(p[kx]) - x, float(p[ky]) - y)
        if best is None or d < best:
            best = d
    return best


def build_design_candidates(
    *,
    artifacts: List[Dict[str, Any]],
    topology: Optional[Dict[str, Any]] = None,
    component_dominance: Optional[Dict[str, Any]] = None,
    boundary_atlas_v2: Optional[Dict[str, Any]] = None,
    design_family_report: Optional[Dict[str, Any]] = None,
    literature_overlay: Optional[Dict[str, Any]] = None,
    max_candidates: int = 12,
) -> List[Dict[str, Any]]:
    # pick feasible artifacts and dedupe by id
    uniq: List[Dict[str, Any]] = []
    seen = set()
    for a in artifacts or []:
        if not (isinstance(a, dict) and a.get("kind") == "shams_run_artifact"):
            continue
        aid = a.get("id") or json.dumps(a.get("inputs", {}), sort_keys=True)[:128]
        if aid in seen:
            continue
        seen.add(aid)
        feas = _artifact_feasible(a)
        if feas is True:
            uniq.append(a)

    # cap
    uniq = uniq[:max_candidates]

    # best-effort component index from design family report (if it includes component_index) else None
    family_ci = None
    if isinstance(design_family_report, dict) and isinstance(design_family_report.get("component_index"), int):
        family_ci = int(design_family_report["component_index"])

    candidates: List[Dict[str, Any]] = []
    for a in uniq:
        inp = a.get("inputs", {})
        if not isinstance(inp, dict):
            continue
        worst_name, worst_mf = _worst_hard(a)

        ci = family_ci  # fallback; in future can assign via nearest component like v109 does
        comp_info = _lookup_component_info(component_dominance, ci)

        # robustness metrics from design family report (if family report corresponds to same component)
        fam = design_family_report if isinstance(design_family_report, dict) else None
        robustness = {}
        if fam:
            robustness = {
                "family_component_index": fam.get("component_index"),
                "family_feasible_fraction": fam.get("feasible_fraction"),
                "family_n_samples": fam.get("n_samples"),
                "family_top_worst_hard": (fam.get("worst_hard_ranked") or [{}])[0] if isinstance(fam.get("worst_hard_ranked"), list) and fam.get("worst_hard_ranked") else None,
            }

        # boundary distances for a few canonical pairs
        canonical_pairs = [("R0_m","Bt_T"), ("R0_m","Ip_MA"), ("Bt_T","Ip_MA"), ("R0_m","a_m")]
        boundary = {}
        lit = {}
        for kx,ky in canonical_pairs:
            d = _nearest_boundary_distance_2d(boundary_atlas_v2, inp, kx, ky)
            if d is not None:
                boundary[f"{kx}_vs_{ky}"] = d
            ld = _nearest_overlay_distance_2d(literature_overlay, inp, kx, ky)
            if ld is not None:
                lit[f"{kx}_vs_{ky}"] = ld

        candidate = {
            "kind": "shams_design_candidate",
            "created_utc": _created_utc(),
            "source_artifact_id": a.get("id"),
            "inputs": inp,
            "component_index": ci,
            "feasibility": {
                "feasible": True,
                "worst_hard": worst_name,
                "worst_hard_margin_frac": worst_mf,
            },
            "robustness": robustness,
            "causality": {
                "dominance_top_constraints": comp_info.get("dominance_top_constraints"),
                "top_failure_modes_near_component": comp_info.get("top_failure_modes_near_component"),
            },
            "boundary_distance_2d": boundary,
            "literature_distance_2d": lit,
            "notes": [
                "Boundary distances are 2D slice distances (lever-pair). They are best-effort indicators, not full multidimensional distances.",
                "Literature distances are computed only if a user-provided overlay JSON was loaded.",
            ],
        }
        candidates.append(candidate)

    return candidates


def build_comparison_table(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for c in candidates or []:
        if not isinstance(c, dict):
            continue
        inp = c.get("inputs", {})
        feas = (c.get("feasibility") or {})
        robustness = (c.get("robustness") or {})
        row = {
            "source_artifact_id": c.get("source_artifact_id"),
            "component_index": c.get("component_index"),
            "R0_m": inp.get("R0_m"),
            "a_m": inp.get("a_m"),
            "Bt_T": inp.get("Bt_T"),
            "Ip_MA": inp.get("Ip_MA"),
            "fG": inp.get("fG"),
            "Ti_keV": inp.get("Ti_keV"),
            "Paux_MW": inp.get("Paux_MW"),
            "worst_hard": feas.get("worst_hard"),
            "worst_hard_margin_frac": feas.get("worst_hard_margin_frac"),
            "family_feasible_fraction": robustness.get("family_feasible_fraction"),
            "family_n_samples": robustness.get("family_n_samples"),
        }
        # bring a few boundary distances
        bd = c.get("boundary_distance_2d", {})
        if isinstance(bd, dict):
            for k in ["R0_m_vs_Bt_T","R0_m_vs_Ip_MA","Bt_T_vs_Ip_MA","R0_m_vs_a_m"]:
                row[f"bd_{k}"] = bd.get(k)
        ld = c.get("literature_distance_2d", {})
        if isinstance(ld, dict):
            for k in ["R0_m_vs_Bt_T","R0_m_vs_Ip_MA","Bt_T_vs_Ip_MA","R0_m_vs_a_m"]:
                row[f"lit_{k}"] = ld.get(k)
        rows.append(row)
    return rows


def build_design_decision_pack(
    *,
    candidates: List[Dict[str, Any]],
    version: str = "v113",
    decision_justification: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    created = _created_utc()
    candidates_json = json.dumps({"kind":"shams_design_candidates","created_utc": created, "version": version, "candidates": candidates}, indent=2, sort_keys=True).encode("utf-8")

    # v114 decision justification (optional)
    just_obj = decision_justification if isinstance(decision_justification, dict) else None
    just_bytes = json.dumps(just_obj, indent=2, sort_keys=True).encode("utf-8") if just_obj is not None else None

    table_rows = build_comparison_table(candidates)
    # CSV
    fieldnames = []
    for r in table_rows:
        for k in r.keys():
            if k not in fieldnames:
                fieldnames.append(k)
    sbuf = io.StringIO()
    w = csv.DictWriter(sbuf, fieldnames=fieldnames)
    w.writeheader()
    for r in table_rows:
        w.writerow(r)
    csv_bytes = sbuf.getvalue().encode("utf-8")

    # Markdown report
    md = []
    md.append("# SHAMS Design Decision Pack")
    md.append("")
    md.append(f"- Version: {version}")
    md.append(f"- Created (UTC): {created}")
    md.append(f"- Candidates: {len(candidates)}")
    md.append("")
    md.append("## Candidate selection principles")
    md.append("")
    md.append("- Candidates are feasible run artifacts selected from the run ledger.")
    md.append("- Robustness signals are derived from local design family sampling (v111), when provided.")
    md.append("- Boundary distances are 2D slice distances derived from Boundary Atlas v2 (v110).")
    md.append("- Literature distances appear only if user overlay points were provided (v112).")
    md.append("")
    md.append("## Files")
    md.append("")
    md.append("- candidates.json")
    md.append("- comparison_table.csv")
    md.append("- manifest.json")
    md.append("- decision_justification.json (optional; v114 preferences + Pareto)")
    report_bytes = ("\n".join(md) + "\n").encode("utf-8")

    import zipfile
    from io import BytesIO
    zbuf = BytesIO()
    manifest = {
        "kind": "shams_design_decision_pack_manifest",
        "version": version,
        "created_utc": created,
        "files": {
            "candidates.json": {"sha256": _sha256_bytes(candidates_json), "bytes": len(candidates_json)},
            "comparison_table.csv": {"sha256": _sha256_bytes(csv_bytes), "bytes": len(csv_bytes)},
            "DESIGN_DECISION_REPORT.md": {"sha256": _sha256_bytes(report_bytes), "bytes": len(report_bytes)},
        },
    }
    if just_bytes is not None:
        manifest["files"]["decision_justification.json"] = {"sha256": _sha256_bytes(just_bytes), "bytes": len(just_bytes)}
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    manifest["files"]["manifest.json"] = {"sha256": _sha256_bytes(manifest_bytes), "bytes": len(manifest_bytes)}

    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("candidates.json", candidates_json)
        z.writestr("comparison_table.csv", csv_bytes)
        z.writestr("DESIGN_DECISION_REPORT.md", report_bytes)
        if just_bytes is not None:
            z.writestr("decision_justification.json", just_bytes)
        z.writestr("manifest.json", manifest_bytes)

    return {
        "kind": "shams_design_decision_pack",
        "version": version,
        "created_utc": created,
        "n_candidates": len(candidates),
        "manifest": manifest,
        "zip_bytes": zbuf.getvalue(),
    }
