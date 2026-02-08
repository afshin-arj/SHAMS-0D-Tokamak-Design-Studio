from __future__ import annotations

"""Optimization Sandbox — Persistence utilities (opt-in).

Tier-2 upgrade: Active learning across runs.

Design discipline
-----------------
- Frozen evaluator is the only truth.
- Persistence is additive only: caches *evaluated* candidates and compact run capsules.
- Cache is local to the SHAMS working directory in `.shams_state/`.
- If cache is removed, nothing breaks.

Stored artifacts
----------------
- `.shams_state/opt_sandbox/evals.jsonl` — evaluated candidates (minimal).
- `.shams_state/opt_sandbox/runs/<run_id>.json` — compact run capsule.

The cache is intentionally small and schema-stable.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json
import hashlib
import time


def state_dir(root: Optional[Path] = None) -> Path:
    root = Path(root) if root else Path.cwd()
    d = root / ".shams_state" / "opt_sandbox"
    d.mkdir(parents=True, exist_ok=True)
    (d / "runs").mkdir(parents=True, exist_ok=True)
    return d


def _sha256_json(obj: Any) -> str:
    try:
        raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except Exception:
        raw = repr(obj).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def evaluation_fingerprint(inp: Dict[str, Any], intent: str) -> str:
    """Stable fingerprint for an evaluation request (inputs + intent)."""
    return _sha256_json({"intent": str(intent), "inputs": dict(inp)})


def load_cached_evals(limit: int = 50000, root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load cached evaluations (most recent last)."""
    p = state_dir(root) / "evals.jsonl"
    if not p.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    if len(out) > limit:
        out = out[-limit:]
    return out


def append_cached_evals(evals: Iterable[Dict[str, Any]], root: Optional[Path] = None) -> int:
    """Append minimal evaluation records to cache. Returns number written."""
    p = state_dir(root) / "evals.jsonl"
    n = 0
    with p.open("a", encoding="utf-8") as f:
        for e in evals:
            try:
                f.write(json.dumps(e, sort_keys=True) + "\n")
                n += 1
            except Exception:
                continue
    return n


def compact_eval_record(res: Dict[str, Any], intent: str) -> Dict[str, Any]:
    """Store a compact, schema-stable record for warm-starting."""
    inp = dict(res.get("inputs") or {})
    out = {
        "ts": int(time.time()),
        "intent": str(intent),
        "fingerprint": evaluation_fingerprint(inp, intent),
        "inputs": inp,
        "feasible": bool(res.get("feasible", False)),
        "min_signed_margin": res.get("min_signed_margin"),
        "failure_mode": res.get("failure_mode"),
        "active_constraints": list(res.get("active_constraints") or [])[:5],
        "score": res.get("_score"),
        "violation": res.get("_violation"),
    }
    # cost proxies (optional)
    if isinstance(res.get("cost"), dict):
        out["cost"] = res.get("cost")
    return out


@dataclass
class RunCapsule:
    run_id: str
    created_ts: int
    intent: str
    settings_hash: str
    evaluator_hash: str
    summary: Dict[str, Any]
    archive_sample: List[Dict[str, Any]]


def save_run_capsule(
    run: Dict[str, Any],
    *,
    run_id: str,
    settings: Dict[str, Any],
    evaluator_hash: str,
    root: Optional[Path] = None,
    archive_sample_n: int = 80,
) -> Path:
    d = state_dir(root) / "runs"
    capsule = {
        "schema": "shams.opt_sandbox.run_capsule.v1",
        "run_id": str(run_id),
        "created_ts": int(time.time()),
        "intent": str(run.get("intent", "")),
        "settings_hash": _sha256_json(settings),
        "evaluator_hash": str(evaluator_hash),
        "summary": {
            "best_feasible_score": (run.get("best_feasible") or {}).get("_score") if isinstance(run.get("best_feasible"), dict) else None,
            "archive_size": len(run.get("archive") or []),
            "trace_len": len(run.get("trace") or []),
            "resistance": run.get("resistance") or {},
        },
        "archive_sample": (run.get("archive") or [])[:archive_sample_n],
    }
    p = d / f"{run_id}.json"
    p.write_text(json.dumps(capsule, indent=2, sort_keys=True), encoding="utf-8")
    return p


def list_run_capsules(root: Optional[Path] = None, limit: int = 50) -> List[Dict[str, Any]]:
    d = state_dir(root) / "runs"
    if not d.exists():
        return []
    items = []
    for p in sorted(d.glob("*.json"), key=lambda x: x.stat().st_mtime):
        try:
            items.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    if len(items) > limit:
        items = items[-limit:]
    return items


def save_run_capsule_v2(
    run: Dict[str, Any],
    *,
    run_id: str,
    settings: Dict[str, Any],
    evaluator_hash: str,
    archive: List[Dict[str, Any]],
    trace: List[Dict[str, Any]],
    lens_contract: Dict[str, Any],
    resistance_report: Optional[Dict[str, Any]] = None,
    root: Optional[Path] = None,
) -> Path:
    """Save a full replay capsule (v2).

    v2 removes any 'best point' semantics and stores the evaluated trace + archive snapshot.
    """
    d = state_dir(root) / "runs"
    d.mkdir(parents=True, exist_ok=True)
    capsule = {
        "schema": "shams.opt_sandbox.run_capsule.v2",
        "run_id": str(run_id),
        "created_ts": int(time.time()),
        "intent": str(run.get("intent", "")),
        "settings_hash": _sha256_json(settings),
        "evaluator_hash": str(evaluator_hash),
        "lens": dict(lens_contract or {}),
        "telemetry": dict(run.get("telemetry", {})),
        "counts": {
            "n_trace": int(len(trace or [])),
            "n_archive": int(len(archive or [])),
            "n_feasible_in_trace": int(sum(1 for t in (trace or []) if bool(t.get("feasible", False)))),
        },
        "bounds": dict(settings.get("bounds", {})),
        "var_specs": list(settings.get("var_specs", [])),
        "trace": trace or [],
        "archive": archive or [],
    }
    if resistance_report is not None:
        capsule["resistance_report"] = resistance_report

    out = d / f"{run_id}_capsule_v2.json"
    out.write_text(json.dumps(capsule, indent=2, sort_keys=True), encoding="utf-8")
    return out


def load_run_capsule_v2(path: Path) -> Dict[str, Any]:
    """Load a v2 run capsule from JSON on disk.

    This is a pure loader used for replay/diff. It does not imply correctness of the
    underlying physics beyond what the capsule recorded at creation time.
    """
    path = Path(path)
    obj = json.loads(path.read_text(encoding="utf-8"))
    if str(obj.get("schema")) != "shams.opt_sandbox.run_capsule.v2":
        raise ValueError(f"Not a v2 capsule: schema={obj.get('schema')}")
    return obj


def capsule_ladder_hist(capsule: Dict[str, Any]) -> Dict[str, int]:
    """Histogram of feasibility ladder states in capsule trace."""
    hist: Dict[str, int] = {}
    for t in (capsule.get("trace") or []):
        s = str(t.get("feasibility_state") or "unknown")
        hist[s] = hist.get(s, 0) + 1
    return hist


def diff_capsules(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a compact, human-readable diff between two v2 capsules."""
    out: Dict[str, Any] = {"schema": "shams.opt_sandbox.capsule_diff.v1"}
    out["run_ids"] = [a.get("run_id"), b.get("run_id")]
    out["intent"] = [a.get("intent"), b.get("intent")]
    out["evaluator_hash"] = [a.get("evaluator_hash"), b.get("evaluator_hash")]
    out["lens"] = {"a": a.get("lens"), "b": b.get("lens")}
    out["bounds"] = {"a": a.get("bounds"), "b": b.get("bounds")}
    out["counts"] = {"a": a.get("counts"), "b": b.get("counts")}
    out["ladder_hist"] = {"a": capsule_ladder_hist(a), "b": capsule_ladder_hist(b)}

    # Shallow setting hash check for determinism drift
    out["settings_hash_equal"] = bool(a.get("settings_hash") == b.get("settings_hash"))
    out["evaluator_hash_equal"] = bool(a.get("evaluator_hash") == b.get("evaluator_hash"))
    return out
