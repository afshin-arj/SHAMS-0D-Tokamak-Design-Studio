from __future__ import annotations
import argparse, json, os, hashlib
from typing import Any, Dict, List
from tools.process_compat.process_compat import constraint_set_hash

def main():
    ap = argparse.ArgumentParser(description="SHAMS→PROCESS Handoff (additive): export feasibility envelope from scan results.")
    ap.add_argument("--feasible-scan-json", required=True)
    ap.add_argument("--out", default="shams_process_handoff.json")
    args = ap.parse_args()

    with open(args.feasible_scan_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    pts = data.get("points", [])
    feas = [p for p in pts if p.get("feasible", False)]
    if not feas:
        raise SystemExit("No feasible points in scan. Cannot build handoff envelope.")

    var = data.get("meta", {}).get("var", feas[0].get("var",""))
    xs = [p.get("x") for p in feas if isinstance(p.get("x"), (int,float))]
    envelope = {
        "kind": "shams_process_handoff",
        "source": {
            "feasible_scan": os.path.abspath(args.feasible_scan_json),
            "meta": data.get("meta", {}),
        },
        "feasible_envelope": {
            "var": var,
            "x_min_feasible": float(min(xs)),
            "x_max_feasible": float(max(xs)),
        },
        "constraint_set_hash": feas[0].get("constraint_set_hash",""),
        "notes": [
            "This envelope is empirical from the provided scan; it is not a proof over all parameters.",
            "Any optimizer output must be re-audited through SHAMS for authoritative feasibility.",
        ],
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(envelope, f, indent=2, sort_keys=True)
    print(f"Wrote: {args.out}")

if __name__ == "__main__":
    main()
