from __future__ import annotations
"""
Feasibility Boundary Atlas:
Extracts feasibility cliffs and boundary points from feasible scans.
"""
import argparse, json, os

def main():
    ap = argparse.ArgumentParser(description="Feasibility Boundary Atlas generator")
    ap.add_argument("--feasible-scan-json", required=True)
    ap.add_argument("--out", default="boundary_atlas.json")
    args = ap.parse_args()

    with open(args.feasible_scan_json) as f:
        data = json.load(f)

    pts = data["points"]
    pts = sorted(pts, key=lambda p: p.get("x", 0.0))

    boundaries = []
    for i in range(len(pts)-1):
        if pts[i]["feasible"] and not pts[i+1]["feasible"]:
            boundaries.append({
                "x_feasible": pts[i]["x"],
                "x_infeasible": pts[i+1]["x"],
                "limiting_constraints": pts[i+1].get("active_constraints", [])
            })

    atlas = {
        "kind": "feasibility_boundary_atlas",
        "var": data.get("meta", {}).get("var"),
        "boundaries": boundaries
    }

    with open(args.out, "w") as f:
        json.dump(atlas, f, indent=2)

    print(f"Wrote boundary atlas: {args.out}")

if __name__ == "__main__":
    main()
