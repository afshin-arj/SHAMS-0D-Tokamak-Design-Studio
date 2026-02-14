from __future__ import annotations

"""PROCESS Parity Layer v2: benchmark calibration runner.

This is a *UI helper* (and lightweight regression primitive) that:

* Evaluates built-in parity cases
* Computes parity bundle (plant/magnets/cryo/costing)
* Compares against a reference table with tolerances

References are expected in `benchmarks/parity_v2_refs.json` or user-provided.

Note: Reference values are user/program dependent; the built-in file ships with
placeholders. The purpose is to make calibration **easy and explicit**, not to
claim universal truth.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from src.parity.calibration import compute_parity_bundle, compare_to_reference


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_refs(path: Optional[str] = None) -> List[Dict[str, Any]]:
    p = Path(path) if path else (_repo_root() / "benchmarks" / "parity_v2_refs.json")
    return json.loads(p.read_text(encoding="utf-8"))


def load_cases() -> List[Dict[str, Any]]:
    p = _repo_root() / "benchmarks" / "parity_v1_cases.json"
    return json.loads(p.read_text(encoding="utf-8"))


def run_parity_calibration(refs_path: Optional[str] = None) -> Dict[str, Any]:
    cases = load_cases()
    refs = load_refs(refs_path)
    ref_map = {str(r.get("name")): r for r in refs}

    results: List[Dict[str, Any]] = []
    for c in cases:
        name = str(c.get("name"))
        if name not in ref_map:
            # skip cases with no reference
            continue
        pi = PointInputs(**(c.get("inputs") or {}))
        outputs = hot_ion_point(pi)
        parity = compute_parity_bundle(pi, outputs)
        r = ref_map[name]
        rows = compare_to_reference(
            parity=parity,
            reference=dict(r.get("reference") or {}),
            tolerances=dict(r.get("tolerances") or {}),
        )
        ok = all(bool(x.get("ok")) for x in rows) if rows else True
        results.append({"name": name, "ok": ok, "rows": rows, "notes": r.get("notes")})

    overall_ok = all(bool(r.get("ok")) for r in results) if results else False
    return {
        "ok": overall_ok,
        "n_cases": len(results),
        "refs_path": refs_path or "benchmarks/parity_v2_refs.json",
        "results": results,
        "note": "Calibration is reference-dependent. Built-in references are placeholders; upload your program's reference file.",
    }
