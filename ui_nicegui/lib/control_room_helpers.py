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
CONST_TABS = ["Model Ledger", "Capability Matrix", "Assumptions", "Constraints", "Constraint Provenance", "Docs Library"]
DIAG_TABS = ["Gatechecks", "Interoperability", "Validation Envelopes", "Session", "Non-Feasibility Guide"]

CHRONICLE_TABS = [
    "Variable Registry",
    "Sensitivity Explorer",
    "Feasibility Map",
    "Knob Trade-Space",
    "Certified Search",
    "Interval Narrowing",
    "Local Forensics",
    "Study Dashboard",
]

ARTIFACT_TABS = ["Artifacts Explorer", "Run Library", "Export & Share", "Benchmark Reference"]

BENCHMARK_REFERENCE_ROWS: List[Dict[str, Any]] = [
    {"Tokamak": "ITER", "Country / Org": "Intl (EU/JP/US/etc.)", "Status": "Under construction", "SC type": "Nb₃Sn / NbTi (LTS)", "Major R (m)": 6.2, "Minor a (m)": 2.0, "B₀ on axis (T)": 5.3, "Ip (MA)": 15.0, "Primary role": "Burning plasma, Q≈10"},
    {"Tokamak": "JT-60SA", "Country / Org": "Japan–EU", "Status": "Commissioning", "SC type": "NbTi (LTS)", "Major R (m)": 3.0, "Minor a (m)": 1.0, "B₀ on axis (T)": 2.3, "Ip (MA)": 5.5, "Primary role": "Advanced plasma physics"},
    {"Tokamak": "WEST", "Country / Org": "France", "Status": "Operating", "SC type": "NbTi (LTS)", "Major R (m)": 2.5, "Minor a (m)": 0.5, "B₀ on axis (T)": 3.7, "Ip (MA)": 1.0, "Primary role": "Long-pulse, PFC/divertor"},
    {"Tokamak": "EAST", "Country / Org": "China", "Status": "Operating", "SC type": "NbTi (LTS)", "Major R (m)": 1.9, "Minor a (m)": 0.5, "B₀ on axis (T)": 3.5, "Ip (MA)": 1.0, "Primary role": "Long-pulse operation"},
    {"Tokamak": "KSTAR", "Country / Org": "Korea", "Status": "Operating", "SC type": "NbTi-based (LTS)", "Major R (m)": 1.8, "Minor a (m)": 0.5, "B₀ on axis (T)": 3.5, "Ip (MA)": 2.0, "Primary role": "Advanced tokamak scenarios"},
    {"Tokamak": "SST-1", "Country / Org": "India", "Status": "Operating", "SC type": "NbTi (LTS)", "Major R (m)": 1.1, "Minor a (m)": 0.2, "B₀ on axis (T)": 3.0, "Ip (MA)": 0.1, "Primary role": "SC tokamak development"},
    {"Tokamak": "TRIAM-1M", "Country / Org": "Japan", "Status": "Historical", "SC type": "Nb₃Sn (LTS)", "Major R (m)": 0.8, "Minor a (m)": 0.15, "B₀ on axis (T)": 8.0, "Ip (MA)": None, "Primary role": "High-field SC operation"},
    {"Tokamak": "HT-7", "Country / Org": "China", "Status": "Historical", "SC type": "LTS", "Major R (m)": 1.22, "Minor a (m)": 0.27, "B₀ on axis (T)": 2.0, "Ip (MA)": 0.2, "Primary role": "Precursor to EAST"},
    {"Tokamak": "SPARC", "Country / Org": "USA (MIT/CFS)", "Status": "Under construction", "SC type": "REBCO (HTS)", "Major R (m)": 1.85, "Minor a (m)": 0.57, "B₀ on axis (T)": 12.2, "Ip (MA)": 8.7, "Primary role": "Q>1, high-field compact"},
    {"Tokamak": "HH70", "Country / Org": "China (Energy Singularity)", "Status": "Operating", "SC type": "REBCO (HTS)", "Major R (m)": 0.7, "Minor a (m)": 0.28, "B₀ on axis (T)": 0.6, "Ip (MA)": None, "Primary role": "Full-HTS integration demo"},
    {"Tokamak": "HH170", "Country / Org": "China (Energy Singularity)", "Status": "Planned", "SC type": "REBCO (HTS)", "Major R (m)": None, "Minor a (m)": None, "B₀ on axis (T)": None, "Ip (MA)": None, "Primary role": "Reactor-relevant HTS tokamak"},
]

REFERENCE_GALLERY: List[Tuple[str, str]] = [
    ("ITER-like", "Large, conservative, physics-demonstration anchor; often stress and divertor constraints dominate."),
    ("SPARC-like", "Compact high-field concept; often HTS margin and structural stress dominate."),
    ("ARC-like", "HTS reactor class; often net-electric closure and blanket/TBR proxies dominate."),
    ("DEMO-like", "Plant realism anchor; often recirculating power and availability assumptions dominate."),
]

MIGRATION_GUIDE_DOC = "PROCESS_TO_SHAMS_MIGRATION_GUIDE.md"
CHAMPION_CASES_DOC = "CHAMPION_CASES.md"

LAUNCHPAD_DECK: Dict[str, str] = {
    "Migrate a PROCESS study to SHAMS": "Control Room",
    "Run a champion feasibility template": "Control Room",
    "Understand feasibility limits (cartography)": "Scan Lab",
    "Explore reactor concepts (Forge)": "Reactor Design Forge",
    "Review a finished case (Review Room)": "Reactor Design Forge",
    "Compare designs (Artifacts)": "Compare",
}

LAUNCHPAD_PATHS: List[Tuple[str, str, str]] = [
    (
        "Migrate a PROCESS study to SHAMS",
        "Recommended: Control Room → Constitution → Docs Library → PROCESS→SHAMS migration guide.",
        "- Open **`docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md`** (IN.DAT→PointInputs, MFILE→artifacts, CCFS propose-only)\n"
        "- Map knobs in **Point Designer**; treat NO-SOLUTION as valid\n"
        "- Cite `VERSION` + artifact SHA-256 — do **not** invent MFILE numbers or claim PROCESS retired.",
    ),
    (
        "Run a champion feasibility template",
        "Recommended: Control Room → Constitution → Docs Library → Champion cases; or CLI runner.",
        "- Open **`docs/CHAMPION_CASES.md`** (SPARC-class / STEP-like / conservative templates + NO-SOLUTION stories)\n"
        "- Reproduce with `python benchmarks/champions/run_champions.py`\n"
        "- Cite `VERSION` + case `citation_sha256` — class/like inspiration only; no PROCESS-retired claim.",
    ),
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


_HYGIENE_CACHE: Optional[Dict[str, Any]] = None


def hygiene_scan(*, force: bool = False) -> Dict[str, Any]:
    """Scan working tree for packaging violations vs dev-only cache artifacts.

    Result is process-cached — full-tree rglob is expensive; Control Room mounts
    call governance_summary often and must not walk the repo twice per switch.
    """
    global _HYGIENE_CACHE
    if _HYGIENE_CACHE is not None and not force:
        return dict(_HYGIENE_CACHE)
    root = _root()
    packaging_forbidden = ["gspulse_ui"]
    dev_cache_names = ["__pycache__", ".pytest_cache"]
    packaging_hits: List[str] = []
    dev_cache_hits: List[str] = []
    for name in packaging_forbidden:
        for h in root.rglob(name):
            packaging_hits.append(str(h))
    for name in dev_cache_names:
        for h in root.rglob(name):
            dev_cache_hits.append(str(h))
    for h in root.glob("run_st*"):
        packaging_hits.append(str(h))
    packaging_hits = sorted(set(packaging_hits))
    dev_cache_hits = sorted(set(dev_cache_hits))
    packaging_ok = len(packaging_hits) == 0
    _HYGIENE_CACHE = {
        "ok": packaging_ok,
        "packaging_ok": packaging_ok,
        "dev_cache_hits": dev_cache_hits,
        "hits": packaging_hits + dev_cache_hits,
    }
    return dict(_HYGIENE_CACHE)


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

    def _add(name: str, ok: bool, detail: str = "", *, required: bool = True) -> None:
        rep["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail), "required": required})
        if required and not ok:
            rep["ok"] = False

    _add("pd_last_outputs", isinstance(getattr(session, "pd_last_outputs", None), dict),
         "Point Designer artifact")
    _add("last_eval", isinstance(getattr(session, "last_eval", None), dict),
         "Last evaluate dict")
    _add(
        "cmp_slot_a",
        getattr(session, "cmp_slot_a", None) is not None,
        "present" if getattr(session, "cmp_slot_a", None) is not None else "missing (optional)",
        required=False,
    )
    _add("systems_targets", True, "NiceGUI Systems Mode uses session fields directly")
    for k in ("last_precheck_report", "scan_cartography_report", "pareto_last", "trade_last"):
        present = getattr(session, k, None) is not None
        _add(f"artifact:{k}", True, "present" if present else "missing (optional)")

    return rep


def run_contract_validator(session: Any) -> Dict[str, Any]:
    """Static wiring audit — NiceGUI scope (Streamlit uncontracted panels are informational)."""
    from ui.panel_contracts import get_panel_contracts
    from tools.interoperability.contract_validator import validate_ui_contracts

    contracts = get_panel_contracts()
    ss = {k: getattr(session, k, None) for k in dir(session) if not k.startswith("_")}
    rep = validate_ui_contracts(_root(), contracts, session_state=ss)
    uncontracted = list(rep.get("uncontracted_panels") or [])
    missing = list(rep.get("missing_functions") or [])
    empty_req = list(rep.get("empty_requires") or [])
    dup = rep.get("dup_required_keys") or {}
    nicegui_ok = len(dup) == 0
    rep["nicegui_ok"] = nicegui_ok
    rep["ok"] = nicegui_ok
    rep["streamlit_parity"] = {
        "missing_functions": len(missing),
        "uncontracted_panels": len(uncontracted),
        "empty_requires": len(empty_req),
        "note": "Legacy Streamlit ui/app.py contract drift — informational for NiceGUI Control Room.",
    }
    if isinstance(rep.get("summary"), dict):
        rep["summary"]["nicegui_ok"] = nicegui_ok
        rep["summary"]["streamlit_uncontracted"] = len(uncontracted)
    return rep


def governance_summary(session: Any) -> Dict[str, Any]:
    """Verdict-first governance KPIs for Control Room header."""
    from ui_nicegui.lib.cr_governance_helpers import design_confidence_class
    from ui_nicegui.lib.verdict_core import verdict_summary

    ver = read_version()
    last = getattr(session, "pd_last_outputs", None) or getattr(session, "last_eval", None)
    art = getattr(session, "pd_last_artifact", None)
    vs = verdict_summary(last) if isinstance(last, dict) else {"loaded": False}
    kpis = art.get("kpis") if isinstance(art, dict) else {}
    if not isinstance(kpis, dict):
        kpis = {}
    verdict = str(vs.get("verdict", "-")) if vs.get("loaded") else "-"
    hygiene = hygiene_scan()
    mirage = bool(last.get("mirage_flag_v402")) if isinstance(last, dict) else False
    pfus = None
    if isinstance(last, dict):
        pfus = last.get("Pfus_total_MW", last.get("Pfus_MW", last.get("P_fus_MW")))
    mechanism = "-"
    if vs.get("loaded") and not vs.get("feasible"):
        try:
            from ui_nicegui.lib.pd_parity_helpers import no_solution_atlas_summary

            atlas = no_solution_atlas_summary(last, design_intent=str(getattr(session, "design_intent", "")))
            mechanism = str(atlas.get("dominant_mechanism") or "-")
        except Exception:
            mechanism = "-"
    return {
        "version": ver,
        "active_deck": str(getattr(session, "active_deck", "-")),
        "point_verdict": verdict,
        "dominant": str(vs.get("dominant", "-")) if vs.get("loaded") else "-",
        "q_label": str(vs.get("q_label", "-")) if vs.get("loaded") else "-",
        "pfus_label": f"{pfus:.3g} MW" if isinstance(pfus, (int, float)) else "-",
        "mirage": mirage,
        "mechanism": mechanism,
        "design_class": design_confidence_class(art) if isinstance(art, dict) else "-",
        "feasible_hard": kpis.get("feasible_hard"),
        "hygiene_ok": bool(hygiene.get("packaging_ok", hygiene.get("ok"))),
    }


def report_to_json_bytes(report: dict) -> bytes:
    return json.dumps(report, indent=2, sort_keys=True, default=str).encode("utf-8")
