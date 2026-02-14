"""Topology regression check (deterministic).

Computes a small coarse feasibility slice around DEFAULT_BASE and compares key
metrics to a committed baseline file.

This is CI-grade: it detects unintended drift in feasibility topology, not just
single-point regressions.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import numpy as np  # type: ignore

from evaluator.core import Evaluator
from models.inputs import PointInputs
from constraints.constraints import evaluate_constraints


def _load_default_base() -> Dict[str, Any]:
    import ast
    p = ROOT / "benchmarks" / "run.py"
    tree = ast.parse(p.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "DEFAULT_BASE":
                    return ast.literal_eval(node.value)
    raise RuntimeError("DEFAULT_BASE not found")


def compute_metrics() -> Dict[str, Any]:
    base = _load_default_base()
    ev = Evaluator()
    R0c = float(base["R0_m"])
    Btc = float(base["Bt_T"])
    R0s = np.linspace(R0c * 0.9, R0c * 1.1, 11)
    Bts = np.linspace(Btc * 0.9, Btc * 1.1, 11)

    n = 0
    n_pass = 0
    mech_counts: Dict[str, int] = {}

    for R0 in R0s:
        for Bt in Bts:
            d = dict(base)
            d["R0_m"] = float(R0)
            d["Bt_T"] = float(Bt)
            inp = PointInputs(**d)
            out = ev.evaluate(inp).out or {}
            cs = evaluate_constraints(out)
            hard = [c for c in cs if str(getattr(c, "severity", "hard")).lower() == "hard"]
            ok = all(bool(getattr(c, "passed", False)) for c in hard)
            n += 1
            if ok:
                n_pass += 1
            else:
                worst = 1e9
                mech = "GENERAL"
                for c in hard:
                    if bool(getattr(c, "passed", False)):
                        continue
                    mm = float(getattr(c, "margin", float("nan")))
                    if math.isfinite(mm) and mm < worst:
                        worst = mm
                        mech = str(getattr(c, "mechanism_group", "GENERAL") or "GENERAL")
                mech_counts[mech] = mech_counts.get(mech, 0) + 1

    return {
        "grid": {"R0_m": [float(R0s[0]), float(R0s[-1]), len(R0s)], "Bt_T": [float(Bts[0]), float(Bts[-1]), len(Bts)]},
        "n_points": int(n),
        "pass_frac": float(n_pass / n) if n else float("nan"),
        "fail_frac": float(1.0 - (n_pass / n)) if n else float("nan"),
        "dominant_mechanism_fail_counts": mech_counts,
    }


def main() -> int:
    baseline_path = ROOT / "verification" / "topology_baseline.json"
    if not baseline_path.exists():
        print(f"Missing baseline: {baseline_path}")
        return 2
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    cur = compute_metrics()

    # tolerances (tight but not absurd)
    tol_frac = 0.02

    ok = True
    bpf = float(baseline.get("pass_frac", float("nan")))
    cpf = float(cur.get("pass_frac", float("nan")))
    if (not math.isfinite(bpf)) or (not math.isfinite(cpf)) or abs(cpf - bpf) > tol_frac:
        ok = False
        print(f"pass_frac drift: baseline={bpf:.4g} current={cpf:.4g} tol={tol_frac}")

    # mechanism distribution: compare normalized top-1 mechanism
    bmc = baseline.get("dominant_mechanism_fail_counts", {}) or {}
    cmc = cur.get("dominant_mechanism_fail_counts", {}) or {}
    def top_mech(d: Dict[str, Any]) -> str:
        best = ("", -1)
        for k,v in d.items():
            try:
                vv = int(v)
            except Exception:
                vv = 0
            if vv > best[1]:
                best = (str(k), vv)
        return best[0] or "GENERAL"
    if top_mech(bmc) != top_mech(cmc):
        ok = False
        print(f"dominant fail mechanism changed: baseline={top_mech(bmc)} current={top_mech(cmc)}")

    out_path = ROOT / "verification" / "topology_regression_report.json"
    out_path.write_text(json.dumps({"ok": ok, "baseline": baseline, "current": cur}, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
