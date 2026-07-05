"""Control Room helpers — governance, docs, diagnostics."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ui_nicegui.bootstrap import repo_root


CR_SECTIONS = [
    "Orientation",
    "Constitution",
    "Diagnostics",
    "Provenance",
    "Artifacts",
    "Chronicle",
]

ORIENT_TABS = ["Launchpad", "Vocabulary", "Reference Gallery", "Scope"]
CONST_TABS = ["Model Ledger", "Capability Matrix", "Docs Library"]
DIAG_TABS = ["Gatechecks", "Interoperability", "Session", "Non-Feasibility Guide"]

CHRONICLE_TABS = [
    "Variable Registry",
    "Sensitivity Explorer",
    "Feasibility Map",
    "Interval Narrowing",
    "Local Forensics",
    "Study Dashboard",
]

ARTIFACT_TABS = ["Artifacts Explorer", "Run Library", "Export & Share"]

REFERENCE_GALLERY: List[Tuple[str, str]] = [
    ("ITER-like", "Large, conservative, physics-demonstration anchor; often stress and divertor constraints dominate."),
    ("SPARC-like", "Compact high-field concept; often HTS margin and structural stress dominate."),
    ("ARC-like", "HTS reactor class; often net-electric closure and blanket/TBR proxies dominate."),
    ("DEMO-like", "Plant realism anchor; often recirculating power and availability assumptions dominate."),
]

LAUNCHPAD_PATHS: List[Tuple[str, str, str]] = [
    (
        "Understand feasibility limits (cartography)",
        "Recommended: Scan Lab → build Scan Atlas → inspect first-failure topology.",
        "- Start with **Scan Lab → Setup & Run**\n- Choose a compact 2D scan\n- Export the Scan Atlas capsule for review-room replay.",
    ),
    (
        "Explore reactor concepts (Forge)",
        "Recommended: Reactor Design Forge → Casebook → Candidate Archive → Machine Dossier.",
        "- Use **Forge Cockpit** with the **Helm Console**\n- Keep **Margins-first** framing\n- Save capsules for deterministic replay.",
    ),
    (
        "Review a finished case (Review Room)",
        "Recommended: Reactor Design Forge → Review Mode → Review Trinity → Do-Not-Build Brief.",
        "- Turn on **Review Mode**\n- Use **Review Trinity** and **Conflict Atlas**\n- Generate a **Reviewer Packet**.",
    ),
    (
        "Compare designs (Artifacts)",
        "Recommended: Compare → upload two artifacts → inspect deltas.",
        "- Use **Compare artifacts** to check reproducibility\n- Prefer capsule replay over manual edits.",
    ),
]


def _root() -> Path:
    return Path(repo_root())


def read_version() -> str:
    try:
        return (_root() / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"


def read_doc(rel: str, *, max_chars: Optional[int] = None) -> str:
    path = _root() / rel.replace("/", "\\").lstrip("\\/")
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return f"(missing {rel})"
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + "\n\n…"
    return text


def list_docs() -> List[str]:
    docs_dir = _root() / "docs"
    if not docs_dir.is_dir():
        return []
    return sorted(str(p.relative_to(docs_dir)).replace("\\", "/") for p in docs_dir.rglob("*.md") if p.is_file())


def read_capability_matrix() -> str:
    docs = _root() / "docs"
    gen = docs / "PHYSICS_CAPABILITY_MATRIX_GENERATED.md"
    src = docs / "PHYSICS_CAPABILITY_MATRIX.md"
    try:
        if gen.exists():
            return gen.read_text(encoding="utf-8", errors="replace")
        if src.exists():
            return src.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    return "(missing docs/PHYSICS_CAPABILITY_MATRIX*.md)"


def hygiene_scan() -> Dict[str, Any]:
    root = _root()
    forbidden = ["__pycache__", ".pytest_cache", "gspulse_ui"]
    hits: List[str] = []
    for name in forbidden:
        for h in root.rglob(name):
            hits.append(str(h))
    for h in root.glob("run_st*"):
        hits.append(str(h))
    hits = sorted(set(hits))
    return {"ok": len(hits) == 0, "hits": hits}


def session_snapshot(session: Any) -> Dict[str, str]:
    """Lightweight session key inventory for debug panel."""
    keys = [
        "active_deck", "last_eval", "pd_last_outputs", "pd_last_artifact",
        "systems_last_solve_artifact", "last_precheck_report", "scan_cartography_report",
        "pareto_last", "trade_last", "cmp_slot_a", "cmp_slot_b", "pub_atlas_last",
    ]
    out: Dict[str, str] = {}
    for k in keys:
        v = getattr(session, k, None)
        if v is None:
            out[k] = "missing"
        elif isinstance(v, dict):
            out[k] = f"dict(len={len(v)})"
        elif isinstance(v, list):
            out[k] = f"list(len={len(v)})"
        else:
            out[k] = type(v).__name__
    return out


def interop_check(session: Any) -> Dict[str, Any]:
    """Deterministic NiceGUI session interoperability audit (no physics)."""
    rep: Dict[str, Any] = {"ok": True, "checks": []}

    def _add(name: str, ok: bool, detail: str = "") -> None:
        rep["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)})
        if not ok:
            rep["ok"] = False

    _add("pd_last_outputs", isinstance(getattr(session, "pd_last_outputs", None), dict),
         "Point Designer artifact")
    _add("last_eval", isinstance(getattr(session, "last_eval", None), dict),
         "Last evaluate dict")
    _add("cmp_slot_a", getattr(session, "cmp_slot_a", None) is not None or True,
         "optional compare slot A")
    _add("systems_targets", True, "NiceGUI Systems Mode uses session fields directly")
    for k in ("last_precheck_report", "scan_cartography_report", "pareto_last", "trade_last"):
        present = getattr(session, k, None) is not None
        _add(f"artifact:{k}", True, "present" if present else "missing (optional)")

    return rep


def run_contract_validator(session: Any) -> Dict[str, Any]:
    """Static UI contract validator (Streamlit ui/app.py wiring audit)."""
    from ui.panel_contracts import get_panel_contracts
    from tools.interoperability.contract_validator import validate_ui_contracts

    contracts = get_panel_contracts()
    ss = {k: getattr(session, k, None) for k in dir(session) if not k.startswith("_")}
    return validate_ui_contracts(_root(), contracts, session_state=ss)


def governance_summary(session: Any) -> Dict[str, Any]:
    """Verdict-first governance KPIs for Control Room header."""
    ver = read_version()
    last = getattr(session, "pd_last_outputs", None) or getattr(session, "last_eval", None)
    verdict = "-"
    if isinstance(last, dict):
        run = last.get("run") or {}
        if isinstance(run, dict) and run.get("verdict"):
            verdict = str(run["verdict"])
        elif last.get("verdict"):
            verdict = str(last["verdict"])
    hygiene = hygiene_scan()
    return {
        "version": ver,
        "active_deck": str(getattr(session, "active_deck", "-")),
        "point_verdict": verdict,
        "hygiene_ok": bool(hygiene.get("ok")),
    }


def report_to_json_bytes(report: dict) -> bytes:
    return json.dumps(report, indent=2, sort_keys=True, default=str).encode("utf-8")
