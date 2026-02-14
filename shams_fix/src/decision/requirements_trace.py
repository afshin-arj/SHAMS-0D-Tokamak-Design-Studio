from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import yaml

def load_requirements(repo_root: Path) -> List[Dict[str, Any]]:
    p = repo_root / "requirements" / "requirements.yaml"
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    reqs = data.get("requirements", [])
    if not isinstance(reqs, list):
        return []
    out=[]
    for r in reqs:
        if isinstance(r, dict) and "id" in r:
            out.append(r)
    return out


def _intent_key_from_artifact(artifact: Dict[str, Any]) -> str:
    """Best-effort intent key extraction.

    Systems artifacts store the human label in ui_state.design_intent.
    Point Designer artifacts may store design_intent directly.
    """
    try:
        v = artifact.get("design_intent")
        if not v and isinstance(artifact.get("ui_state"), dict):
            v = artifact["ui_state"].get("design_intent")
        s = str(v or "Power Reactor (net-electric)").strip().lower()
        return "research" if (s.startswith("research") or s.startswith("experimental") or ("research" in s)) else "reactor"
    except Exception:
        return "reactor"


# Canonical intent policy (must match UI policy in ui/app.py)
_INTENT_HARD: Dict[str, Set[str]] = {
    "reactor": {"q95", "q_div", "P_SOL/R", "sigma_vm", "B_peak", "TF_SC", "HTS margin", "TBR", "NWL"},
    "research": {"q95"},
}
_INTENT_IGNORE: Dict[str, Set[str]] = {
    "reactor": set(),
    "research": {"TBR"},
}


def _hard_set_for_intent(artifact: Dict[str, Any]) -> Set[str]:
    return set(_INTENT_HARD.get(_intent_key_from_artifact(artifact), set()))


def _ignored_set_for_intent(artifact: Dict[str, Any]) -> Set[str]:
    return set(_INTENT_IGNORE.get(_intent_key_from_artifact(artifact), set()))


def _constraint_passed(constraints: List[Dict[str, Any]], name: str) -> bool:
    for c in constraints:
        if str(c.get("name", "")) == name:
            return bool(c.get("passed", False))
    # If constraint is absent, be conservative.
    return False

def _match_constraint(constraints: List[Dict[str, Any]], pattern: str, *, artifact: Dict[str, Any]) -> bool:
    """Return whether a constraint pattern is satisfied.

    Freeze-grade behavior:
    - "*" means all **blocking** constraints pass under the active Design Intent.
      (This prevents the common audit confusion: Research intent may intentionally
      relax/ignore some engineering constraints.)
    - A named constraint that is **ignored** under the active intent is treated as satisfied.
    """

    # '*' means all blocking constraints pass (intent-aware)
    if pattern == "*":
        hard_set = _hard_set_for_intent(artifact)
        for name in sorted(hard_set):
            if not _constraint_passed(constraints, name):
                return False
        return True

    # named constraint: if ignored under intent, treat as satisfied
    if pattern in _ignored_set_for_intent(artifact):
        return True

    # exact name match
    for c in constraints:
        if str(c.get("name","")) == pattern:
            return bool(c.get("passed", False))
    return False

def trace_requirements(artifact: Dict[str, Any], *, repo_root: Path) -> Dict[str, Any]:
    reqs = load_requirements(repo_root)
    constraints = artifact.get("constraints", [])
    if not isinstance(constraints, list):
        constraints=[]
    constraints=[c for c in constraints if isinstance(c, dict)]
    kpis = artifact.get("kpis", {})
    if not isinstance(kpis, dict):
        kpis = {}
    decision = artifact.get("decision", {})
    if not isinstance(decision, dict):
        decision = {}

    rows=[]
    overall="PASS"
    for r in reqs:
        rid=str(r.get("id","REQ"))
        text=str(r.get("text",""))
        severity=str(r.get("severity","should")).lower()
        c_pats=r.get("constraints", [])
        if not isinstance(c_pats, list):
            c_pats=[]
        k_list=r.get("kpis", [])
        if not isinstance(k_list, list):
            k_list=[]
        passed=True

        # Special hook: allow 'decision_grade_ok' as a pseudo-constraint key
        for pat in c_pats:
            if pat == "decision_grade_ok":
                if decision.get("decision_grade_ok") is False:
                    passed=False
            else:
                if not _match_constraint(constraints, str(pat), artifact=artifact):
                    passed=False

        status="PASS" if passed else ("FAIL" if severity=="must" else "WARN")
        if status=="FAIL":
            overall="FAIL"
        elif status=="WARN" and overall!="FAIL":
            overall="WARN"

        evidence={"kpis": {k: kpis.get(k) for k in k_list if k in kpis}}
        rows.append({
            "id": rid,
            "severity": severity,
            "status": status,
            "text": text,
            "evidence": evidence,
        })

    return {"overall": overall, "requirements": rows}
