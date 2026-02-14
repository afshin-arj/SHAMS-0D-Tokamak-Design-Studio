#!/usr/bin/env python3
"""
SHAMS–FUSION-X v69 Upgrade: One-command Validation Bundle Runner

This script is validation-only. It does not modify physics or solver logic.
It orchestrates existing verification runners if present and creates a single
artifact bundle directory containing:
- logs
- summary.json
- rendered markdown report

Usage:
  python upgrade_v69/run_validation_bundle.py --root <path_to_repo_or_package_root> --out <artifact_dir>

If scripts are missing, it exits explicitly with diagnostics.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from pathlib import Path

def run(cmd, cwd: Path, log_path: Path) -> int:
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n$ {' '.join(cmd)}\n")
        f.flush()
        p = subprocess.Popen(cmd, cwd=str(cwd), stdout=f, stderr=subprocess.STDOUT)
        return p.wait()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Path to SHAMS package root")
    ap.add_argument("--out", required=True, help="Output artifact directory")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    log = out / "validation.log"
    summary = {
        "status": "UNKNOWN",
        "root": str(root),
        "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "steps": [],
    }

    candidates = [
        root / "verification" / "run_physics_benchmarks.py",
        root / "verification" / "run_ui_mode_benchmarks.py",
    ]

    missing = [str(p) for p in candidates if not p.exists()]
    if missing:
        summary["status"] = "FAILED"
        summary["error"] = "Missing expected verification runners"
        summary["missing"] = missing
        (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        with open(log, "a", encoding="utf-8") as f:
            f.write("\nERROR: Missing expected verification runners:\n")
            for m in missing:
                f.write(f" - {m}\n")
        return 2

    rc1 = run([sys.executable, str(candidates[0])], root, log)
    summary["steps"].append({"name": "physics_benchmarks", "rc": rc1})

    rc2 = run([sys.executable, str(candidates[1])], root, log)
    summary["steps"].append({"name": "ui_mode_benchmarks", "rc": rc2})

    ok = (rc1 == 0 and rc2 == 0)
    summary["status"] = "PASS" if ok else "FAIL"
    summary["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md = ["# SHAMS Validation Bundle", "", f"Root: `{root}`", "", f"Status: **{summary['status']}**", ""]
    for step in summary["steps"]:
        md.append(f"- {step['name']}: rc={step['rc']}")
    (out / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
