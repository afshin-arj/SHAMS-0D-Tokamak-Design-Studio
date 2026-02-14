from __future__ import annotations
"""
CLI: Safe Optimization Sandbox

Inputs:
- feasible_scan.json produced by tools.studies.feasible_scan
Outputs:
- sandbox_run.json (non-authoritative ranking + manifest hashes)
- optional audit_report.json (SHAMS re-audit of top-K)

This does NOT change physics or solvers.
"""
import argparse, json, os, time
from typing import Any, Dict, List
from tools.sandbox.selector import Objective, rank_feasible_points, manifest_hash, filter_by_min_margin
from tools.studies.audit_external_designs import main as _audit_main  # reuse (writes its own file)

def parse_objectives(s: str) -> List[Objective]:
    # Format: key:min:weight,key2:max:weight
    out = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        bits = [b.strip() for b in part.split(":")]
        if len(bits) < 2:
            raise ValueError("Objective must be key:sense[:weight]")
        key, sense = bits[0], bits[1].lower()
        w = float(bits[2]) if len(bits) >= 3 else 1.0
        if sense not in ("min","max"):
            raise ValueError("sense must be min or max")
        out.append(Objective(key=key, sense=sense, weight=w))
    return out

def main():
    ap = argparse.ArgumentParser(description="SHAMS Optimization Sandbox (SAFE, non-authoritative)")
    ap.add_argument("--feasible-scan-json", required=True)
    ap.add_argument("--objectives", required=True, help="e.g. R0:min:1.0,Q:max:2.0")
    ap.add_argument("--min-margin", type=float, default=None, help="Optional minimum min_signed_margin filter")
    ap.add_argument("--topk", type=int, default=20)
    ap.add_argument("--outdir", default="out_sandbox")
    ap.add_argument("--reaudit-topk", type=int, default=10, help="Re-audit top K through SHAMS (default 10)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    with open(args.feasible_scan_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    pts = data.get("points", [])
    feasible = [p for p in pts if p.get("feasible", False)]
    feasible = filter_by_min_margin(feasible, args.min_margin)

    objectives = parse_objectives(args.objectives)
    ranked = rank_feasible_points(feasible, objectives)
    top = ranked[:max(1, int(args.topk))]

    run = {
        "kind": "optimization_sandbox_run",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "inputs": {
            "feasible_scan_json": os.path.abspath(args.feasible_scan_json),
            "objectives": [o.__dict__ for o in objectives],
            "min_margin": args.min_margin,
            "topk": args.topk,
        },
        "hashes": {
            "feasible_scan_sha256": manifest_hash(data),
            "objectives_sha256": manifest_hash([o.__dict__ for o in objectives]),
        },
        "ranked_top": top,
        "non_authoritative_notice": "Optimization Sandbox outputs are rankings over SHAMS-feasible points only. Feasibility truth remains in SHAMS.",
    }

    out_run = os.path.join(args.outdir, "sandbox_run.json")
    with open(out_run, "w", encoding="utf-8") as f:
        json.dump(run, f, indent=2, sort_keys=True)

    print(f"Wrote: {out_run}")

    # Re-audit top K (if inputs are available)
    reaudit_k = max(0, int(args.reaudit_topk))
    designs = []
    for p in top[:reaudit_k]:
        inp = p.get("inputs")
        if isinstance(inp, dict):
            designs.append(inp)
    if designs:
        tmp = os.path.join(args.outdir, "_topk_designs.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(designs, f, indent=2, sort_keys=True)
        out_audit = os.path.join(args.outdir, "audit_report.json")
        # Call audit tool by spawning a new process (keeps separation clean)
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "tools.studies.audit_external_designs", "--design-json", tmp, "--out", out_audit])
        print(f"Wrote: {out_audit}")
    else:
        print("No 'inputs' found for top-K; skipping re-audit. (Ensure feasible_scan includes inputs.)")

if __name__ == "__main__":
    main()
