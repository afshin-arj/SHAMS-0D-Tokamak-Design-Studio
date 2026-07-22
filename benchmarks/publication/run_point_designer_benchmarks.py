"""Point Designer publication benchmark runner (Research vs Reactor).

Goal
----
Produce *publishable*, reproducible benchmark tables for Point Designer without
changing physics.

What it does
------------
- Loads named benchmark cases (either explicit PointInputs dicts, or reference
  presets from src.models.reference_machines).
- Runs the frozen evaluator (src.physics.hot_ion.hot_ion_point).
- Evaluates constraints (src.constraints.constraints.evaluate_constraints).
- Applies the *same Design Intent policy* used by the UI (q95 hard in both;
  several engineering/plant constraints become diagnostic-only in Research;
  TBR ignored in Research).
- Writes:
    * CSV table for publication
    * Per-case JSON artifacts (inputs/outputs/constraint ledger)

Usage
-----
python benchmarks/publication/run_point_designer_benchmarks.py \
  --cases benchmarks/publication/cases_point_designer.json \
  --outdir benchmarks/publication/out

You can also run built-in reference presets:
python benchmarks/publication/run_point_designer_benchmarks.py --use-reference-presets

Notes
-----
- The default cases shipped here are *inspired presets* (qualitative). For a
  paper, replace with your cited parameter tables.
- This runner is intentionally conservative and deterministic.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Make src importable when run from repo root
import sys
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from models.inputs import PointInputs
try:
    from evaluator.core import Evaluator
except Exception:
    from src.evaluator.core import Evaluator  # type: ignore
try:
    from ui_nicegui.lib.pd_intent_policy import classify_failed_constraints as _ui_classify
except Exception:
    _ui_classify = None  # type: ignore
from physics.hot_ion import hot_ion_point
from constraints.constraints import evaluate_constraints
from models.reference_machines import reference_presets
from provenance.authority import authority_snapshot_from_outputs
from provenance.confidence import authority_confidence_from_artifact
from decision.constraint_ledger import build_constraint_ledger


# -----------------------------
# Design Intent policy (must match ui/app.py)
# -----------------------------
_INTENT_HARD = {
    "reactor": {"q95", "q_div", "P_SOL/R", "sigma_vm", "B_peak", "HTS margin", "TBR", "NWL"},
    "research": {"q95"},
}
_INTENT_SOFT = {
    "reactor": set(),
    "research": {"q_div", "P_SOL/R", "sigma_vm", "B_peak", "HTS margin", "NWL"},
}
_INTENT_IGNORE = {
    "reactor": set(),
    "research": {"TBR"},
}

DEFAULT_BASE = {
    # Minimal baseline required to construct PointInputs (safe defaults).
    # These are *not* a claim of any specific machine; they simply prevent missing-field crashes.
    "R0_m": 1.85,
    "a_m": 0.57,
    "kappa": 1.75,
    "Bt_T": 12.2,
    "Ip_MA": 8.7,
    "Ti_keV": 10.0,
    "fG": 0.85,
    "Paux_MW": 25.0,
    # Common sensible defaults used throughout the codebase
    "delta": 0.0,
    "zeff": 1.8,
    "dilution_fuel": 0.85,
    "include_radiation": True,
    "radiation_model": "fractional",
    "f_rad_core": 0.2,
    "steady_state": True,
}


def _intent_key(design_intent: str) -> str:
    s = str(design_intent or "").strip().lower()
    if s.startswith("experimental") or s.startswith("research") or ("research" in s):
        return "research"
    return "reactor"

def _safe_filename(stem: str, *, max_len: int = 120) -> str:
    """Make a filesystem-safe filename stem (Windows-safe).

    Notes
    -----
    Windows invalid characters: <>:"/\\|?* plus ASCII control chars (0x00-0x1F).
    Windows also forbids reserved device names (CON, PRN, AUX, NUL, COM1.., LPT1..),
    and trailing dots/spaces. We also proactively cap length to reduce MAX_PATH issues.
    """
    raw = str(stem or "")
    # Normalize separators early
    s = raw.replace("/", "_").replace("\\", "_")
    # Remove characters invalid on Windows and control chars
    s = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "_", s)
    # Collapse repeats
    s = re.sub(r"_+", "_", s).strip(" _")
    # Windows does not allow trailing dots/spaces
    s = s.rstrip(" .")
    if not s:
        s = "case"

    # Reserved device names (case-insensitive)
    base = s.split(".")[0].upper()
    reserved = {"CON","PRN","AUX","NUL", *{f"COM{i}" for i in range(1,10)}, *{f"LPT{i}" for i in range(1,10)}}
    if base in reserved:
        s = f"_{s}"

    # Length cap: if we must truncate, append a short hash to keep uniqueness stable
    if len(s) > max_len:
        h = hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:8]
        keep = max(1, max_len - 9)  # 1 for "_" + 8 for hash
        s = (s[:keep].rstrip(" ._") + "_" + h).rstrip(" .")

    return s




def _stable_hash(obj: Any) -> str:
    b = json.dumps(obj, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(b).hexdigest()[:16]


def _safe_float(x: Any) -> float:
    try:
        v = float(x)
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return float("nan")


def _constraint_passed(c: Any) -> bool:
    """True if constraint passed (GovernanceConstraint uses `.passed`, not `.ok`)."""
    if hasattr(c, "passed"):
        return bool(getattr(c, "passed"))
    if isinstance(c, dict):
        if "passed" in c:
            return bool(c.get("passed"))
        if "failed" in c:
            return not bool(c.get("failed"))
        if "ok" in c:
            return bool(c.get("ok"))
    return True


def _constraint_as_dict(c: Any) -> Dict[str, Any]:
    if hasattr(c, "as_dict") and callable(getattr(c, "as_dict")):
        return dict(c.as_dict())
    if isinstance(c, dict):
        return dict(c)
    try:
        d = asdict(c)
        d.setdefault("passed", _constraint_passed(c))
        d.setdefault("failed", not _constraint_passed(c))
        if hasattr(c, "margin"):
            d.setdefault("margin", getattr(c, "margin"))
        return d
    except Exception:
        return {"name": str(getattr(c, "name", "")), "passed": _constraint_passed(c)}


def _classify_failures(failed_names: List[str], *, intent: str) -> Dict[str, List[str]]:
    """Match Point Designer / ui_nicegui intent policy (Reactor: any non-ignored fail is blocking)."""
    if _ui_classify is not None:
        return _ui_classify(failed_names, design_intent=intent)
    hard = set(_INTENT_HARD.get(intent, set()))
    soft = set(_INTENT_SOFT.get(intent, set()))
    ign = set(_INTENT_IGNORE.get(intent, set()))
    blocking: List[str] = []
    diagnostic: List[str] = []
    ignored: List[str] = []
    for name in failed_names or []:
        nm = str(name)
        if nm in ign:
            ignored.append(nm)
        elif nm in soft:
            diagnostic.append(nm)
        elif nm in hard or intent == "reactor":
            blocking.append(nm)
        else:
            diagnostic.append(nm)
    return {"blocking": blocking, "diagnostic": diagnostic, "ignored": ignored}


def _tightest(constraints, *, hard_set: set[str], n: int = 3) -> List[Tuple[str, float]]:
    rows = []
    for c in constraints:
        try:
            name = str(getattr(c, "name", "") if not isinstance(c, dict) else c.get("name", ""))
            margin = _safe_float(getattr(c, "margin", None) if not isinstance(c, dict) else c.get("margin"))
            ok = _constraint_passed(c)
        except Exception:
            continue
        if name in hard_set:
            # We sort by margin ascending (most negative / tightest first)
            rows.append((name, margin, ok))
    rows.sort(key=lambda t: (t[1], 0 if not t[2] else 1))
    out = [(nm, m) for (nm, m, _ok) in rows[:n]]
    return out


def _build_inputs(d: Dict[str, Any], *, base: PointInputs | None = None) -> PointInputs:
    """Build PointInputs from a dict, with safe defaults.

    If `base` is provided, `d` overrides it. Otherwise we start from DEFAULT_BASE.
    Only keys that exist on PointInputs are applied (robust to refactors).
    """
    base = base or PointInputs(**DEFAULT_BASE)
    allowed = set(base.__dict__.keys())
    clean = {k: v for k, v in (d or {}).items() if k in allowed}
    merged = base.__dict__.copy()
    merged.update(clean)
    return PointInputs(**merged)


def run_one(case_id: str, inp: PointInputs, *, design_intent: str) -> Dict[str, Any]:
    intent = _intent_key(design_intent)

    # Prefer Evaluator choke point (calibration + model cards); fall back to hot_ion_point.
    try:
        evr = Evaluator(label="publication_benchmark", cache_enabled=False).evaluate(inp)
        if not evr.ok or not isinstance(evr.out, dict):
            out = hot_ion_point(inp)
        else:
            out = evr.out
    except Exception:
        out = hot_ion_point(inp)
    cons = evaluate_constraints(out)

    failed = [str(getattr(c, "name", "")) for c in cons if not _constraint_passed(c)]
    classified = _classify_failures(failed, intent=intent)

    hard_set = set(_INTENT_HARD.get(intent, set()))
    tight = _tightest(cons, hard_set=hard_set, n=5)

    row = {
        "case_id": case_id,
        "design_intent": design_intent,
        "intent_key": intent,
        "inputs_hash": _stable_hash(inp.__dict__),
        "ok_blocking": (len(classified["blocking"]) == 0),
        "failed_blocking": ";".join(classified["blocking"]),
        "failed_diagnostic": ";".join(classified["diagnostic"]),
        "failed_ignored": ";".join(classified["ignored"]),
        # Core outputs (stable keys used throughout SHAMS)
        "R0_m": _safe_float(out.get("R0_m")),
        "a_m": _safe_float(out.get("a_m")),
        "Bt_T": _safe_float(out.get("Bt_T")),
        "Ip_MA": _safe_float(out.get("Ip_MA")),
        "fG": _safe_float(out.get("fG")),
        "Ti_keV": _safe_float(out.get("Ti_keV")),
        "H98": _safe_float(out.get("H98")),
        "Q_DT_eqv": _safe_float(out.get("Q_DT_eqv")),
        "P_fus_MW": _safe_float(out.get("P_fus_MW", out.get("Pfus_DT_MW"))),
        "P_e_net_MW": _safe_float(out.get("P_e_net_MW", out.get("P_net_e_MW"))),
        "q95": _safe_float(out.get("q95", out.get("q95_proxy"))),
        # Non-authoritative cross-check (PROCESS-style relation)
        "Ip_from_q95_PROCESS_MA": _safe_float(out.get("Ip_from_q95_PROCESS_MA")),
        "Ip_vs_PROCESS_ratio": _safe_float(out.get("Ip_vs_PROCESS_ratio")),
        "betaN": _safe_float(out.get("betaN", out.get("betaN_proxy"))),
        "q_div_MW_m2": _safe_float(out.get("q_div_MW_m2")),
        "sigma_vm_MPa": _safe_float(out.get("sigma_vm_MPa", out.get("sigma_hoop_MPa"))),
        "B_peak_T": _safe_float(out.get("B_peak_T")),
        "hts_margin": _safe_float(out.get("hts_margin")),
        "TBR": _safe_float(out.get("TBR")),
        "tightest_hard": ";".join([f"{nm}:{m:.3g}" for (nm, m) in tight]),
    }

    # PHYS-KPI-001: paper-facing CSV must not present claim KPIs as achievements on FAIL.
    if not row["ok_blocking"]:
        for _claim_k in ("H98", "Q_DT_eqv", "P_fus_MW", "P_e_net_MW"):
            if _claim_k in row:
                row[_claim_k] = "— (diagnostic)"

    artifact = {
        "schema_version": "publication_point_benchmark_v1",
        "case_id": case_id,
        "design_intent": design_intent,
        "intent_key": intent,
        "inputs": inp.__dict__,
        "outputs": out,
        "constraints": [_constraint_as_dict(c) for c in cons],
        "classification": classified,
        "tightest_hard": [{"name": nm, "margin": m} for (nm, m) in tight],
    }

    # v256.0: add authority snapshot + confidence trust ledger (deterministic; does not change physics)
    try:
        artifact["constraint_ledger"] = build_constraint_ledger(artifact.get("constraints") or [])
    except Exception:
        artifact["constraint_ledger"] = {"schema_version": "constraint_ledger.v1", "entries": [], "top_blockers": []}

    try:
        artifact["authority_contracts"] = authority_snapshot_from_outputs(out if isinstance(out, dict) else {})
    except Exception:
        artifact["authority_contracts"] = {"schema_version": "authority_contracts.v1", "subsystems": {}}

    try:
        artifact["authority_confidence"] = authority_confidence_from_artifact(artifact)
        # light row visibility for tables (no new columns unless desired)
        row["design_confidence"] = str((artifact.get("authority_confidence") or {}).get("design", {}).get("design_confidence_class", "UNKNOWN"))
    except Exception:
        artifact["authority_confidence"] = {"schema_version": "authority_confidence.v1", "design": {"design_confidence_class": "UNKNOWN"}, "subsystems": {}}
        row["design_confidence"] = "UNKNOWN"

    return {"row": row, "artifact": artifact}


def load_cases(path: Path) -> List[Dict[str, Any]]:
    """Load cases from JSON.

    Supported shapes:
    - ``{"include": ["sibling.json", ...]}`` — merge cases from sibling files
    - ``{"cases": [...]}`` — list under ``cases``
    - a bare list of case dicts
    - a mapping of ``case_id -> case`` (optional README key ignored)
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        includes = data.get("include") or []
        if includes:
            cases: List[Dict[str, Any]] = []
            seen: set[str] = set()
            for rel in includes:
                child = (path.parent / str(rel)).resolve()
                for c in load_cases(child):
                    cid = str(c.get("case_id") or c.get("id") or c.get("name") or "")
                    if cid and cid in seen:
                        continue
                    if cid:
                        seen.add(cid)
                    cases.append(c)
            return cases
        if "cases" in data:
            return list(data["cases"])
    if isinstance(data, list):
        return data
    # Mapping of case_id -> case (common for hand-edited JSON),
    # ignoring an optional README key.
    if isinstance(data, dict):
        cases = []
        for k, v in data.items():
            if str(k).strip().upper() == "README":
                continue
            if str(k).strip().lower() == "include":
                continue
            if isinstance(v, dict):
                vv = dict(v)
                vv.setdefault("case_id", str(k))
                # Allow authors to ship templates without running them by default.
                vv.setdefault("enabled", True)
                cases.append(vv)
        if cases:
            return cases

    raise ValueError(
        "Cases file must be a list, a dict with key 'cases' or 'include', "
        "or a mapping of case_id -> case."
    )


def run_publication_pack(
    *,
    cases: List[Dict[str, Any]],
    outdir: Path,
    also_run_opposite_intent: bool = False,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
) -> Dict[str, Any]:
    """Run the publication pack in-process; write CSV, artifacts, topology, summary.

    ``progress_cb(case_id, index_1based, n_enabled)`` is invoked before each enabled case.
    Returns a summary dict (also written to ``summary.json``).
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    artdir = outdir / "artifacts"
    artdir.mkdir(parents=True, exist_ok=True)

    enabled = [c for c in cases if bool(c.get("enabled", True))]
    rows: List[Dict[str, Any]] = []
    preset_map = reference_presets()
    n_case_ok = 0
    n_case_fail = 0
    total = len(enabled)

    for i, c in enumerate(enabled, start=1):
        case_id = str(c.get("case_id") or c.get("name") or "case")
        if progress_cb is not None:
            progress_cb(case_id, i, total)
        title = str(c.get("title") or "")
        design_intent = str(c.get("design_intent") or "Power Reactor (net-electric)")
        source = str(c.get("source") or "")
        preset_key = c.get("preset_key")
        try:
            base_pi = None
            if preset_key:
                base_pi = preset_map.get(str(preset_key))
                if base_pi is None:
                    raise KeyError(f"Unknown preset_key: {preset_key}")
            inp = _build_inputs(dict(c.get("inputs") or {}), base=base_pi)

            # Run declared intent
            res = run_one(case_id, inp, design_intent=design_intent)
            # Attach optional metadata for publication traceability.
            if title:
                res["row"]["title"] = title
                res["artifact"]["title"] = title
            if source:
                res["row"]["source"] = source
                res["artifact"]["source"] = source
            tier = str(c.get("tier") or "")
            if tier:
                res["row"]["tier"] = tier
                res["artifact"]["tier"] = tier
            rows.append(res["row"])
            (artdir / f"{_safe_filename(case_id)}.{_intent_key(design_intent)}.json").write_text(
                json.dumps(res["artifact"], indent=2, sort_keys=True), encoding="utf-8"
            )

            # Optionally run the opposite intent (to show policy difference)
            if also_run_opposite_intent:
                opp = (
                    "Experimental Device (research)"
                    if _intent_key(design_intent) == "reactor"
                    else "Power Reactor (net-electric)"
                )
                res2 = run_one(case_id, inp, design_intent=opp)
                if title:
                    res2["row"]["title"] = title
                    res2["artifact"]["title"] = title
                if source:
                    res2["row"]["source"] = source
                    res2["artifact"]["source"] = source
                if tier:
                    res2["row"]["tier"] = tier
                    res2["artifact"]["tier"] = tier
                rows.append(res2["row"])
                (artdir / f"{_safe_filename(case_id)}.{_intent_key(opp)}.json").write_text(
                    json.dumps(res2["artifact"], indent=2, sort_keys=True), encoding="utf-8"
                )
            n_case_ok += 1
        except Exception as e:
            n_case_fail += 1
            rows.append(
                {
                    "case_id": case_id,
                    "title": title,
                    "source": source,
                    "design_intent": design_intent,
                    "intent_key": _intent_key(design_intent),
                    "error": f"{type(e).__name__}: {e}",
                    "ok_blocking": False,
                    "failed_blocking": "runner_error",
                    "failed_diagnostic": "",
                    "failed_ignored": "",
                }
            )

    # Optional: compare to a baseline benchmark table (same schema) and append delta columns.
    baseline_path = Path(__file__).resolve().parent / "baselines" / "point_designer_benchmark_table_baseline_v219_9.csv"
    if rows and baseline_path.exists():
        try:
            with baseline_path.open("r", newline="", encoding="utf-8") as f:
                br = csv.DictReader(f)
                base_map: Dict[str, Dict[str, Any]] = {}
                for rr in br:
                    key = f"{rr.get('case_id','')}.{rr.get('intent_key','')}"
                    base_map[key] = dict(rr)

            delta_cols = [
                "H98", "Q_DT_eqv", "P_fus_MW", "P_e_net_MW",
                "Prad_core_MW", "Prad_line_MW", "Prad_brem_MW", "Prad_sync_MW",
                "P_SOL_MW", "q_div_MW_m2", "betaN",
                "hts_margin", "P_tf_ohmic_MW",
            ]

            def _to_float(x: Any) -> Optional[float]:
                try:
                    if x is None:
                        return None
                    xs = str(x).strip()
                    if xs == "" or xs.lower() in {"n/a", "nan", "none"}:
                        return None
                    return float(xs)
                except Exception:
                    return None

            for r in rows:
                key = f"{r.get('case_id','')}.{r.get('intent_key','')}"
                b = base_map.get(key)
                if not b:
                    continue
                r["baseline_ok_blocking"] = b.get("ok_blocking", "")
                for col in delta_cols:
                    if col in r and col in b:
                        rv = _to_float(r.get(col))
                        bv = _to_float(b.get(col))
                        if rv is None or bv is None:
                            continue
                        r[f"d_{col}"] = rv - bv

            for r in rows:
                r.setdefault("baseline_table", baseline_path.name)
        except Exception:
            # Baseline comparison is optional; never fail the benchmark pack because of it.
            pass

    # Write CSV table
    csv_path = outdir / "point_designer_benchmark_table.csv"
    if rows:
        preferred = [
            "case_id", "title", "source", "tier",
            "design_intent", "intent_key", "inputs_hash",
            "design_confidence",
            "ok_blocking", "failed_blocking", "failed_diagnostic", "failed_ignored",
            "R0_m", "a_m", "Bt_T", "Ip_MA", "fG", "Ti_keV",
            "H98", "Q_DT_eqv", "P_fus_MW", "P_e_net_MW",
            "q95", "Ip_from_q95_PROCESS_MA", "Ip_vs_PROCESS_ratio",
            "betaN", "q_div_MW_m2", "sigma_vm_MPa", "B_peak_T",
            "magnet_technology", "tf_sc_flag", "Tcoil_K", "hts_margin", "P_tf_ohmic_MW",
            "TBR",
            "tightest_hard",
            "error",
        ]
        keys = []
        seen = set()
        for k in preferred:
            if any(k in r for r in rows) and k not in seen:
                keys.append(k)
                seen.add(k)
        for k in sorted({kk for r in rows for kk in r.keys()}):
            if k not in seen:
                keys.append(k)
                seen.add(k)
        fieldnames = keys
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)

    # Write summary JSON + topology fractions for NiceGUI pack view
    n_pass = sum(1 for r in rows if bool(r.get("ok_blocking")))
    n_fail = len(rows) - n_pass
    n_diag = sum(1 for r in rows if str(r.get("failed_diagnostic") or "").strip())
    n_total = max(len(rows), 1)
    topology = {
        "schema": "publication_pack_topology.v1",
        "n_rows": len(rows),
        "n_pass_blocking": n_pass,
        "n_fail_blocking": n_fail,
        "n_with_diagnostics": n_diag,
        "fractions": {
            "pass": float(n_pass) / float(n_total),
            "fail": float(n_fail) / float(n_total),
            "robust": float(
                sum(
                    1
                    for r in rows
                    if bool(r.get("ok_blocking")) and not str(r.get("failed_diagnostic") or "").strip()
                )
            )
            / float(n_total),
            "fragile": float(
                sum(
                    1
                    for r in rows
                    if bool(r.get("ok_blocking")) and str(r.get("failed_diagnostic") or "").strip()
                )
            )
            / float(n_total),
        },
        "dominant_mechanism_hist": {},
    }
    for r in rows:
        fb = str(r.get("failed_blocking") or "").split(";")[0].strip()
        if fb:
            topology["dominant_mechanism_hist"][fb] = int(topology["dominant_mechanism_hist"].get(fb, 0)) + 1
    (outdir / "topology.json").write_text(json.dumps(topology, indent=2, sort_keys=True), encoding="utf-8")

    version = "unknown"
    try:
        version = (Path(__file__).resolve().parents[2] / "VERSION").read_text(encoding="utf-8").strip().splitlines()[0]
    except Exception:
        pass
    summary = {
        "n_rows": len(rows),
        "n_pass_blocking": n_pass,
        "n_fail_blocking": n_fail,
        "n_cases_ok": n_case_ok,
        "n_cases_fail": n_case_fail,
        "n_cases": total,
        "outdir": str(outdir),
        "csv": str(csv_path),
        "topology": str(outdir / "topology.json"),
        "shams_version": version,
        "notes": (
            "Prefer cases_literature.json / cases_for_paper.json for cited geometry claims; "
            "cases_inspired.json is qualitative screening only. "
            "ok_blocking uses GovernanceConstraint.passed under intent hard-set policy. "
            "Constitutional Atlas clause maps are documentation semantics — not this classification."
        ),
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    summary["rows"] = rows
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=str, default=str(Path(__file__).with_name("cases_point_designer.json")))
    ap.add_argument("--outdir", type=str, default=str(Path(__file__).with_name("out")))
    ap.add_argument("--use-reference-presets", action="store_true", help="Use src.models.reference_machines.reference_presets()")
    ap.add_argument("--also-run-opposite-intent", action="store_true", help="Run each case under both Research and Reactor intents")
    args = ap.parse_args()

    if args.use_reference_presets:
        presets = reference_presets()
        cases = []
        for key, pi in presets.items():
            intent = "Experimental Device (research)" if "|RESEARCH|" in key else "Power Reactor (net-electric)"
            cases.append({"case_id": key, "design_intent": intent, "inputs": pi.__dict__})
    else:
        cases = load_cases(Path(args.cases))

    def _cli_progress(case_id: str, i: int, total: int) -> None:
        print(f"[{i}/{total}] {case_id}", flush=True)

    summary = run_publication_pack(
        cases=cases,
        outdir=Path(args.outdir),
        also_run_opposite_intent=bool(args.also_run_opposite_intent),
        progress_cb=_cli_progress,
    )
    print(f"Wrote: {summary['csv']}")
    print(f"Artifacts: {Path(summary['outdir']) / 'artifacts'}")
    return 0 if int(summary.get("n_cases_fail") or 0) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
