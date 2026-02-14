from __future__ import annotations
"""Feasibility Science Pack (v107)

Unifies Direction B outputs into a single publishable bundle:
- feasible_topology.json
- constraint_dominance_report.json
- failure_taxonomy_report.json
- FEASIBILITY_SCIENCE_REPORT.md
- feasibility_science_pack_summary.json
- feasibility_science_pack.zip

Additive only: operates on already-produced artifacts (run artifacts, atlas, etc.).
"""

from typing import Any, Dict, List, Optional, Tuple
import json
import time
import zipfile
from io import BytesIO
from pathlib import Path

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256_bytes(b: bytes) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def _sha256_file(p: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, indent=2, sort_keys=True).encode("utf-8")

def _nearest_component_index(topology: Dict[str, Any], point: Dict[str, Any]) -> Optional[int]:
    # best-effort: map to component by nearest point index
    pts = topology.get("points")
    comps = topology.get("components")
    lever_keys = topology.get("lever_keys")
    bounds = topology.get("lever_bounds")
    if not (isinstance(pts, list) and isinstance(comps, list) and isinstance(lever_keys, list) and isinstance(bounds, dict)):
        return None
    scales = {}
    for k, ab in bounds.items():
        if isinstance(ab, list) and len(ab) == 2:
            try:
                scales[k] = max(float(ab[1]) - float(ab[0]), 1e-12)
            except Exception:
                pass
    # distance to each point
    best_i = None
    best_d = None
    for i, p in enumerate(pts):
        if not isinstance(p, dict):
            continue
        s = 0.0
        n = 0
        for k in lever_keys:
            if k not in scales:
                continue
            if k not in p or k not in point:
                continue
            try:
                dx = (float(point[k]) - float(p[k])) / float(scales[k])
            except Exception:
                continue
            s += dx*dx
            n += 1
        if n == 0:
            continue
        d = (s/n) ** 0.5
        if best_d is None or d < best_d:
            best_d = d
            best_i = i
    if best_i is None:
        return None
    # find which component contains best_i
    for ci, comp in enumerate(comps):
        if isinstance(comp, list) and best_i in comp:
            return ci
    return None

def build_feasibility_science_pack(
    *,
    topology: Dict[str, Any],
    dominance: Dict[str, Any],
    failures: Dict[str, Any],
    source_run_ids: Optional[List[str]] = None,
    version: str = "v107",
) -> Dict[str, Any]:
    """Return a dict containing all bundle contents + a zip bytes payload."""
    created = _created_utc()
    source_run_ids = source_run_ids or []

    # summary scalars
    comps = topology.get("components", [])
    comp_sizes = [len(c) for c in comps] if isinstance(comps, list) else []
    n_components = len(comp_sizes)
    largest = max(comp_sizes) if comp_sizes else 0

    ranked = dominance.get("constraints_ranked", [])
    top_constraints = []
    if isinstance(ranked, list):
        for r in ranked[:8]:
            if isinstance(r, dict):
                top_constraints.append({
                    "name": r.get("name"),
                    "score": r.get("dominance_score"),
                    "fail_rate": r.get("fail_rate"),
                    "near_rate": r.get("near_boundary_rate"),
                })

    counts_by_mode = failures.get("counts_by_mode", {})
    top_failure_modes = []
    if isinstance(counts_by_mode, dict):
        for k in list(counts_by_mode.keys())[:10]:
            top_failure_modes.append({"mode": k, "count": counts_by_mode.get(k)})

    # component-linked dominance/failures (best-effort)
    comp_link = []
    # Map failure records to components based on nearest feasible point
    failure_records = failures.get("records", [])
    mode_counts_by_comp: Dict[int, Dict[str, int]] = {}
    if isinstance(failure_records, list):
        for rec in failure_records:
            if not isinstance(rec, dict):
                continue
            pt = rec.get("inputs", {})
            if not isinstance(pt, dict):
                continue
            ci = _nearest_component_index(topology, pt)
            if ci is None:
                continue
            mode = rec.get("mode")
            if not isinstance(mode, str):
                continue
            mode_counts_by_comp.setdefault(ci, {}).setdefault(mode, 0)
            mode_counts_by_comp[ci][mode] += 1

    # Dominance per component is difficult without storing per-run constraint rows;
    # we provide a conservative placeholder: global dominance + per-component failure mix.
    for ci in range(n_components):
        mode_counts = mode_counts_by_comp.get(ci, {})
        topm = []
        if isinstance(mode_counts, dict) and mode_counts:
            for m, v in sorted(mode_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]:
                topm.append({"mode": m, "count": v})
        comp_link.append({
            "component_index": ci,
            "component_size": comp_sizes[ci] if ci < len(comp_sizes) else None,
            "top_failure_modes_near_component": topm,
        })

    summary = {
        "kind": "shams_feasibility_science_pack_summary",
        "created_utc": created,
        "version": version,
        "source_run_ids": source_run_ids,
        "topology": {
            "n_points": topology.get("n_points"),
            "n_edges": topology.get("n_edges"),
            "n_components": n_components,
            "largest_component_size": largest,
            "component_sizes": comp_sizes[:25],
        },
        "top_constraints": top_constraints,
        "top_failure_modes": top_failure_modes,
        "component_links": comp_link[:50],
    }

    # markdown report
    md = []
    md.append("# SHAMS Feasibility Science Report")
    md.append("")
    md.append(f"- Created (UTC): {created}")
    md.append(f"- Version: {version}")
    md.append(f"- Source run ids: {len(source_run_ids)}")
    md.append("")
    md.append("## Feasible Space Topology")
    md.append("")
    md.append(f"- Components: **{n_components}**")
    md.append(f"- Largest feasible island: **{largest}** points")
    if comp_sizes:
        md.append(f"- Component sizes (top): {comp_sizes[:10]}")
    md.append("")
    md.append("## Constraint Dominance (global)")
    md.append("")
    if top_constraints:
        for r in top_constraints:
            md.append(f"- `{r['name']}`: score={r['score']}, fail_rate={r['fail_rate']}, near_rate={r['near_rate']}")
    else:
        md.append("- (No dominance rows found.)")
    md.append("")
    md.append("## Failure Modes (global)")
    md.append("")
    if top_failure_modes:
        for r in top_failure_modes[:10]:
            md.append(f"- `{r['mode']}`: {r['count']}")
    else:
        md.append("- (No failure modes found.)")
    md.append("")
    md.append("## Failure Modes by Feasible Island (best-effort)")
    md.append("")
    if comp_link:
        for cl in comp_link[:10]:
            md.append(f"### Component {cl['component_index']} (size={cl['component_size']})")
            t = cl.get("top_failure_modes_near_component", [])
            if t:
                for m in t:
                    md.append(f"- `{m['mode']}`: {m['count']}")
            else:
                md.append("- (No mapped failures near this component.)")
    md.append("")
    md.append("## Notes")
    md.append("")
    md.append("- This pack is additive and audit-ready: it contains raw JSON artifacts plus this summary report.")
    md.append("- Component-linked failure mapping uses nearest-feasible-point assignment; treat it as exploratory until higher-fidelity mapping is added.")
    report_md = "\n".join(md) + "\n"

    # bundle zip
    files = {
        "feasible_topology.json": _json_bytes(topology),
        "constraint_dominance_report.json": _json_bytes(dominance),
        "failure_taxonomy_report.json": _json_bytes(failures),
        "feasibility_science_pack_summary.json": _json_bytes(summary),
        "FEASIBILITY_SCIENCE_REPORT.md": report_md.encode("utf-8"),
    }

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    zip_bytes = buf.getvalue()

    out = {
        "kind": "shams_feasibility_science_pack",
        "created_utc": created,
        "version": version,
        "summary": summary,
        "files": {k: {"bytes": len(v), "sha256": _sha256_bytes(v)} for k, v in files.items()},
        "zip_bytes": zip_bytes,
        "zip_sha256": _sha256_bytes(zip_bytes),
    }
    return out
