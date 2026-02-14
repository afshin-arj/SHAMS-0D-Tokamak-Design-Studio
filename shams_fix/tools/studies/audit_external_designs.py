from __future__ import annotations
"""
Audit externally optimized designs through SHAMS.
"""
import argparse, json
from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from constraints.system import build_constraints_from_outputs
from tools.process_compat.process_compat import constraints_to_records, active_constraints, feasibility_flag, failure_mode

def main():
    ap = argparse.ArgumentParser(description="Audit external design(s) via SHAMS")
    ap.add_argument("--design-json", required=True, help="Single design or list of designs")
    ap.add_argument("--out", default="audit_report.json")
    args = ap.parse_args()

    with open(args.design_json) as f:
        designs = json.load(f)
    if isinstance(designs, dict):
        designs = [designs]

    reports = []
    for d in designs:
        inp = PointInputs(**PointInputs.sanitize(d))
        out = hot_ion_point(inp)
        cons = build_constraints_from_outputs(out)
        recs = constraints_to_records(cons)
        reports.append({
            "feasible": feasibility_flag(recs),
            "failure_mode": failure_mode(recs),
            "active_constraints": [c.name for c in active_constraints(recs)],
            "design": d
        })

    with open(args.out, "w") as f:
        json.dump({"reports": reports}, f, indent=2)

    print(f"Wrote audit report: {args.out}")

if __name__ == "__main__":
    main()
