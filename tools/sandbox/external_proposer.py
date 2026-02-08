from __future__ import annotations
"""
External Proposer Adapter (SAFE):
- Accepts candidate designs from external tools (e.g., PROCESS) as JSON.
- Audits each candidate via SHAMS.
- Keeps ONLY audited-feasible candidates.
- Optionally merges them into an existing SHAMS feasible dataset for sandbox ranking.

This preserves invariants:
- External tools never define feasibility.
- No constraint relaxation, no penalties.
- Outputs are explicitly NON-AUTHORITATIVE selections.
"""
import argparse, json, os, time
from typing import Any, Dict, List, Optional
from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from constraints.system import build_constraints_from_outputs
from tools.process_compat.process_compat import constraints_to_records, active_constraints, feasibility_flag, failure_mode, constraint_set_hash
from tools.sandbox.selector import Objective, rank_feasible_points, filter_by_min_margin, manifest_hash

def parse_objectives(s: str) -> List[Objective]:
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

def audit_design(d: Dict[str, Any]) -> Dict[str, Any]:
    inp = PointInputs(**PointInputs.sanitize(d))
    out = hot_ion_point(inp)
    cons = build_constraints_from_outputs(out)
    recs = constraints_to_records(cons)
    return {
        "inputs": d,
        "outputs": out,
        "feasible": feasibility_flag(recs),
        "failure_mode": failure_mode(recs),
        "active_constraints": [c.name for c in active_constraints(recs) if c.name],
        "min_signed_margin": min((r.signed_margin for r in recs if r.name), default=float("nan")),
        "constraint_set_hash": constraint_set_hash(recs),
    }

def main():
    ap = argparse.ArgumentParser(description="External proposer adapter: audit external candidates then rank feasible ones.")
    ap.add_argument("--candidates-json", required=True, help="JSON list of design dicts (e.g., exported from PROCESS)")
    ap.add_argument("--feasible-scan-json", default=None, help="Optional feasible_scan.json to merge with audited candidates")
    ap.add_argument("--objectives", required=True, help="e.g. R0:min:1.0,Q:max:2.0")
    ap.add_argument("--min-margin", type=float, default=None)
    ap.add_argument("--topk", type=int, default=20)
    ap.add_argument("--outdir", default="out_external_adapter")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    objectives = parse_objectives(args.objectives)

    with open(args.candidates_json, "r", encoding="utf-8") as f:
        candidates = json.load(f)
    if isinstance(candidates, dict):
        candidates = [candidates]
    if not isinstance(candidates, list):
        raise SystemExit("candidates-json must be a dict or list of dicts")

    audited = [audit_design(d) for d in candidates]
    feasible_ext = [a for a in audited if a.get("feasible", False)]

    merged = list(feasible_ext)

    base_data = None
    if args.feasible_scan_json:
        with open(args.feasible_scan_json, "r", encoding="utf-8") as f:
            base_data = json.load(f)
        pts = base_data.get("points", [])
        base_feas = [p for p in pts if p.get("feasible", False)]
        merged.extend(base_feas)

    merged = filter_by_min_margin(merged, args.min_margin)
    ranked = rank_feasible_points(merged, objectives)
    ranked_top = ranked[:max(1, int(args.topk))]

    out = {
        "kind": "external_proposer_sandbox_run",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "inputs": {
            "candidates_json": os.path.abspath(args.candidates_json),
            "feasible_scan_json": os.path.abspath(args.feasible_scan_json) if args.feasible_scan_json else None,
            "objectives": [o.__dict__ for o in objectives],
            "min_margin": args.min_margin,
            "topk": args.topk,
        },
        "counts": {
            "candidates_in": len(candidates),
            "audited_feasible": len(feasible_ext),
            "merged_pool": len(merged),
        },
        "hashes": {
            "candidates_sha256": manifest_hash(candidates),
            "base_feasible_scan_sha256": manifest_hash(base_data) if base_data else None,
            "objectives_sha256": manifest_hash([o.__dict__ for o in objectives]),
        },
        "audited": audited,
        "ranked_top": ranked_top,
        "non_authoritative_notice": "External proposer runs are non-authoritative. Only SHAMS audits determine feasibility; rankings are secondary.",
    }

    out_json = os.path.join(args.outdir, "external_proposer_run.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)

    print(f"Wrote: {out_json}")

if __name__ == "__main__":
    main()
