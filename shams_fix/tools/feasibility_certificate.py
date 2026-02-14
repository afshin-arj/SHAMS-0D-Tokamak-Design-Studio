from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _stable_json_bytes(obj: Any) -> bytes:
    """Stable JSON bytes for hashing; never raises.

    We use default=str so unknown objects become strings. That is acceptable for
    hashing/provenance because it still makes the certificate deterministic for
    the provided artifact payload.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")


def _sha256(obj: Any) -> str:
    return hashlib.sha256(_stable_json_bytes(obj)).hexdigest()


def _tree_code_hash(repo_root: Path) -> str:
    """Best-effort code hash for a release zip (no .git).

    Hashes a curated set of files that define executable behavior: VERSION,
    ui/*.py, tools/*.py, src/**/*.py.
    """
    repo_root = Path(repo_root)
    parts: List[Tuple[str, str]] = []

    def add_file(p: Path):
        try:
            b = p.read_bytes()
        except Exception:
            return
        parts.append((str(p.relative_to(repo_root)).replace("\\", "/"), hashlib.sha256(b).hexdigest()))

    for rel in ["VERSION"]:
        p = repo_root / rel
        if p.exists():
            add_file(p)

    for glob in ["ui/**/*.py", "tools/**/*.py", "src/**/*.py"]:
        for p in sorted(repo_root.glob(glob)):
            if p.is_file():
                add_file(p)

    payload = {"files": parts}
    return _sha256(payload)


def _extract_hard_constraints(constraints: Any) -> Dict[str, Dict[str, Any]]:
    """Normalize the run_artifact constraints list into a HARD constraint table."""
    hard: Dict[str, Dict[str, Any]] = {}
    if not isinstance(constraints, list):
        return hard

    for c in constraints:
        if not isinstance(c, dict):
            continue
        if str(c.get("severity", "hard")).lower() != "hard":
            continue
        name = str(c.get("name") or "").strip() or "(unnamed)"
        val = c.get("value")
        passed = bool(c.get("passed", True))
        margin_abs = c.get("margin")
        margin_frac = c.get("margin_frac")
        # limit: represent bounds if present, else sense/limit
        limit: Any = None
        if (c.get("lo") is not None) or (c.get("hi") is not None):
            limit = {"lo": c.get("lo"), "hi": c.get("hi")}
        elif c.get("limit") is not None:
            limit = c.get("limit")
        elif (c.get("sense") is not None) and (c.get("limit") is not None):
            limit = {"sense": c.get("sense"), "limit": c.get("limit")}

        hard[name] = {
            "value": val,
            "limit": limit,
            "margin_abs": margin_abs,
            "margin_frac": margin_frac,
            "pass": passed,
        }
    return hard


def generate_feasibility_certificate(
    run_artifact: Dict[str, Any],
    *,
    repo_root: Optional[Path] = None,
    run_id: str = "",
    origin: str = "point",
) -> Dict[str, Any]:
    """Generate a v139 Feasibility Certificate from a run_artifact.

    Parameters
    - run_artifact: SHAMS run artifact payload (kind=shams_run_artifact)
    - repo_root: root of the repository (for computing code_hash). If omitted,
      hashes will use artifact provenance only.
    - run_id: optional ledger run id for traceability
    - origin: point | fc_handoff | study_matrix | other
    """

    if not (isinstance(run_artifact, dict) and run_artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("run_artifact must be a dict with kind='shams_run_artifact'")

    inputs = run_artifact.get("inputs", {}) if isinstance(run_artifact.get("inputs"), dict) else {}
    cs = run_artifact.get("constraints_summary", {}) if isinstance(run_artifact.get("constraints_summary"), dict) else {}
    solver = run_artifact.get("solver", {}) if isinstance(run_artifact.get("solver"), dict) else {}

    # SHAMS version + code hash
    shams_version = str(run_artifact.get("shams_version") or run_artifact.get("version") or "")
    if repo_root is not None:
        try:
            code_hash = _tree_code_hash(Path(repo_root))
        except Exception:
            code_hash = ""
    else:
        # fall back to artifact provenance fingerprint
        code_hash = _sha256(run_artifact.get("provenance", {}))

    hard_table = _extract_hard_constraints(run_artifact.get("constraints"))

    # dominance: worst + second worst by margin_frac (most negative)
    ordered = []
    for name, row in hard_table.items():
        try:
            mf = float(row.get("margin_frac"))
        except Exception:
            mf = float("inf")
        ordered.append((mf, name))
    ordered.sort(key=lambda x: x[0])  # most negative first

    worst_name = cs.get("worst_hard")
    worst_mf = cs.get("worst_hard_margin_frac")
    # if cs missing, use computed
    if not worst_name and ordered:
        worst_name = ordered[0][1]
        worst_mf = ordered[0][0]

    second = ordered[1][1] if len(ordered) >= 2 else None

    solver_context = {
        "backend": solver.get("backend") or solver.get("name") or solver.get("label") or "",
        "iterations": solver.get("iterations") or solver.get("n_iter") or solver.get("iters"),
        "converged": solver.get("converged") if solver.get("converged") is not None else solver.get("ok"),
        "tolerances": solver.get("tolerances") or {},
    }

    cert = {
        "kind": "shams_feasibility_certificate",
        "version": "v139",
        "certificate_id": str(uuid.uuid4()),
        "issued_utc": _utc_now(),
        "shams": {
            "version": shams_version,
            "code_hash": code_hash,
        },
        "source_run": {
            "run_id": str(run_id or ""),
            "origin": str(origin or ""),
        },
        "inputs": inputs,
        "constraints": {
            "hard": hard_table,
        },
        "dominance": {
            "worst_constraint": worst_name,
            "worst_margin_frac": worst_mf,
            "second_worst_constraint": second,
        },
        "solver_context": solver_context,
        "hashes": {
            "inputs_sha256": _sha256(inputs),
            "constraints_sha256": _sha256(hard_table),
            "solver_context_sha256": _sha256(solver_context),
        },
    }

    return cert
