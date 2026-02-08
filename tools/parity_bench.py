from __future__ import annotations

"""Parity benchmarks (PROCESS Parity Layer v1).

These benchmarks are *internal regression tests* for the parity layer. They are
not intended to validate absolute real-world plant economics; they validate:

* the parity functions run end-to-end
* keys are present and finite when expected
* outputs remain stable unless intentionally changed
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from src.models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from src.parity import parity_plant_closure, parity_magnets, parity_cryo, parity_costing


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_parity_cases() -> List[Dict[str, Any]]:
    p = _repo_root() / "benchmarks" / "parity_v1_cases.json"
    return json.loads(p.read_text(encoding="utf-8"))


def run_parity_benchmarks(update_golden: bool = False) -> Dict[str, Any]:
    cases = load_parity_cases()
    out_rows: List[Dict[str, Any]] = []
    for c in cases:
        name = str(c.get("name"))
        in_dict = dict(c.get("inputs") or {})
        pi = PointInputs(**in_dict)
        outputs = hot_ion_point(pi)
        parity = {
            "plant": parity_plant_closure(pi, outputs),
            "magnets": parity_magnets(pi, outputs),
            "cryo": parity_cryo(pi, outputs),
            "costing": parity_costing(pi, outputs),
        }
        # Minimal, stable subset for golden comparisons
        derived = {
            "P_e_net_MW": parity["plant"]["derived"]["P_e_net_MW"],
            "Qe": parity["plant"]["derived"]["Qe"],
            "CAPEX_MUSD": parity["costing"]["derived"]["CAPEX_MUSD"],
            "LCOE_USD_per_MWh": parity["costing"]["derived"].get("LCOE_USD_per_MWh"),
        }
        out_rows.append({"name": name, "derived": derived})

    golden_path = _repo_root() / "benchmarks" / "parity_v1_golden.json"
    if update_golden:
        golden_path.write_text(json.dumps(out_rows, indent=2), encoding="utf-8")
        return {"ok": True, "updated_golden": True, "n": len(out_rows)}

    if not golden_path.exists():
        return {"ok": False, "reason": "missing_golden", "n": len(out_rows), "golden_path": str(golden_path)}
    golden = json.loads(golden_path.read_text(encoding="utf-8"))

    # Compare with tolerances
    tol_rel = 1e-6
    diffs = []
    gmap = {r["name"]: r["derived"] for r in golden}
    for r in out_rows:
        nm = r["name"]
        if nm not in gmap:
            diffs.append({"name": nm, "missing_in_golden": True})
            continue
        for k, v in r["derived"].items():
            gv = gmap[nm].get(k)
            if gv is None and v is None:
                continue
            try:
                v = float(v)
                gv = float(gv)
            except Exception:
                if v != gv:
                    diffs.append({"name": nm, "key": k, "golden": gv, "new": v})
                continue
            denom = max(abs(gv), 1e-9)
            rel = abs(v - gv) / denom
            if rel > tol_rel:
                diffs.append({"name": nm, "key": k, "golden": gv, "new": v, "rel": rel})

    return {"ok": len(diffs) == 0, "n": len(out_rows), "diffs": diffs}
