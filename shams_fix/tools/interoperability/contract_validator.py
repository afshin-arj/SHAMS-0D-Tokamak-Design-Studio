"""SHAMS UI interoperability contract validator (deterministic).

This module intentionally performs **no physics**, **no solvers**, and **no optimization**.
It validates:
  - Panel contract coverage (declared vs discoverable panel functions in ui/app.py)
  - Basic contract sanity (duplicate keys, empty requirements)
  - Optional runtime presence check for declared session_state keys

The goal is reviewer-safe wiring assurance: catch phantom/partial panels and
broken inter-panel promotion paths early.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple


def _discover_panel_function_names(app_py: Path) -> Set[str]:
    """Discover panel function names from ui/app.py via lightweight parsing.

    We do NOT import ui.app (avoid side effects / Streamlit execution).
    We scan text for `def <name>(` patterns.
    """
    txt = app_py.read_text(encoding="utf-8", errors="replace")
    out: Set[str] = set()
    # Conservative scan: only functions that look like SHAMS subpanels.
    # Typical naming in SHAMS: def _v123_something_panel(...):
    import re

    for m in re.finditer(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", txt, flags=re.MULTILINE):
        name = m.group(1)
        if name.startswith("_v") or name.startswith("_panel_"):
            out.add(name)
    return out


def validate_ui_contracts(
    repo_root: Path,
    contracts: Dict[str, Any],
    session_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Validate declared UI panel contracts vs discoverable panel functions.

    Args:
        repo_root: repository root (contains ui/app.py)
        contracts: mapping of panel_fn_name -> PanelContract-like object
        session_state: optional dict-like of current Streamlit session_state

    Returns:
        A JSON-serializable report.
    """
    app_py = repo_root / "ui" / "app.py"
    if not app_py.exists():
        raise FileNotFoundError(f"Expected ui/app.py at: {app_py}")

    discovered = _discover_panel_function_names(app_py)
    declared = set(contracts.keys())

    missing_functions = sorted([c for c in declared if c not in discovered])
    uncontracted_panels = sorted([p for p in discovered if p not in declared])

    # Contract sanity
    dup_required_keys: Dict[str, int] = {}
    empty_requires: List[str] = []
    key_freq: Dict[str, int] = {}
    contract_dump: Dict[str, Dict[str, Any]] = {}

    for name, c in contracts.items():
        # dataclass or object with attributes
        try:
            d = asdict(c)  # type: ignore[arg-type]
        except Exception:
            d = {
                "panel_fn_name": getattr(c, "panel_fn_name", name),
                "title": getattr(c, "title", ""),
                "requires": list(getattr(c, "requires", []) or []),
                "optional": list(getattr(c, "optional", []) or []),
                "notes": getattr(c, "notes", ""),
                "blocked_if_true_keys": list(getattr(c, "blocked_if_true_keys", []) or []),
            }
        req = list(d.get("requires") or [])
        if len(req) == 0:
            empty_requires.append(name)
        # key frequency counts
        for k in req + list(d.get("optional") or []):
            key_freq[k] = int(key_freq.get(k, 0)) + 1
        # duplicates inside requires
        for k in set(req):
            if req.count(k) > 1:
                dup_required_keys[f"{name}:{k}"] = req.count(k)
        contract_dump[name] = d

    runtime_presence: Dict[str, bool] = {}
    if session_state is not None:
        # Check declared required keys (only)
        for name, c in contracts.items():
            req: Iterable[str] = getattr(c, "requires", []) or []
            for k in req:
                runtime_presence[k] = bool(k in session_state)

    # Overall status
    ok = (
        len(missing_functions) == 0
        and len(empty_requires) == 0
        and len(dup_required_keys) == 0
    )

    return {
        "ok": bool(ok),
        "summary": {
            "declared_contracts": len(declared),
            "discovered_panels": len(discovered),
            "missing_functions": len(missing_functions),
            "uncontracted_panels": len(uncontracted_panels),
            "empty_requires": len(empty_requires),
            "dup_required_key_entries": len(dup_required_keys),
        },
        "missing_functions": missing_functions,
        "uncontracted_panels": uncontracted_panels,
        "empty_requires": sorted(empty_requires),
        "dup_required_keys": dup_required_keys,
        "key_frequency": dict(sorted(key_freq.items(), key=lambda kv: (-kv[1], kv[0]))),
        "runtime_required_key_presence": runtime_presence,
        "contracts": contract_dump,
    }
