from __future__ import annotations
import argparse, json, os
from typing import Any, Dict, List, Tuple
from tools.process_compat.process_compat import nondominated_mask

def parse_objectives(s: str) -> List[Tuple[str,str]]:
    """
    Format: key:min,key2:max
    """
    out = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        key, sense = part.split(":")
        sense = sense.strip().lower()
        if sense not in ("min","max"):
            raise ValueError("sense must be min or max")
        out.append((key.strip(), sense))
    if not out:
        raise ValueError("No objectives parsed")
    return out

def main():
    ap = argparse.ArgumentParser(description="Feasible Pareto (additive): Pareto filter over feasible points only.")
    ap.add_argument("--feasible-scan-json", required=True, help="Path to feasible_scan.json produced by feasible_scan.py")
    ap.add_argument("--objectives", required=True, help="Comma list like: R0:min,Q:max (keys must exist in point['outputs'] or point root)")
    ap.add_argument("--outdir", default="out_feasible_pareto")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    objectives = parse_objectives(args.objectives)

    with open(args.feasible_scan_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    pts = data["points"]
    feasible = []
    for p in pts:
        if p.get("feasible", False):
            # Flatten candidate objective keys (root or outputs)
            flat = dict(p)
            out = p.get("outputs", {})
            if isinstance(out, dict):
                for k, v in out.items():
                    if k not in flat:
                        flat[k] = v
            feasible.append(flat)

    mask = nondominated_mask(feasible, objectives)
    pareto = [feasible[i] for i, keep in enumerate(mask) if keep]

    out_json = os.path.join(args.outdir, "feasible_pareto.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"meta": {"kind":"feasible_pareto", "objectives": objectives}, "pareto": pareto}, f, indent=2, sort_keys=True)

    print(f"Feasible points: {len(feasible)}")
    print(f"Pareto points: {len(pareto)}")
    print(f"Wrote: {out_json}")

if __name__ == "__main__":
    main()
