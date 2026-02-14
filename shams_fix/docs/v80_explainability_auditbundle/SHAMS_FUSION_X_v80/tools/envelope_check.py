from __future__ import annotations
import argparse, json
from models.inputs import PointInputs
from envelope.points import default_envelope_points
from physics.hot_ion import hot_ion_point
from constraints.system import build_constraints_from_outputs, summarize_constraints

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    args=ap.parse_args()
    with open(args.base,"r",encoding="utf-8") as f:
        base=json.load(f)
    base_inp=PointInputs.sanitize(base)
    pts=default_envelope_points(base_inp)
    reports=[]
    worst=None
    for i,p in enumerate(pts):
        out=hot_ion_point(p)
        cs=build_constraints_from_outputs(out)
        summ=summarize_constraints(cs)
        dom=summ.get("dominant",{})
        rep={"point_index": i, "inputs": p.__dict__, "all_ok": summ.get("all_ok", False), "dominant": dom}
        reports.append(rep)
        if worst is None or (dom.get("residual",0) > worst.get("dominant",{}).get("residual", -1e9)):
            worst=rep
    result={"n_points": len(pts), "points": reports, "worst": worst}
    print(json.dumps(result, indent=2))

if __name__=="__main__":
    main()
