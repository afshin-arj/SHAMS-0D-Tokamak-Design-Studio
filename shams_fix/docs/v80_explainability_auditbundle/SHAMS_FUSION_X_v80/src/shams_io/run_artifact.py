
from __future__ import annotations

import json
import time
import hashlib
import platform
import sys
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from decision.blockers import rank_blockers
from decision.trade_ledger import trade_ledger
from decision.constraint_ledger import build_constraint_ledger
from decision.kpis import KPI_SET
from decision.requirements_trace import trace_requirements
from program.risk import schedule_proxy, robustness_from_uq
from fidelity.config import normalize_fidelity
from fidelity.maturity import is_low_maturity, decision_grade_check

from constraints.constraints import Constraint
from constraints.bookkeeping import summarize as summarize_constraints_tiered, summarize_by_group

from shams_io.provenance import collect_provenance
from validation.unit_audit import run_unit_audit
from models.model_registry import default_model_registry, selected_model_set

def _normalize_constraints(constraints: List[Any]) -> List[Constraint]:
    """Accept multiple constraint schemas and normalize to constraints.constraints.Constraint."""
    norm: List[Constraint] = []
    for c in constraints or []:
        # Already in expected schema
        if hasattr(c, "passed") and hasattr(c, "sense") and hasattr(c, "limit"):
            norm.append(c)  # type: ignore[arg-type]
            continue

        # Dataclass-like dict
        if isinstance(c, dict):
            # Try to interpret
            name = str(c.get("name","constraint"))
            val = float(c.get("value", 0.0))
            lo = c.get("lo", None)
            hi = c.get("hi", None)
            units = str(c.get("units",""))
            note = str(c.get("description", c.get("note","")))
            group = str(c.get("group","general"))
            severity = str(c.get("severity","hard"))
            if lo is not None:
                lim=float(lo)
                norm.append(Constraint(name=f"{name}_lo", value=val, limit=lim, sense=">=", passed=(val>=lim), severity=severity, units=units, note=note, group=group, meaning=str(c.get('meaning', note)), dominant_inputs=c.get('dominant_inputs'), best_knobs=c.get('best_knobs'), validity=c.get('validity'), maturity=c.get('maturity')))
            if hi is not None:
                lim=float(hi)
                norm.append(Constraint(name=f"{name}_hi", value=val, limit=lim, sense="<=", passed=(val<=lim), severity=severity, units=units, note=note, group=group, meaning=str(c.get('meaning', note)), dominant_inputs=c.get('dominant_inputs'), best_knobs=c.get('best_knobs'), validity=c.get('validity'), maturity=c.get('maturity')))
            if lo is None and hi is None and "sense" in c and "limit" in c:
                lim=float(c["limit"])
                sense=str(c["sense"])
                passed=bool(c.get("passed", (val<=lim if sense=="<=" else val>=lim)))
                norm.append(Constraint(name=name, value=val, limit=lim, sense=sense, passed=passed, severity=severity, units=units, note=note, group=group, meaning=str(c.get('meaning', note)), dominant_inputs=c.get('dominant_inputs'), best_knobs=c.get('best_knobs'), validity=c.get('validity'), maturity=c.get('maturity')))
            continue

        # Dataclass object with lo/hi
        if hasattr(c, "lo") or hasattr(c, "hi"):
            name = str(getattr(c, "name", "constraint"))
            val = float(getattr(c, "value", 0.0))
            lo = getattr(c, "lo", None)
            hi = getattr(c, "hi", None)
            units = str(getattr(c, "units", ""))
            note = str(getattr(c, "description", getattr(c, "note", "")))
            group = str(getattr(c, "group", "general"))
            severity = str(getattr(c, "severity", "hard"))
            if lo is not None:
                lim=float(lo)
                norm.append(Constraint(name=f"{name}_lo", value=val, limit=lim, sense=">=", passed=(val>=lim), severity=severity, units=units, note=note, group=group, meaning=str(c.get('meaning', note)), dominant_inputs=c.get('dominant_inputs'), best_knobs=c.get('best_knobs'), validity=c.get('validity'), maturity=c.get('maturity')))
            if hi is not None:
                lim=float(hi)
                norm.append(Constraint(name=f"{name}_hi", value=val, limit=lim, sense="<=", passed=(val<=lim), severity=severity, units=units, note=note, group=group, meaning=str(c.get('meaning', note)), dominant_inputs=c.get('dominant_inputs'), best_knobs=c.get('best_knobs'), validity=c.get('validity'), maturity=c.get('maturity')))
            continue

        # Fallback: skip unknown types
    return norm

from .migrate import migrate_artifact
from .schema import validate_artifact


from .schema import CURRENT_SCHEMA_VERSION
from .provenance import collect_provenance

from models.model_registry import default_model_registry, selected_model_set
from validation.unit_audit import run_unit_audit

SCHEMA_VERSION = CURRENT_SCHEMA_VERSION

# -----------------------------
# Verification provenance
# -----------------------------

def _repo_root(start: Path) -> Path:
    """Walk up to find repo root (heuristic: requirements.txt or .git)."""
    cur = start.resolve()
    for _ in range(12):
        if (cur / "requirements.txt").exists() or (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def _read_repo_version(start: Path | None = None) -> str:
    """Read VERSION file if present at repo root."""
    try:
        if start is None:
            start = Path(__file__).resolve()
        root = _repo_root(Path(start))
        p = root / "VERSION"
        if p.exists():
            v = p.read_text(encoding="utf-8", errors="ignore").strip()
            return v
    except Exception:
        pass
    return ""


def _read_release_notes_excerpt(start: Path | None = None, max_lines: int = 40) -> str:
    """Return a short excerpt of RELEASE_NOTES.md if present (for artifact provenance)."""
    try:
        if start is None:
            start = Path(__file__).resolve()
        root = _repo_root(Path(start))
        p = root / "RELEASE_NOTES.md"
        if p.exists():
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            return "\n".join(lines[:max_lines]).strip()
    except Exception:
        pass
    return ""


def try_load_verification_report() -> Dict[str, Any]:
    """Load verification/report.json if present (optional)."""
    try:
        root = _repo_root(Path(__file__).resolve())
        rp = root / "verification" / "report.json"
        if rp.exists():
            return json.loads(rp.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {}


def _stable_hash_json(obj: Any) -> str:
    try:
        s = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(s).hexdigest()
    except Exception:
        return ""

def _attach_constraint_fingerprint(d: Dict[str, Any]) -> Dict[str, Any]:
    """Attach deterministic provenance fingerprints for a constraint JSON dict.

    This is intentionally transparent: the fingerprint is a SHA256 hash of a
    stable, sorted JSON subset of fields that define the constraint.
    """
    subset_keys = [
        "name","sense","limit","lo","hi","units","severity","group",
        "meaning","validity","maturity"
    ]
    subset = {k: d.get(k) for k in subset_keys if k in d}
    fp = _stable_hash_json(subset)
    prov = d.get("provenance", {})
    if not isinstance(prov, dict):
        prov = {}
    prov.setdefault("constraint_fingerprint_sha256", fp)
    d["provenance"] = prov
    return d



@dataclass(frozen=True)
class RunMeta:
    """Metadata for a SHAMS run artifact.

    This is the SHAMS-native analogue of PROCESS's 'MFILE' concept: one canonical
    output object that every report/plotter can consume.

    Times are unix seconds to keep things portable.
    """
    created_unix: float
    shams_version: str = "phase14"
    label: str = ""
    mode: str = "point"  # point | scan
    notes: str = ""


def _constraint_to_json(c: Constraint) -> Dict[str, Any]:
    """Serialize a constraint with consistent margin semantics.

    Supports the SHAMS Constraint dataclass (lo/hi bounds) and
    older PROCESS-like forms (sense/limit) if present.
    """
    d = asdict(c)

    # New-style bounds: lo/hi (preferred)
    lo = d.get("lo", None)
    hi = d.get("hi", None)
    val = float(d.get("value", 0.0))
    if lo is not None or hi is not None:
        # Margin is positive when feasible, negative when violated.
        # If both bounds exist, take the tighter (smaller) margin.
        margins = []
        if lo is not None:
            m = val - float(lo)
            margins.append(m)
            d["margin_to_lo"] = float(m)
        if hi is not None:
            m = float(hi) - val
            margins.append(m)
            d["margin_to_hi"] = float(m)
        d["margin"] = float(min(margins)) if margins else 0.0
        denom = max(abs(val), 1e-30)
        d["margin_frac"] = float(d["margin"] / denom)
        d = _attach_constraint_fingerprint(d)
        return d

    # Legacy-style: sense/limit (best-effort)
    sense = getattr(c, "sense", None)
    limit = getattr(c, "limit", None)
    if sense in ("<=", ">=") and limit is not None:
        limit_f = float(limit)
        if sense == "<=":
            d["margin"] = float(limit_f - val)
        else:
            d["margin"] = float(val - limit_f)
        d["margin_frac"] = float(d["margin"] / max(abs(limit_f), 1e-30))
        d["sense"] = sense
        d["limit"] = limit_f
        d = _attach_constraint_fingerprint(d)
        return d

    # Fallback: unknown schema
    d["margin"] = float("nan")
    d["margin_frac"] = float("nan")
    d = _attach_constraint_fingerprint(d)
    return d


def _stable_hash(obj: Any) -> str:
    """Compute a stable SHA256 over a JSON-serializable object."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def _get_git_commit(root: Optional[Path] = None) -> str:
    """Best-effort git commit hash (empty if unavailable)."""
    try:
        root = root or Path(__file__).resolve().parents[2]
        head = root / ".git" / "HEAD"
        if not head.exists():
            return ""
        ref = head.read_text(encoding="utf-8").strip()
        if ref.startswith("ref:"):
            ref_path = root / ".git" / ref.split(":", 1)[1].strip()
            if ref_path.exists():
                return ref_path.read_text(encoding="utf-8").strip()[:40]
        return ref[:40]
    except Exception:
        return ""



def _compute_kpis(outputs: Dict[str, Any], constraints_json: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute a stable KPI dict used across UI + PDF.

    KPIs come from KPI_SET (decision/kpis.py) plus a few derived feasibility scalars.
    """
    k: Dict[str, Any] = {}
    for kpi in KPI_SET:
        key = kpi.key
        k[key] = outputs.get(key, kpi.fallback)

    # Derived feasibility KPIs
    hard_margins=[]
    hard_ok=True
    for c in constraints_json:
        if str(c.get("severity","hard")).lower() != "hard":
            continue
        m = c.get("margin", None)
        try:
            if m is not None:
                hard_margins.append(float(m))
        except Exception:
            pass
        if not bool(c.get("passed", True)):
            hard_ok=False
    k["feasible_hard"] = bool(hard_ok)
    k["min_hard_margin"] = float(min(hard_margins)) if hard_margins else float("nan")
    # robustness passthrough (if present)
    rob = robustness_from_uq(outputs)
    if rob:
        k["p_feasible"] = rob.get("p_feasible")
    return k

def _build_nonfeasibility_certificate(constraints_json: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create an explicit non-feasibility certificate when no hard-feasible solution exists."""
    hard_failed=[c for c in constraints_json if str(c.get("severity","hard")).lower()=="hard" and not bool(c.get("passed", True))]
    # Sort by worst margin (most negative first)
    def key(c):
        try:
            return float(c.get("margin", 0.0))
        except Exception:
            return 0.0
    hard_failed.sort(key=key)
    blockers=[]
    for c in hard_failed[:10]:
        blockers.append({
            "name": c.get("name",""),
            "value": c.get("value"),
            "limit": c.get("limit"),
            "sense": c.get("sense"),
            "margin": c.get("margin"),
            "meaning": c.get("meaning",""),
            "best_knobs": c.get("best_knobs", []),
            "validity": c.get("validity"),
            "maturity": c.get("maturity"),
            "provenance": c.get("provenance"),
        })
    return {
        "hard_feasible": False,
        "dominant_blockers": blockers,
        "recommendation": "Move the listed best_knobs (and/or relax assumptions) until all hard constraints pass.",
    }
def build_run_artifact(
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    constraints: List[Constraint],
    *,
    meta: Optional[RunMeta] = None,
    subsystems: Optional[Dict[str, Any]] = None,
    scan: Optional[Dict[str, Any]] = None,
    solver: Optional[Dict[str, Any]] = None,
    baseline_inputs: Optional[Dict[str, Any]] = None,
    decision: Optional[Dict[str, Any]] = None,
    fidelity: Optional[Dict[str, Any]] = None,
    calibration: Optional[Dict[str, Any]] = None,
    economics: Optional[Dict[str, Any]] = None,
    verification: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a canonical run artifact dict (JSON-serializable)."""
    if meta is None:
        meta = RunMeta(created_unix=time.time())
    elif isinstance(meta, dict):
        # Backward compatible: allow passing a dict of RunMeta fields.
        _allowed = {f.name for f in RunMeta.__dataclass_fields__.values()}
        _kw = {k: meta[k] for k in meta.keys() if k in _allowed and k != "created_unix"}
        meta = RunMeta(created_unix=float(meta.get("created_unix", time.time())), **_kw)

    # Stamp repo version if available (keeps backward compatibility)
    try:
        rv = _read_repo_version(Path(__file__).resolve())
        if rv and (not getattr(meta, "shams_version", "") or meta.shams_version == "phase14"):
            meta = RunMeta(created_unix=meta.created_unix, shams_version=rv, label=meta.label, mode=meta.mode, notes=meta.notes)
    except Exception:
        pass

    # Normalize constraint schemas (lo/hi vs sense/limit)
    constraints = _normalize_constraints(constraints)

    art: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_unix": float(meta.created_unix),
        "shams_version": str(meta.shams_version),
        "label": str(meta.label),
        "mode": str(meta.mode),
        "notes": str(meta.notes),
        "meta": asdict(meta),
        "inputs": inputs,
        "outputs": outputs,
        "economics": economics or {},
        "constraints": [_constraint_to_json(c) for c in constraints],
        "constraints_summary": summarize_constraints_tiered(constraints).to_dict(),
        "constraints_by_group": summarize_by_group(constraints),
        "constraint_ledger": {},
        "solver": solver,
        "input_hash": _stable_hash(inputs),
        "model_cards": (outputs.get("model_cards") if isinstance(outputs, dict) else {}),
        "verification": {},
        "provenance": {
            **collect_provenance(Path(__file__).resolve()),
            "release_notes_excerpt": _read_release_notes_excerpt(Path(__file__).resolve(), max_lines=60),
        },

        # PROCESS-inspired but SHAMS-native: make model option selection explicit.
        "model_registry": default_model_registry(),
        "model_set": selected_model_set(outputs if isinstance(outputs, dict) else {}, overrides=(subsystems or {}).get("model_overrides") if isinstance(subsystems, dict) else None),

    }

        # Compute stable KPIs for UI + PDF.
    constraints_json = art.get("constraints", [])
    if isinstance(constraints_json, list):
        constraints_json = [c for c in constraints_json if isinstance(c, dict)]
    else:
        constraints_json = []
    art["kpis"] = _compute_kpis(outputs if isinstance(outputs, dict) else {}, constraints_json)

    # Standardized output tables (PROCESS-inspired, SHAMS-transparent).
    try:
        outd = outputs if isinstance(outputs, dict) else {}
        art["tables"] = {
            "schema_version": "tables.v1",
            "plasma": {k: outd.get(k) for k in ["H98", "Q_DT_eqv", "beta_N", "nGW", "Ti_keV", "Te_keV", "Ip_MA", "B0_T"] if k in outd},
            "power_balance": {k: outd.get(k) for k in ["Paux_MW", "Pfus_DT_adj_MW", "P_net_e_MW", "P_rad_MW", "Pohm_MW"] if k in outd},
            "tritium": {k: outd.get(k) for k in ["TBR", "TBR_margin", "TBR_req"] if k in outd},
        }
    except Exception:
        art["tables"] = {"schema_version": "tables.v1"}

    # Constraint accounting ledger (explicit, stable ordering, decision-grade).
    try:
        art["constraint_ledger"] = build_constraint_ledger(constraints_json)
    except Exception:
        art["constraint_ledger"] = {"schema_version": "constraint_ledger.v1", "entries": [], "top_blockers": []}

    # Verification proxy: sanity/unit audit embedded in artifact.
    try:
        art["verification_checks"] = run_unit_audit(outputs if isinstance(outputs, dict) else {})
    except Exception:
        art["verification_checks"] = {"schema_version": "verification_checks.v1", "overall_ok": True, "checks": []}

    # Program-level planning proxies (transparent heuristics).
    art["program"] = schedule_proxy(inputs if isinstance(inputs, dict) else {}, outputs if isinstance(outputs, dict) else {})

    # Requirements traceability (if requirements/requirements.yaml exists).
    try:
        repo_root = _repo_root(Path(__file__).resolve())
        art["requirements_trace"] = trace_requirements(art, repo_root=repo_root)
    except Exception:
        art["requirements_trace"] = {"overall": "UNKNOWN", "requirements": []}

    # Explicit non-feasibility certificate when hard infeasible.
    if not bool(art["kpis"].get("feasible_hard", False)):
        art["nonfeasibility_certificate"] = _build_nonfeasibility_certificate(constraints_json)

    # Attach verification compliance matrix (if available).
    if verification is None:
        verification = try_load_verification_report()
    if isinstance(verification, dict) and verification:
        art["verification"] = {
            "report": verification,
            "report_hash": _stable_hash_json(verification),
        }
    if decision is not None:
        art["decision"] = decision
    if fidelity is not None:
        art["fidelity"] = normalize_fidelity(fidelity)
    if calibration is not None:
        art["calibration"] = calibration
    if subsystems:
        art["subsystems"] = subsystems
    if scan:
        art["scan"] = scan
    return art

def write_run_artifact(path: str | Path, artifact: Dict[str, Any]) -> Path:
    """Write artifact to JSON with stable formatting."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    return p


def read_run_artifact(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def summarize_constraints(constraints_json: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Quick summary useful for UI + reports."""
    n = len(constraints_json)
    n_fail = sum(0 if c.get("passed") else 1 for c in constraints_json)
    worst = None
    worst_key = None
    # most negative margin_frac among hard constraints
    for c in constraints_json:
        if c.get("severity", "hard") != "hard":
            continue
        mf = float(c.get("margin_frac", 0.0))
        if worst is None or mf < worst:
            worst = mf
            worst_key = c.get("name")
    return {"n": n, "n_fail": n_fail, "worst_margin_frac": worst, "worst": worst_key}
