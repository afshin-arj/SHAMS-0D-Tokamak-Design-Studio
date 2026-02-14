from __future__ import annotations
"""Feasibility Boundary Atlas (v124)

Runs an explicit 2D grid scan around a baseline input set, evaluates each point using frozen physics + constraints,
and builds a SHAMS-native feasibility atlas bundle:
- grid points with feasibility + dominant failure constraint
- boundary extraction (uses boundary_atlas_v2 algorithm)
- publishable plots and manifest (SHA256)

Additive only: no physics/solver changes.
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import time, json, hashlib, csv, io, math

from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from constraints.constraints import evaluate_constraints
from src.shams_io.run_artifact import build_run_artifact, write_run_artifact
from tools.boundary_atlas_v2 import build_boundary_atlas_v2

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def _linspace(lo: float, hi: float, n: int) -> List[float]:
    if n <= 1:
        return [0.5*(lo+hi)]
    step = (hi-lo)/float(n-1)
    return [lo + i*step for i in range(n)]

def _is_num(x: Any) -> bool:
    try:
        float(x); return True
    except Exception:
        return False

def available_numeric_levers(baseline_inputs: Dict[str, Any]) -> List[str]:
    out=[]
    for k,v in (baseline_inputs or {}).items():
        if _is_num(v):
            out.append(k)
    return sorted(out)

def _extract_point_row(art: Dict[str, Any], kx: str, ky: str) -> Dict[str, Any]:
    inp = art.get("inputs", {}) if isinstance(art.get("inputs"), dict) else {}
    cs = art.get("constraints_summary", {}) if isinstance(art.get("constraints_summary"), dict) else {}
    return {
        kx: float(inp.get(kx)) if _is_num(inp.get(kx)) else None,
        ky: float(inp.get(ky)) if _is_num(inp.get(ky)) else None,
        "feasible": cs.get("feasible"),
        "worst_hard": cs.get("worst_hard"),
        "worst_hard_margin_frac": cs.get("worst_hard_margin_frac"),
        "worst_soft": cs.get("worst_soft"),
        "worst_soft_margin_frac": cs.get("worst_soft_margin_frac"),
        "artifact_id": art.get("id"),
    }

def scan_grid(
    *,
    baseline_inputs: Dict[str, Any],
    lever_x: str,
    lever_y: str,
    x_range: Tuple[float, float],
    y_range: Tuple[float, float],
    nx: int,
    ny: int,
    label: str = "atlas",
    outdir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Returns list of shams_run_artifact payloads for each grid point. Optionally writes artifacts to outdir."""
    xs = _linspace(float(x_range[0]), float(x_range[1]), int(nx))
    ys = _linspace(float(y_range[0]), float(y_range[1]), int(ny))

    out_payloads: List[Dict[str, Any]] = []
    od = Path(outdir) if outdir else None
    if od:
        od.mkdir(parents=True, exist_ok=True)

    # deterministic ordering
    idx = 0
    for j,y in enumerate(ys):
        for i,x in enumerate(xs):
            inp_dict = dict(baseline_inputs or {})
            inp_dict[lever_x] = float(x)
            inp_dict[lever_y] = float(y)
            inp = PointInputs(**inp_dict)

            out = hot_ion_point(inp)
            cons = evaluate_constraints(out)
            art = build_run_artifact(
                inputs=dict(inp.__dict__),
                outputs=dict(out) if isinstance(out, dict) else {},
                constraints=cons,
                meta={"label": f"{label}_{idx:05d}", "mode":"feasibility_atlas_v124"},
                solver={"message":"feasibility_atlas_v124"},
                baseline_inputs=dict(baseline_inputs or {}),
                scan={"kind":"grid_2d", "lever_x": lever_x, "lever_y": lever_y, "i": i, "j": j, "nx": nx, "ny": ny},
                economics=dict((out or {}).get("_economics", {})) if isinstance(out, dict) else {},
            )
            out_payloads.append(art)
            if od:
                rdir = od / f"pt_{idx:05d}"
                rdir.mkdir(parents=True, exist_ok=True)
                write_run_artifact(rdir / "shams_run_artifact.json", art)
            idx += 1
    return out_payloads

def _plot_maps(points: List[Dict[str, Any]], kx: str, ky: str, outdir: Path) -> List[str]:
    """Generate simple publishable maps using matplotlib defaults."""
    import matplotlib.pyplot as plt

    rows = []
    for art in points:
        rows.append(_extract_point_row(art, kx, ky))

    xs=[r[kx] for r in rows if r[kx] is not None]
    ys=[r[ky] for r in rows if r[ky] is not None]
    feas=[r["feasible"] for r in rows if r[kx] is not None and r[ky] is not None]
    worst=[r.get("worst_hard") for r in rows if r[kx] is not None and r[ky] is not None]
    margin=[r.get("worst_hard_margin_frac") for r in rows if r[kx] is not None and r[ky] is not None]

    paths=[]

    # Feasible/infeasible scatter
    fig, ax = plt.subplots(figsize=(6.2,5.0))
    xf=[x for x,f in zip(xs,feas) if f is True]
    yf=[y for y,f in zip(ys,feas) if f is True]
    xi=[x for x,f in zip(xs,feas) if f is False]
    yi=[y for y,f in zip(ys,feas) if f is False]
    ax.scatter(xf, yf, s=10, marker="o", label="feasible")
    ax.scatter(xi, yi, s=10, marker="x", label="infeasible")
    ax.set_xlabel(kx); ax.set_ylabel(ky); ax.set_title("Feasibility map");
    ax.legend(loc="best")
    fig.tight_layout()
    p = outdir / "atlas_feasibility_map.png"
    fig.savefig(p, dpi=200); plt.close(fig)
    paths.append(p.name)

    # Dominant constraint labels (infeasible only) - show text-lite by mapping to integers
    uniq = sorted(set([w for w,f in zip(worst,feas) if f is False and isinstance(w,str)]))
    cmap = {name:i for i,name in enumerate(uniq)}
    codes=[cmap.get(w, -1) for w,f in zip(worst,feas) if f is False]
    xic=[x for x,f in zip(xs,feas) if f is False]
    yic=[y for y,f in zip(ys,feas) if f is False]
    if xic:
        fig, ax = plt.subplots(figsize=(6.2,5.0))
        sc=ax.scatter(xic, yic, c=codes, s=14, marker="s")
        ax.set_xlabel(kx); ax.set_ylabel(ky); ax.set_title("Dominant hard-constraint region (infeasible points)");
        fig.tight_layout()
        p = outdir / "atlas_dominant_constraint_map.png"
        fig.savefig(p, dpi=200); plt.close(fig)
        paths.append(p.name)
        # legend mapping
        legend_txt = "\n".join([f"{i}: {name}" for name,i in cmap.items()])
        (outdir / "atlas_dominant_constraint_legend.txt").write_text(legend_txt, encoding="utf-8")
        paths.append("atlas_dominant_constraint_legend.txt")

    # Worst hard margin heat scatter (all points where numeric)
    mvals=[]; xm=[]; ym=[]
    for x,y,m in zip(xs,ys,margin):
        try:
            if m is None: continue
            m=float(m)
        except Exception:
            continue
        xm.append(x); ym.append(y); mvals.append(m)
    if xm:
        fig, ax = plt.subplots(figsize=(6.2,5.0))
        ax.scatter(xm, ym, c=mvals, s=14, marker="o")
        ax.set_xlabel(kx); ax.set_ylabel(ky); ax.set_title("Worst hard margin fraction (color)");
        fig.tight_layout()
        p = outdir / "atlas_worst_hard_margin.png"
        fig.savefig(p, dpi=200); plt.close(fig)
        paths.append(p.name)

    return paths

def _csv_points(points: List[Dict[str, Any]], kx: str, ky: str) -> bytes:
    buf = io.StringIO()
    cols=[kx,ky,"feasible","worst_hard","worst_hard_margin_frac","worst_soft","worst_soft_margin_frac","artifact_id"]
    w=csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for art in points:
        r=_extract_point_row(art,kx,ky)
        w.writerow({c:r.get(c) for c in cols})
    return buf.getvalue().encode("utf-8")

def build_feasibility_atlas_bundle(
    *,
    baseline_run_artifact: Dict[str, Any],
    lever_x: str,
    lever_y: str,
    x_range: Tuple[float, float],
    y_range: Tuple[float, float],
    nx: int = 25,
    ny: int = 25,
    outdir: str = "out_feasibility_atlas_v124",
    version: str = "v124",
) -> Dict[str, Any]:
    if not (isinstance(baseline_run_artifact, dict) and baseline_run_artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("expected shams_run_artifact baseline")
    baseline_inputs = baseline_run_artifact.get("inputs", {})
    if not isinstance(baseline_inputs, dict):
        raise ValueError("baseline artifact missing inputs"
        )

    outp = Path(outdir)
    outp.mkdir(parents=True, exist_ok=True)

    # Run scan and write artifacts
    pts = scan_grid(
        baseline_inputs=baseline_inputs,
        lever_x=lever_x,
        lever_y=lever_y,
        x_range=x_range,
        y_range=y_range,
        nx=nx,
        ny=ny,
        label="atlas",
        outdir=str(outp / "grid_points"),
    )

    # Build boundary atlas (v2)
    atlas_v2 = build_boundary_atlas_v2(payloads=pts, lever_pairs=[(lever_x, lever_y)])

    # Write core files
    atlas_json_path = outp / "boundary_atlas_v2.json"
    atlas_json_path.write_text(json.dumps(atlas_v2, indent=2, sort_keys=True), encoding="utf-8"
    )

    points_csv = _csv_points(pts, lever_x, lever_y)
    (outp / "feasibility_points.csv").write_bytes(points_csv)

    # Plots (maps + boundary plots via existing plot module)
    plot_files = []
    plot_files += _plot_maps(pts, lever_x, lever_y, outp)

    # Boundary polyline plots (reuse existing plotting module deterministically)
    try:
        from tools.plot_boundary_atlas_v2 import main as _plot_main
        # emulate CLI by writing temp args
        # safer: call module via subprocess? avoid; import matplotlib in same process
    except Exception:
        _plot_main = None

    if _plot_main is not None:
        # run by invoking as a function with patched argv
        import sys as _sys
        argv0 = list(_sys.argv)
        try:
            _sys.argv = ["plot_boundary_atlas_v2", "--atlas", str(atlas_json_path), "--outdir", str(outp / "boundary_plots") ]
            rc = _plot_main()
            # collect produced files
            bp = outp / "boundary_plots"
            if bp.exists():
                for p in sorted(bp.glob("*.png")):
                    plot_files.append(str(p.relative_to(outp)))
                for p in sorted(bp.glob("*.svg")):
                    plot_files.append(str(p.relative_to(outp)))
        finally:
            _sys.argv = argv0

    # Bundle manifest + zip
    files: Dict[str, bytes] = {}
    # Collect representative files; zip stores from disk for large items (plots)
    def add_file(rel: str):
        p = outp / rel
        if p.exists() and p.is_file():
            b = p.read_bytes()
            files[rel] = b

    add_file("boundary_atlas_v2.json")
    add_file("feasibility_points.csv")
    for pf in plot_files:
        add_file(pf)

    manifest = {
        "kind":"shams_feasibility_atlas_manifest",
        "version": version,
        "created_utc": _created_utc(),
        "files": {k: {"sha256": _sha256_bytes(v), "bytes": len(v)} for k,v in files.items()},
        "notes": ["Feasibility atlas bundle (v124)."],
    }
    files["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    import zipfile
    from io import BytesIO
    zbuf = BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k, v)

    bundle = {
        "kind":"shams_feasibility_atlas",
        "version": version,
        "created_utc": _created_utc(),
        "baseline_run_id": baseline_run_artifact.get("id"),
        "lever_x": lever_x,
        "lever_y": lever_y,
        "grid": {"x_range": list(x_range), "y_range": list(y_range), "nx": int(nx), "ny": int(ny)},
        "atlas_v2": atlas_v2,
        "manifest": manifest,
        "zip_bytes": zbuf.getvalue(),
        "outdir": str(outp),
        "notes": ["Additive scan + boundary extraction; no physics changes."],
    }
    # Also write top-level summary json
    bundle_meta = dict(bundle)
    bundle_meta.pop("zip_bytes", None)
    (outp / "feasibility_atlas_v124.json").write_text(json.dumps(bundle_meta, indent=2, sort_keys=True), encoding="utf-8")
    return bundle
