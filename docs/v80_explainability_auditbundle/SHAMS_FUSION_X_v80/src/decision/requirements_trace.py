from __future__ import annotations

from typing import Any, Dict, List, Optional
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

def _match_constraint(constraints: List[Dict[str, Any]], pattern: str) -> bool:
    # '*' means all hard constraints pass
    if pattern == "*":
        for c in constraints:
            if str(c.get("severity","hard")).lower() != "hard":
                continue
            if not bool(c.get("passed", True)):
                return False
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
                if not _match_constraint(constraints, str(pat)):
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
