from __future__ import annotations
import json
from dataclasses import replace
from pathlib import Path

from models.inputs import PointInputs
from solvers.point_solver import evaluate_point

def sweep(base: PointInputs, field: str, values):
    rows=[]
    for v in values:
        inp = replace(base, **{field: float(v)})
        out = evaluate_point(inp)
        rows.append({"x": float(v), **{k: out.get(k) for k in ["Q", "Pfus_MW", "P_e_net_MW", "q_div_MW_m2", "H98"]}, "feasible": out.get("feasible", True)})
    return rows

def main():
    # Small PROCESS-style trend check (qualitative, not numeric matching).
    base = PointInputs(R0_m=1.85, a_m=0.55, kappa=1.8, Bt_T=12.2, Ip_MA=8.7, Ti_keV=15.0, fG=0.85, Paux_MW=25.0)
    rows = sweep(base, "Bt_T", [10, 11, 12, 13, 14])
    Path("trend_Bt.json").write_text(json.dumps(rows, indent=2))
    print("Wrote trend_Bt.json")

if __name__ == "__main__":
    main()
