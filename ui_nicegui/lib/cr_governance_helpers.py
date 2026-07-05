"""Control Room — artifact governance overlays and case deck runner."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ui_nicegui.bootstrap import repo_root
from ui_nicegui.lib.cr_artifacts_helpers import collect_session_artifacts, load_json_bytes


def pick_session_artifact(session) -> Optional[dict]:
    if isinstance(getattr(session, "cr_selected_artifact", None), dict):
        return session.cr_selected_artifact
    arts = collect_session_artifacts(session)
    if arts:
        return arts[-1]["artifact"]
    from ui_nicegui.lib.pub_benchmark_extended_helpers import pick_session_run_artifact

    return pick_session_run_artifact(session)


def authority_confidence_rows(art: dict) -> List[dict]:
    ac = art.get("authority_confidence") if isinstance(art, dict) else None
    if not isinstance(ac, dict):
        return []
    subs = ac.get("subsystems") or {}
    rows = []
    for k in sorted(subs.keys()):
        v = subs.get(k) or {}
        if not isinstance(v, dict):
            continue
        rows.append({
            "subsystem": k,
            "confidence": v.get("confidence_class"),
            "authority_tier": v.get("authority_tier"),
            "maturity": v.get("maturity"),
            "involved": v.get("involved"),
        })
    return rows


def design_confidence_class(art: dict) -> str:
    ac = art.get("authority_confidence") or {}
    if isinstance(ac, dict):
        return str((ac.get("design") or {}).get("design_confidence_class", "UNKNOWN"))
    return "UNKNOWN"


def decision_consequences_summary(art: dict) -> Dict[str, Any]:
    dc = art.get("decision_consequences") if isinstance(art, dict) else None
    if not isinstance(dc, dict):
        return {}
    return {
        "decision_posture": dc.get("decision_posture"),
        "primary_risk_driver": dc.get("primary_risk_driver"),
        "dominant_mechanism": dc.get("dominant_mechanism"),
        "dominant_constraint": dc.get("dominant_constraint"),
        "worst_hard_margin_frac": dc.get("worst_hard_margin_frac"),
        "narrative": dc.get("narrative"),
    }


def authority_dominance_summary(art: dict) -> Dict[str, Any]:
    dom = art.get("authority_dominance") if isinstance(art, dict) else None
    if not isinstance(dom, dict):
        dom = (art.get("outputs") or {}).get("authority_dominance") if isinstance(art.get("outputs"), dict) else None
    if not isinstance(dom, dict):
        return {}
    return {
        "dominant_authority": dom.get("dominant_authority") or dom.get("dominant"),
        "ranking": dom.get("ranking") or dom.get("ordered") or [],
        "top_limiting": dom.get("top_limiting_constraints") or dom.get("top_blockers") or [],
    }


def epoch_feasibility_summary(art: dict) -> Dict[str, Any]:
    ef = art.get("epoch_feasibility") if isinstance(art, dict) else None
    if not isinstance(ef, dict):
        ef = ((art.get("artifact") or {}).get("epoch_feasibility") if isinstance(art.get("artifact"), dict) else None)
    if not isinstance(ef, dict):
        return {}
    rows = []
    for e in ef.get("epochs") or []:
        if isinstance(e, dict):
            rows.append({"epoch": e.get("epoch"), "verdict": e.get("verdict")})
    return {"overall": ef.get("overall"), "epochs": rows}


def constraint_ledger_rows(art: dict, *, failed_only: bool = False) -> List[dict]:
    ledger = art.get("constraint_ledger") or {}
    entries = ledger.get("entries") if isinstance(ledger, dict) else []
    if not isinstance(entries, list):
        entries = art.get("constraints") or []
    rows = [e for e in entries if isinstance(e, dict)]
    if failed_only:
        rows = [r for r in rows if r.get("passed") is False or r.get("failed")]
    rows.sort(key=lambda r: float(r.get("margin_frac", r.get("margin", 0)) or 0))
    return rows


def constraint_names(art: dict) -> List[str]:
    names: List[str] = []
    for r in constraint_ledger_rows(art):
        n = r.get("name")
        if n and n not in names:
            names.append(str(n))
    for c in art.get("constraints") or []:
        if isinstance(c, dict) and c.get("name"):
            n = str(c["name"])
            if n not in names:
                names.append(n)
    return names


def constraint_detail(art: dict, name: str) -> dict:
    out: dict = {}
    for r in constraint_ledger_rows(art):
        if str(r.get("name")) == name:
            out.update(r)
    for c in art.get("constraints") or []:
        if isinstance(c, dict) and str(c.get("name")) == name:
            out.update({k: c.get(k) for k in c})
    return out


def run_case_deck_file(deck_bytes: bytes, filename: str, out_name: str) -> dict:
    root = Path(repo_root())
    out_root = root / "ui_runs"
    out_root.mkdir(parents=True, exist_ok=True)
    deck_path = out_root / f"_uploaded_{filename}"
    deck_path.write_bytes(deck_bytes)
    out_dir = out_root / (out_name or f"deck_{int(time.time())}")
    out_dir.mkdir(parents=True, exist_ok=True)
    runner = root / "tools" / "run_case_deck.py"
    proc = subprocess.run(
        [sys.executable, str(runner), str(deck_path), "--out", str(out_dir)],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    result = {
        "returncode": int(proc.returncode),
        "stdout": (proc.stdout or "")[:8000],
        "stderr": (proc.stderr or "")[:8000],
        "out_dir": str(out_dir),
    }
    art_path = out_dir / "shams_run_artifact.json"
    cfg_path = out_dir / "run_config_resolved.json"
    if cfg_path.is_file():
        result["resolved_config"] = json.loads(cfg_path.read_text(encoding="utf-8"))
    if art_path.is_file():
        result["artifact"] = json.loads(art_path.read_text(encoding="utf-8"))
    return result


def parse_uploaded_deck(content: bytes) -> bytes:
    return content
