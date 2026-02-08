from __future__ import annotations
"""Pareto from Study (v129)

Compute Pareto fronts (non-dominated layers) from a v127 study_matrix bundle (zip or folder).

Zero-risk:
- Reads only the study index (csv/json)
- Does not invoke physics or solvers
- Produces publishable tables + manifest

Conventions:
- Objectives are specified as list of dicts: {"k": "<column>", "sense": "max"|"min"}.
- Filters can be applied before Pareto computation (e.g., feasible only, mission, KPI thresholds).
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from io import BytesIO, StringIO
import json, csv, zipfile, time, hashlib

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def _safe_float(x):
    try:
        if x is None: return None
        if isinstance(x, bool): return None
        if isinstance(x, (int,float)): return float(x)
        s=str(x).strip()
        if s=="": return None
        return float(s)
    except Exception:
        return None

def load_study_files(path: str) -> Dict[str, bytes]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    if p.is_dir():
        out: Dict[str, bytes] = {}
        base = p
        for f in base.rglob("*"):
            if f.is_file():
                out[str(f.relative_to(base)).replace("\\","/")] = f.read_bytes()
        return out
    with zipfile.ZipFile(p, "r") as z:
        return {n: z.read(n) for n in z.namelist() if not n.endswith("/")}

def parse_index(files: Dict[str, bytes]) -> Tuple[str, List[Dict[str, Any]]]:
    if "study_index.json" in files:
        j = json.loads(files["study_index.json"].decode("utf-8"))
        return str(j.get("created_utc","")), list(j.get("rows") or [])
    if "study_index.csv" in files:
        s = files["study_index.csv"].decode("utf-8", errors="replace")
        rows = list(csv.DictReader(StringIO(s)))
        return "", rows
    raise ValueError("study_index.csv/json not found")


def filter_rows(
    rows: List[Dict[str, Any]],
    *,
    feasible_only: bool = False,
    mission: Optional[str] = None,
    kpi_filters: Optional[Dict[str, Tuple[Optional[float], Optional[float]]]] = None,
) -> List[Dict[str, Any]]:
    out=[]
    for r in rows:
        if feasible_only:
            if str(r.get("feasible")).lower() not in ("true","1","yes"):
                continue
        if mission and str(r.get("mission","")) != mission:
            continue
        ok=True
        if kpi_filters:
            for k,(lo,hi) in kpi_filters.items():
                v=_safe_float(r.get(k))
                if v is None:
                    ok=False; break
                if lo is not None and v < lo: ok=False; break
                if hi is not None and v > hi: ok=False; break
        if ok:
            out.append(r)
    return out

def dominates(a: List[float], b: List[float]) -> bool:
    """Return True if a Pareto-dominates b (a no worse in all, better in at least one)."""
    better=False
    for ai,bi in zip(a,b):
        if ai < bi:
            return False
        if ai > bi:
            better=True
    return better

def pareto_layers(points: List[List[float]]) -> Tuple[List[int], List[List[int]]]:
    """Compute non-dominated sorting. Returns (rank per point, layers list of indices)."""
    n=len(points)
    S=[[] for _ in range(n)]
    ndom=[0]*n
    fronts=[]
    F0=[]
    for p in range(n):
        for q in range(n):
            if p==q: continue
            if dominates(points[p], points[q]):
                S[p].append(q)
            elif dominates(points[q], points[p]):
                ndom[p]+=1
        if ndom[p]==0:
            F0.append(p)
    fronts.append(F0)
    i=0
    while i < len(fronts) and fronts[i]:
        Q=[]
        for p in fronts[i]:
            for q in S[p]:
                ndom[q]-=1
                if ndom[q]==0:
                    Q.append(q)
        i+=1
        if Q:
            fronts.append(Q)
    rank=[None]*n  # type: ignore
    for i,f in enumerate(fronts):
        for idx in f:
            rank[idx]=i
    # type ignore fallback
    rank=[int(r) if r is not None else (len(fronts)+1) for r in rank]
    return rank, fronts

def build_pareto(
    *,
    study_path: str,
    objectives: List[Dict[str, str]],
    feasible_only: bool = True,
    mission: Optional[str] = None,
    kpi_filters: Optional[Dict[str, Tuple[Optional[float], Optional[float]]]] = None,
    version: str = "v129",
) -> Dict[str, Any]:
    files = load_study_files(study_path)
    created_src, rows = parse_index(files)
    created = _created_utc()

    if not objectives:
        raise ValueError("objectives required")
    obj_cols=[str(o.get("k")) for o in objectives]
    senses=[str(o.get("sense","max")).lower() for o in objectives]
    if any(s not in ("max","min") for s in senses):
        raise ValueError("objective sense must be max or min")

    fr = filter_rows(rows, feasible_only=feasible_only, mission=mission, kpi_filters=kpi_filters)
    if not fr:
        raise ValueError("no rows after filtering")

    # Build points in 'maximize' space (convert min -> -value)
    pts=[]
    keep_rows=[]
    for r in fr:
        vec=[]
        ok=True
        for col,sense in zip(obj_cols,senses):
            v=_safe_float(r.get(col))
            if v is None:
                ok=False; break
            vec.append(v if sense=="max" else -v)
        if ok:
            pts.append(vec)
            keep_rows.append(r)
    if not pts:
        raise ValueError("no numeric objective rows")

    rank, fronts = pareto_layers(pts)

    # Build output table rows
    out_rows=[]
    for i,(r,rr) in enumerate(zip(keep_rows, rank)):
        row=dict(r)
        row["pareto_rank"]=rr
        out_rows.append(row)

    # Sort by rank then by first objective desc
    def _key(x):
        r=int(x.get("pareto_rank", 9999))
        v=_safe_float(x.get(obj_cols[0]))
        return (r, -(v if v is not None else -1e99))
    out_rows=sorted(out_rows, key=_key)

    # counts per layer
    layer_counts={}
    for rr in rank:
        layer_counts[str(rr)] = layer_counts.get(str(rr), 0) + 1

    rep={
        "kind":"shams_pareto_report",
        "version": version,
        "created_utc": created,
        "source_created_utc": created_src,
        "filters": {"feasible_only": feasible_only, "mission": mission, "kpi_filters": kpi_filters},
        "objectives": objectives,
        "n_rows": len(rows),
        "n_filtered": len(keep_rows),
        "layer_counts": layer_counts,
        "rows": out_rows,
    }
    return rep

def pareto_bundle_zip(report: Dict[str, Any]) -> Dict[str, Any]:
    created = report.get("created_utc") or _created_utc()
    # csv table
    rows = list(report.get("rows") or [])
    if rows:
        fieldnames = list(rows[0].keys())
    else:
        fieldnames = ["case_id","pareto_rank"]
    buf = StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k) for k in fieldnames})
    csv_bytes = buf.getvalue().encode("utf-8")

    json_bytes = json.dumps(report, indent=2, sort_keys=True).encode("utf-8")
    manifest = {
        "kind":"shams_pareto_bundle_manifest",
        "version":"v129",
        "created_utc": created,
        "files": {
            "pareto_report_v129.json": {"sha256": _sha256(json_bytes), "bytes": len(json_bytes)},
            "pareto_table_v129.csv": {"sha256": _sha256(csv_bytes), "bytes": len(csv_bytes)},
        }
    }
    man_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    zbuf = BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pareto_report_v129.json", json_bytes)
        z.writestr("pareto_table_v129.csv", csv_bytes)
        z.writestr("manifest_v129.json", man_bytes)
    return {"kind":"shams_pareto_bundle", "version":"v129", "created_utc": created, "manifest": manifest, "zip_bytes": zbuf.getvalue()}
