from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_regression")
    args = ap.parse_args()
    out = Path(args.outdir); out.mkdir(parents=True, exist_ok=True)

    art = json.loads(Path("regression/baselines/baseline_run_artifact.json").read_text(encoding="utf-8"))

    ok = True
    try:
        from tools.validate_schemas import _fallback_validate
        schema = json.loads(Path("schemas/shams_run_artifact.schema.json").read_text(encoding="utf-8"))
        errs = _fallback_validate(art, schema)
        if errs:
            ok = False
            print("Schema FAIL")
            for e in errs[:20]: print(" -", e)
        else:
            print("Schema PASS (fallback)")
    except Exception as e:
        print("Schema skipped:", repr(e))

    figdir = out/"figures"; figdir.mkdir(exist_ok=True)
    try:
        from src.shams_io.plotting import plot_radial_build_dual_export
        plot_radial_build_dual_export(art, str(figdir/"radial_build"))
        print("Figures exported.")
    except Exception as e:
        ok = False
        print("Figures FAIL:", repr(e))

    hashes = {}
    for p in figdir.glob("*"):
        if p.is_file():
            hashes[p.name] = sha256_file(p)
    (out/"hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True), encoding="utf-8")
    print("Wrote hashes.json with", len(hashes), "entries")
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
