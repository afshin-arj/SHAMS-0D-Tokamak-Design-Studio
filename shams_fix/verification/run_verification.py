"""Requirements + verification harness.

Runs acceptance checks from requirements/SHAMS_REQS.yaml and writes a compliance
report to verification/report.json.

Windows note (important): The UI launches this file in a subprocess. Some user
Python installs used with Streamlit may not include PyYAML even when the main
app runs. We therefore *prefer* YAML (authoritative human-edited source) but
fall back to a committed JSON mirror if PyYAML is unavailable.

Designed to be Windows-safe and CI-friendly.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point


def _load_default_base() -> Dict[str, Any]:
    """Extract DEFAULT_BASE dict from benchmarks/run.py (single source of truth)."""
    p = ROOT / "benchmarks" / "run.py"
    txt = p.read_text(encoding="utf-8")
    # Find the AST assignment to DEFAULT_BASE
    mod = ast.parse(txt)
    for node in mod.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "DEFAULT_BASE" for t in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError("Could not find DEFAULT_BASE in benchmarks/run.py")


def _load_case_inputs(case_name: str, overrides: Dict[str, Any] | None = None) -> PointInputs:
    cases = json.loads((ROOT / "benchmarks" / "cases.json").read_text(encoding="utf-8"))
    if case_name not in cases:
        raise KeyError(f"Unknown case_name: {case_name}")
    base = _load_default_base()
    d = dict(base)
    d.update(cases[case_name])
    if overrides:
        d.update(overrides)
    return PointInputs(**d)


def _eval_case(case_name: str, overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    inp = _load_case_inputs(case_name, overrides=overrides)
    out = hot_ion_point(inp)
    return out


def _compare(op: str, a: float, b: float) -> bool:
    if op == ">=":
        return a >= b
    if op == ">":
        return a > b
    if op == "<=":
        return a <= b
    if op == "<":
        return a < b
    if op in ("==", "="):
        return a == b
    raise ValueError(f"Unsupported op: {op}")


def run() -> Tuple[int, Dict[str, Any]]:
    req_path_yaml = ROOT / "requirements" / "SHAMS_REQS.yaml"
    req_path_json = ROOT / "requirements" / "SHAMS_REQS.json"

    if yaml is not None and req_path_yaml.exists():
        reqs = yaml.safe_load(req_path_yaml.read_text(encoding="utf-8"))
    else:
        if not req_path_json.exists():
            raise RuntimeError(
                "PyYAML not available and requirements/SHAMS_REQS.json is missing. "
                "Install PyYAML or commit the JSON mirror."
            )
        reqs = json.loads(req_path_json.read_text(encoding="utf-8"))
    requirements: List[Dict[str, Any]] = reqs.get("requirements", [])

    results: List[Dict[str, Any]] = []
    overall_ok = True
    started = time.time()

    # Cache a baseline evaluation for checks that need a representative output
    baseline_out: Dict[str, Any] | None = None

    for r in requirements:
        rid = r.get("id", "UNKNOWN")
        acc = r.get("acceptance", {}) or {}
        r_ok = True
        note = ""
        t0 = time.time()

        try:
            typ = acc.get("type")

            if typ == "script_exit_code":
                cmd = acc.get("command")
                exp = int(acc.get("expected_exit_code", 0))
                if not cmd:
                    raise ValueError("Missing command")
                proc = subprocess.run(cmd, shell=True, cwd=str(ROOT))
                r_ok = (proc.returncode == exp)
                if not r_ok:
                    note = f"Exit code {proc.returncode} != expected {exp}"

            elif typ == "output_keys_present":
                keys = acc.get("keys", [])
                if baseline_out is None:
                    baseline_out = _eval_case("sparc_baseline")
                missing = [k for k in keys if k not in baseline_out]
                r_ok = (len(missing) == 0)
                if not r_ok:
                    note = f"Missing keys: {missing}"

            elif typ == "case_check":
                case = acc.get("case_name")
                overrides = acc.get("overrides", None)
                assertion = acc.get("assert", {})
                if not case or "key" not in assertion:
                    raise ValueError("Missing case_name or assert")
                out = _eval_case(case, overrides=overrides)
                key = assertion["key"]
                op = assertion.get("op", ">=")
                val = float(assertion.get("value", 0.0))
                got = float(out.get(key, float("nan")))
                r_ok = _compare(op, got, val)
                if not r_ok:
                    note = f"{key}={got} not {op} {val}"

            elif typ == "model_cards_present":
                ids = acc.get("ids", [])
                if baseline_out is None:
                    baseline_out = _eval_case("sparc_baseline")
                mc = baseline_out.get("model_cards", {}) or {}
                missing = [mid for mid in ids if mid not in mc]
                r_ok = (len(missing) == 0)
                if not r_ok:
                    note = f"Missing model card ids: {missing}"

            else:
                raise ValueError(f"Unknown acceptance type: {typ}")

        except Exception as e:
            r_ok = False
            note = f"Exception: {e}"

        dt = time.time() - t0
        results.append({
            "id": rid,
            "title": r.get("title", ""),
            "ok": bool(r_ok),
            "seconds": dt,
            "model_cards": r.get("model_cards", []),
            "note": note,
        })
        overall_ok = overall_ok and bool(r_ok)

    elapsed = time.time() - started

    # Include a snapshot of baseline model card index if available
    baseline_model_cards = {}
    if baseline_out is None:
        try:
            baseline_out = _eval_case("sparc_baseline")
        except Exception:
            baseline_out = None
    if baseline_out is not None:
        baseline_model_cards = baseline_out.get("model_cards", {}) or {}

    report = {
        "schema_version": 1,
        "project": reqs.get("project", "SHAMS–FUSION-X"),
        "ran_unix": time.time(),
        "elapsed_s": elapsed,
        "overall_ok": bool(overall_ok),
        "requirements": results,
        "baseline_model_cards": baseline_model_cards,
    }
    return (0 if overall_ok else 2), report


if __name__ == "__main__":
    code, report = run()
    out_path = ROOT / "verification" / "report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    sys.exit(code)
