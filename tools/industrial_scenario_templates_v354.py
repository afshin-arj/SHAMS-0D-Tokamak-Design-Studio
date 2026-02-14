from __future__ import annotations

"""Industrial scenario templates (v354.0).

These are *intent templates* for Point Designer inputs:
- They do NOT modify physics truth.
- They provide deterministic, reviewer-safe starting points for industrial use cases.

Templates are defined as sparse PointInputs override dicts. Unknown keys are ignored by callers.

© 2026 Afshin Arjhangmehr
"""

from typing import Dict, List, Any
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCEN_DIR = _REPO_ROOT / "scenarios" / "industrial_v354"

def template_names() -> List[str]:
    out: List[str] = []
    if _SCEN_DIR.exists():
        for p in sorted(_SCEN_DIR.glob("*.json")):
            try:
                j = json.loads(p.read_text(encoding="utf-8"))
                out.append(str(j.get("name") or p.stem))
            except Exception:
                out.append(p.stem)
    return out

def get_template(name: str) -> Dict[str, Any]:
    n = str(name).strip()
    if not _SCEN_DIR.exists():
        return {}
    for p in sorted(_SCEN_DIR.glob("*.json")):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            if str(j.get("name") or "").strip() == n:
                d = j.get("point_inputs_overrides") or {}
                return dict(d) if isinstance(d, dict) else {}
        except Exception:
            continue
    return {}

def get_template_payload(name: str) -> Dict[str, Any]:
    n = str(name).strip()
    if not _SCEN_DIR.exists():
        return {}
    for p in sorted(_SCEN_DIR.glob("*.json")):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            if str(j.get("name") or "").strip() == n:
                return dict(j)
        except Exception:
            continue
    return {}
