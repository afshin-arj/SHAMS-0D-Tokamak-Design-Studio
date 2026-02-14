from __future__ import annotations
"""Mission Context Layer (v121)

Mission contexts provide *advisory overlays* for a run artifact:
- evaluate how a design aligns with mission targets
- identify mission gaps from existing artifact outputs/constraints
- generate report artifacts (JSON + CSV)

No physics/constraint/solver behavior is changed.
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import json
import time
import csv
import io

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def list_builtin_missions(missions_dir: str = "missions") -> List[str]:
    """Return builtin mission spec filenames (e.g., pilot.json).

    missions_dir is resolved relative to repo root for robustness.
    """
    base = Path(__file__).resolve().parents[1]
    d = (base / missions_dir)
    if not d.exists():
        return []
    return sorted([p.name for p in d.glob("*.json")])

def load_mission(path: str) -> Dict[str, Any]:
    """Load a mission spec.

    Accepts:
      - full path to a .json file
      - a filename like 'pilot.json'
      - a bare name like 'pilot' (will resolve to missions/pilot.json)
    """
    base = Path(__file__).resolve().parents[1]
    p = Path(path)

    # If a bare name is provided, resolve into missions/<name>.json
    if (not p.exists()) and (p.suffix == ""):
        cand = base / "missions" / f"{p.name}.json"
        p = cand

    # If a filename is provided but not found, try missions/<filename>
    if (not p.exists()) and (p.suffix == ".json"):
        cand = base / "missions" / p.name
        p = cand

    if p.is_dir():
        raise ValueError("mission path must be a file")
    if not p.exists():
        raise FileNotFoundError(str(p))

    m = json.loads(p.read_text(encoding="utf-8"))
    if not (isinstance(m, dict) and m.get("kind") == "shams_mission_spec"):
        raise ValueError("expected shams_mission_spec")
    return m

def _get_outputs(artifact: Dict[str, Any]) -> Dict[str, Any]:
    o = artifact.get("outputs", {})
    return o if isinstance(o, dict) else {}

def _get_constraints_summary(artifact: Dict[str, Any]) -> Dict[str, Any]:
    cs = artifact.get("constraints_summary", {})
    return cs if isinstance(cs, dict) else {}

def _metric(outputs: Dict[str, Any], keys: List[str]) -> Optional[float]:
    for k in keys:
        v = outputs.get(k)
        try:
            if v is not None:
                return float(v)
        except Exception:
            continue
    return None

def apply_mission_overlays(
    *,
    run_artifact: Dict[str, Any],
    mission: Dict[str, Any],
    version: str = "v121",
) -> Dict[str, Any]:
    if not (isinstance(run_artifact, dict) and run_artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("expected shams_run_artifact")
    if not (isinstance(mission, dict) and mission.get("kind") == "shams_mission_spec"):
        raise ValueError("expected shams_mission_spec")

    outputs = _get_outputs(run_artifact)
    cs = _get_constraints_summary(run_artifact)

    # SHAMS does not assume canonical naming; try common fields
    pn = _metric(outputs, ["Pn_MW", "Pnet_MW", "P_net_MW"])
    q = _metric(outputs, ["Q", "Qfus", "Q_plasma"])

    targets = mission.get("targets", {}) if isinstance(mission.get("targets"), dict) else {}
    gaps: List[Dict[str, Any]] = []
    def check_min(name: str, val: Optional[float], tkey: str):
        t = targets.get(tkey)
        try:
            t = float(t)
        except Exception:
            return
        if val is None:
            gaps.append({"kind":"mission_gap", "metric": name, "target": t, "value": None, "status":"missing"})
        elif val < t:
            gaps.append({"kind":"mission_gap", "metric": name, "target": t, "value": val, "status":"below_target"})
    check_min("Pn_MW", pn, "Pn_MW_min")
    check_min("Q", q, "Q_min")

    feas = cs.get("feasible")
    if feas is False:
        gaps.append({"kind":"mission_gap", "metric":"feasibility", "target": True, "value": False, "status":"infeasible"})

    # Use worst constraint as a mission-critical blocker signal
    worst = cs.get("worst_hard")
    wmargin = cs.get("worst_hard_margin_frac")
    report = {
        "kind":"shams_mission_report",
        "version": version,
        "created_utc": _created_utc(),
        "mission_name": mission.get("name"),
        "mission": mission,
        "source_artifact_id": run_artifact.get("id"),
        "alignment": {
            "Pn_MW": pn,
            "Q": q,
            "feasible": feas,
            "worst_hard": worst,
            "worst_hard_margin_frac": wmargin,
        },
        "gaps": gaps,
        "notes":[
            "Mission report is advisory overlay only. No physics/constraints were modified.",
        ],
    }
    return report

def mission_report_csv(report: Dict[str, Any]) -> bytes:
    # Flatten gaps to CSV rows
    gaps = report.get("gaps", [])
    if not isinstance(gaps, list):
        gaps = []
    buf = io.StringIO()
    fieldnames = ["metric","target","value","status"]
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for g in gaps:
        if not isinstance(g, dict):
            continue
        w.writerow({k: g.get(k) for k in fieldnames})
    return buf.getvalue().encode("utf-8")
