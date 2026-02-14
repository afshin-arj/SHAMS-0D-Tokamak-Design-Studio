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
from typing import Any, Dict, List, Tuple

# Make src importable when run from repo root
import sys
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from models.inputs import PointInputs
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


def _classify_failures(failed_names: List[str], *, intent: str) -> Dict[str, List[str]]:
    hard = set(_INTENT_HARD.get(intent, set()))
    ign = set(_INTENT_IGNORE.get(intent, set()))
    blocking = [c for c in failed_names if c in hard]
    ignored = [c for c in failed_names if c in ign]
    diagnostic = [c for c in failed_names if (c not in blocking and c not in ignored)]
    return {"blocking": blocking, "diagnostic": diagnostic, "ignored": ignored}


def _tightest(constraints, *, hard_set: set[str], n: int = 3) -> List[Tuple[str, float]]:
    rows = []
    for c in constraints:
        try:
            name = str(getattr(c, "name", ""))
            margin = _safe_float(getattr(c, "margin", None))
            ok = bool(getattr(c, "ok", True))
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

    out = hot_ion_point(inp)
    cons = evaluate_constraints(out)

    failed = [str(getattr(c, "name", "")) for c in cons if not bool(getattr(c, "ok", True))]
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

    artifact = {
        "schema_version": "publication_point_benchmark_v1",
        "case_id": case_id,
        "design_intent": design_intent,
        "intent_key": intent,
        "inputs": inp.__dict__,
        "outputs": out,
        "constraints": [asdict(c) for c in cons],
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
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "cases" in data:
        return list(data["cases"])
    if isinstance(data, list):
        return data
    # Also accept a mapping of case_id -> case (common for hand-edited JSON),
    # ignoring an optional README key.
    if isinstance(data, dict):
        cases = []
        for k, v in data.items():
            if str(k).strip().upper() == "README":
                continue
            if isinstance(v, dict):
                vv = dict(v)
                vv.setdefault("case_id", str(k))
                # Allow authors to ship templates without running them by default.
                # This keeps the benchmark pack rich without forcing incomplete cases.
                vv.setdefault("enabled", True)
                cases.append(vv)
        if cases:
            return cases

    raise ValueError("Cases file must be a list, a dict with key 'cases', or a mapping of case_id -> case.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=str, default=str(Path(__file__).with_name("cases_point_designer.json")))
    ap.add_argument("--outdir", type=str, default=str(Path(__file__).with_name("out")))
    ap.add_argument("--use-reference-presets", action="store_true", help="Use src.models.reference_machines.reference_presets()")
    ap.add_argument("--also-run-opposite-intent", action="store_true", help="Run each case under both Research and Reactor intents")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    artdir = outdir / "artifacts"
    artdir.mkdir(parents=True, exist_ok=True)

    cases: List[Dict[str, Any]] = []
    if args.use_reference_presets:
        presets = reference_presets()
        for key, pi in presets.items():
            # Infer intent from canonical key REF|RESEARCH|... vs REF|REACTOR|...
            intent = "Experimental Device (research)" if "|RESEARCH|" in key else "Power Reactor (net-electric)"
            cases.append({"case_id": key, "design_intent": intent, "inputs": pi.__dict__})
    else:
        cases = load_cases(Path(args.cases))

    rows: List[Dict[str, Any]] = []
    preset_map = reference_presets()

    for c in cases:
        if not bool(c.get("enabled", True)):
            continue
        case_id = str(c.get("case_id") or c.get("name") or "case")
        title = str(c.get("title") or "")
        design_intent = str(c.get("design_intent") or "Power Reactor (net-electric)")
        source = str(c.get("source") or "")
        preset_key = c.get("preset_key")
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
        rows.append(res["row"])
        (artdir / f"{_safe_filename(case_id)}.{_intent_key(design_intent)}.json").write_text(
            json.dumps(res["artifact"], indent=2, sort_keys=True), encoding="utf-8"
        )

        # Optionally run the opposite intent (to show policy difference)
        if args.also_run_opposite_intent:
            opp = "Experimental Device (research)" if _intent_key(design_intent) == "reactor" else "Power Reactor (net-electric)"
            res2 = run_one(case_id, inp, design_intent=opp)
            rows.append(res2["row"])
            (artdir / f"{_safe_filename(case_id)}.{_intent_key(opp)}.json").write_text(
                json.dumps(res2["artifact"], indent=2, sort_keys=True), encoding="utf-8"
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

            # Define a small set of numeric channels worth tracking as deltas.
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
                # Verdict delta
                r["baseline_ok_blocking"] = b.get("ok_blocking", "")
                # Numeric deltas
                for c in delta_cols:
                    if c in r and c in b:
                        rv = _to_float(r.get(c))
                        bv = _to_float(b.get(c))
                        if rv is None or bv is None:
                            continue
                        r[f"d_{c}"] = rv - bv

            # Record baseline provenance in summary.json later via an extra row key.
            for r in rows:
                r.setdefault("baseline_table", baseline_path.name)
        except Exception:
            # Baseline comparison is optional; never fail the benchmark pack because of it.
            pass

    # Write CSV table
    csv_path = outdir / "point_designer_benchmark_table.csv"
    if rows:
        # Union of keys across rows (some cases include extra metadata such as `source`).
        # Keep a stable, publication-friendly ordering.
        preferred = [
            "case_id", "title", "source",
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
        ]
        keys = []
        seen = set()
        for k in preferred:
            if any(k in r for r in rows) and k not in seen:
                keys.append(k); seen.add(k)
        # Append any remaining keys deterministically
        for k in sorted({kk for r in rows for kk in r.keys()}):
            if k not in seen:
                keys.append(k); seen.add(k)
        fieldnames = keys
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)

    # Write summary JSON
    summary = {
        "n_rows": len(rows),
        "outdir": str(outdir),
        "csv": str(csv_path),
        "notes": "Replace inspired presets with cited parameter tables for publication.",
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Wrote: {csv_path}")
    print(f"Artifacts: {artdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())