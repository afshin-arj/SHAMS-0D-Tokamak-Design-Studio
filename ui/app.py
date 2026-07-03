"""
Phase-1 Clean Point Design UI (Streamlit)

Professional, single-command UI for:
- Point Designer: evaluate one operating point and show pass/fail constraint dashboard
- Scan Lab: run parameter scans and explore results
- Results Explorer: filter/sort/export feasible points

Design goals:
- No JS toolchain required (runs on pure Python).
- Physics and models live in src/ (imported as a library).
- All models remain explicit proxies (Phase-1), with conservative pass/fail gates.
"""

from __future__ import annotations

import subprocess


# --- Branding (v175.4) ---
APP_NAME = 'Tokamak 0-D Design Studio'
APP_SUBTITLE = 'Feasibility-first, constraint-authoritative 0-D tokamak design'
APP_AUTHOR = 'Afshin Arjhangmehr'
APP_YEAR = 2026
APP_COPYRIGHT = '© 2026 Afshin Arjhangmehr'

def _render_branding_header():
    # Keep the main title crisp and readable across zoom levels.
    st.markdown(f"# {APP_NAME}")
    st.caption(APP_SUBTITLE)

def _render_footer():
    """Render a persistent footer (safe HTML/CSS injection)."""
    st.markdown(
        f"""
        <style>
        .shams-footer {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            text-align: center;
            font-size: 12px;
            color: rgba(49,51,63,0.7);
            padding: 6px 0;
            background: rgba(255,255,255,0.92);
            border-top: 1px solid rgba(49,51,63,0.15);
            z-index: 1000;
        }}
        .block-container {{
            padding-bottom: 3rem;
        }}
        </style>
        <div class="shams-footer">{APP_COPYRIGHT}</div>
        """,
        unsafe_allow_html=True,
    )


def _attach_common_metadata(d: dict) -> dict:
    """Attach canonical author/software metadata to an artifact-like dict.

    v264.0 adds governance overlays:
    - citation completeness (for authority overrides)
    - experimental evidence anchoring on constraint records
    """
    if not isinstance(d, dict):
        return d

    d.setdefault("software", APP_NAME)
    d.setdefault("author", APP_AUTHOR)
    d.setdefault("year", APP_YEAR)
    d.setdefault("copyright", APP_COPYRIGHT)

    # Point Designer governance (frozen): embed in every artifact so that
    # downstream exports and bundles always carry the evaluation/exploration boundary.
    d.setdefault(
        "point_designer",
        {
            "status": "frozen",
            "frozen_since": "v179.2",
            "role": "constraint-authoritative 0-D operating point evaluator",
            "note": "No optimization, relaxation, or exploration occurs in Point Designer. Exploration is performed in Systems Mode, which calls Point Designer as a fixed evaluator.",
            "non_goals": [
                "optimization",
                "transport",
                "time evolution",
                "design space exploration",
                "equilibrium solve",
                "SOL / edge code replacement",
                "neutronics Monte-Carlo replacement",
            ],
        },
    )

    # Reproducibility stamp: keep Point Designer artifacts audit-ready.
    # (UI-only; does not affect physics.)
    try:
        from pathlib import Path as _Path
        import platform as _platform
        import sys as _sys
        import datetime as _dt
        _ver_path = _Path(__file__).resolve().parents[1] / "VERSION"
        _ver = "unknown"
        if _ver_path.exists():
            _ver = _ver_path.read_text(encoding="utf-8").strip().splitlines()[0]
        d.setdefault("shams_version", _ver)
        d.setdefault(
            "build_utc",
            _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
        d.setdefault("python", _sys.version.split("\n")[0])
        d.setdefault("platform", _platform.platform())
    except Exception:
        pass

    # --- Governance overlays (v264.0) ---
    try:
        from src.governance.citations import validate_authority_overrides, summarize_citation_completeness
        issues = validate_authority_overrides(d.get("authority_overrides", {}))
        d["citation_completeness"] = summarize_citation_completeness(issues)
    except Exception:
        pass

    try:
        from pathlib import Path as _Path
        from src.governance.experimental_anchoring import load_anchoring_db, annotate_constraints, summarize_evidence
        dbp = _Path(ROOT) / "benchmarks"/ "experimental"/ "data"/ "anchors_default.json"
        if dbp.exists() and isinstance(d.get("constraints"), list):
            db = load_anchoring_db(dbp)
            d["constraints"] = annotate_constraints(d["constraints"], db)
            d["experimental_evidence_summary"] = summarize_evidence(d["constraints"])
    except Exception:
        pass

    return d
# ---- import path bootstrap (must be before any local imports) ----
import os as _os, sys as _sys
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
_SRC = _os.path.join(_ROOT, "src")
if _SRC not in _sys.path:
    _sys.path.insert(0, _SRC)
# ---------------------------------------------------------------

# Expose repo root for downstream helpers
ROOT = _ROOT
SRC = _SRC

import io
import json
import os
import sys
import math

# --- JSON export helpers (cycle-safe, deterministic) ---
def _shams_json_sanitize(obj, _seen=None, _depth: int = 0, _max_depth: int = 25):
    import math
    if _seen is None:
        _seen = set()
    if _depth > _max_depth:
        return "<max_depth>"
    if obj is None or isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, float):
        if not math.isfinite(obj):
            return None
        return obj
    oid = id(obj)
    if oid in _seen:
        return "<circular_ref>"
    if isinstance(obj, dict):
        _seen.add(oid)
        out = {}
        for k, v in obj.items():
            try:
                kk = str(k)
            except Exception:
                kk = "<key>"
            if kk in {"_session_state", "session_state", "__streamlit__", "__ctx__"}:
                continue
            out[kk] = _shams_json_sanitize(v, _seen, _depth + 1, _max_depth)
        _seen.discard(oid)
        return out
    if isinstance(obj, (list, tuple, set)):
        _seen.add(oid)
        out = [_shams_json_sanitize(v, _seen, _depth + 1, _max_depth) for v in list(obj)]
        _seen.discard(oid)
        return out
    try:
        import dataclasses
        if dataclasses.is_dataclass(obj):
            return _shams_json_sanitize(dataclasses.asdict(obj), _seen, _depth + 1, _max_depth)
    except Exception:
        pass
    try:
        return str(obj)
    except Exception:
        return "<unserializable>"

def _shams_json_dumps(obj, **kwargs):
    import json as _json
    safe = _shams_json_sanitize(obj)
    return _json.dumps(safe, **kwargs)

# ----------------------------------------------------

import random
import datetime
import time
import concurrent.futures
import queue
import threading
from dataclasses import asdict, fields, replace
from typing import Dict, Any, List, Tuple

import html

import pandas as pd
import numpy as np
from decision.kpis import headline_kpis

import streamlit as st
from ui.tablekit import install_expandable_tables

# --- Optional plotting dependency (matplotlib) ---
# Matplotlib is intentionally optional in SHAMS. The UI must never crash if it is missing.
try:  # pragma: no cover (availability depends on user environment)
    import matplotlib.pyplot as plt  # type: ignore
    _HAVE_MPL = True
except Exception:  # pragma: no cover
    plt = None  # type: ignore
    _HAVE_MPL = False

# --- Global UI preference: make all tables collapsible to prevent scroll walls
if "ui_tablekit_enabled"not in st.session_state:
    st.session_state["ui_tablekit_enabled"] = True
if "ui_tablekit_default_expanded"not in st.session_state:
    st.session_state["ui_tablekit_default_expanded"] = False

# --- v327.0: Design State Graph (DSG) — inter-panel continuity (exploration layer)
_DSG_SNAPSHOT_PATH = "artifacts/dsg/current_dsg.json"
from typing import Any, Optional
try:
    from src.dsg import DesignStateGraph  # type: ignore
except Exception:
    try:
        from dsg import DesignStateGraph  # type: ignore
    except Exception:
        DesignStateGraph = None  # type: ignore

if "_shams_dsg"not in st.session_state and DesignStateGraph is not None:
    try:
        st.session_state["_shams_dsg"] = DesignStateGraph.load(_DSG_SNAPSHOT_PATH)
    except Exception:
        st.session_state["_shams_dsg"] = DesignStateGraph()

def _dsg_save_best_effort() -> None:
    try:
        if DesignStateGraph is None:
            return
        g = st.session_state.get("_shams_dsg")
        if g is None:
            return
        g.save(_DSG_SNAPSHOT_PATH)
    except Exception:
        return

def _dsg_record_best_effort(*, inp: Any, res: Any, origin: str, parents: Optional[list[str]] = None, tags: Optional[list[str]] = None, edge_kind: Optional[str] = None, edge_note: str = "") -> None:
    """Record an evaluation into the DSG if available.

    This is an exploration-layer side effect only; it must not affect truth.
    """
    try:
        if DesignStateGraph is None:
            return
        g = st.session_state.get("_shams_dsg")
        if g is None:
            return
        out = getattr(res, "out", {}) if res is not None else {}
        ok = bool(getattr(res, "ok", True))
        msg = str(getattr(res, "message", "") or "")
        el = float(getattr(res, "elapsed_s", 0.0) or 0.0)
        node = g.record(inp=inp, out=out, ok=ok, message=msg, elapsed_s=el, origin=str(origin), parents=parents, tags=tags, edge_kind=edge_kind, edge_note=edge_note)
        st.session_state["active_design_node_id"] = node.node_id
        _dsg_save_best_effort()
    except Exception:
        return

def _dsg_evaluator(*, origin: str = "UI", **evaluator_kwargs: Any):
    """Construct an Evaluator wrapper that records evaluations into DSG.

    This is an exploration-layer adapter only.
    """
    try:
        from src.evaluator.core import Evaluator  # type: ignore
    except Exception:
        from evaluator.core import Evaluator  # type: ignore

    # Evaluator construction can be expensive. Cache the base evaluator instance deterministically
    # so UI reruns (tab switches, widget edits) do not rebuild heavy objects.
    @st.cache_resource(show_spinner=False)
    def _cached_evaluator(**kwargs: Any):
        return Evaluator(**kwargs)

    ev = _cached_evaluator(**evaluator_kwargs)

    class _Wrap:
        def __init__(self, _ev: Any, _origin: str):
            self._ev = _ev
            self._origin = str(_origin)

        def evaluate(self, inp: Any, Paux_for_Q_MW: Optional[float] = None):
            res = self._ev.evaluate(inp, Paux_for_Q_MW=Paux_for_Q_MW)
            parent = st.session_state.get("dsg_selected_node_id") or st.session_state.get("active_design_node_id")
            kind = st.session_state.get("dsg_context_edge_kind") or "derived"
            parents = [str(parent)] if parent else None
            _dsg_record_best_effort(inp=inp, res=res, origin=self._origin, parents=parents, edge_kind=str(kind))
            return res

        def get(self, *args: Any, **kwargs: Any):
            return self._ev.get(*args, **kwargs)

        def cache_stats(self):
            return self._ev.cache_stats()

        def reset_cache_stats(self):
            return self._ev.reset_cache_stats()

    return _Wrap(ev, origin)


def _ui_evaluate(
    inp: Any,
    *,
    origin: str = "UI",
    Paux_for_Q_MW: Optional[float] = None,
    **evaluator_kwargs: Any,
) -> Dict[str, Any]:
    """Route UI point evaluation through the Evaluator choke point (PROPOSAL-008)."""
    return _dsg_evaluator(origin=origin, **evaluator_kwargs).evaluate(inp, Paux_for_Q_MW=Paux_for_Q_MW).out


install_expandable_tables(st)

from ui.icons import label as ui_label, render_mode_scope
from ui.dsg_panel import render_dsg_sidebar
# ---- SHAMS UX guardrails: global run lock + fusion-expert notifications
from ui import runlock as _shams_runlock
import atexit as _shams_atexit
import time as _shams_time
import uuid as _shams_uuid
import re as _shams_re

if "_shams_app_start_ts"not in st.session_state:
    st.session_state["_shams_app_start_ts"] = _shams_time.time()
if "_shams_owner_token"not in st.session_state:
    st.session_state["_shams_owner_token"] = str(_shams_uuid.uuid4())

def _shams_lock_banner():
    locked, task, started, is_owner = _shams_runlock.status(st.session_state.get("_shams_owner_token"), app_start_ts=st.session_state.get("_shams_app_start_ts"))
    if locked and task:
        age_s = int(_shams_time.time() - float(started or _shams_time.time()))
        badge = "Shot in Progress"if not is_owner else "Running Sequence"
        st.sidebar.info(f"{badge}: **{task}** · t+{age_s}s")
    return locked, task, started, is_owner

def _shams_is_solver_label(label: str) -> bool:
    # Freeze only *solver* actions, not navigation / downloads.
    return bool(_shams_re.search(r"\b(evaluate|solve|run|build|compute|scan|pareto|search|atlas|trajectory|candidates)\b", label, flags=_shams_re.I))

# Monkeypatch st.button to enforce lock on solver actions
_shams__orig_button = st.button
def _shams_button(label, *args, **kwargs):
    locked, task, started, is_owner = _shams_runlock.status(st.session_state.get("_shams_owner_token"), app_start_ts=st.session_state.get("_shams_app_start_ts"))
    label_str = str(label)
    if locked and _shams_is_solver_label(label_str) and not is_owner:
        kwargs["disabled"] = True
        return _shams__orig_button(label, *args, **kwargs)

    clicked = _shams__orig_button(label, *args, **kwargs)
    if clicked and _shams_is_solver_label(label_str):
        # Do NOT acquire the global run-lock here.
        # Streamlit reruns can cause a deadlock if acquisition happens before the solver call stack.
        locked2, task2, started2, is_owner2 = _shams_runlock.status(
            st.session_state.get("_shams_owner_token"),
            app_start_ts=st.session_state.get("_shams_app_start_ts"),
        )
        if locked2 and (not is_owner2):
            try:
                st.toast("Another sequence is already running. Wait for the Black‑Box Chronicle to clear.")
            except Exception:
                pass
            return False
    return clicked

st.button = _shams_button

# Show lock banner early (Control Ledger will inherit this)
_shams_lock_banner()

# --- v327.1: DSG selector + lineage breadcrumb (sidebar)
try:
    from ui.dsg_panel import render_dsg_sidebar  # type: ignore
    _g = st.session_state.get("_shams_dsg")
    if _g is not None:
        render_dsg_sidebar(_g)
        try:
            _sel = st.session_state.get("dsg_selected_node_id") or getattr(_g, "active_node_id", None)
            if _sel:
                st.caption(f"Active design node: `{_sel}` · lineage edge kind: `{st.session_state.get('dsg_context_edge_kind','derived')}`")
        except Exception:
            pass
except Exception:
    pass


# ---- Systems solver adapter imports (v178.9) ----
# UI directly builds SolverRequest objects for Systems Mode solves.
# Some deployments expose `src/` modules as top-level packages; keep a robust fallback.
try:
    from solvers import SolverRequest, DefaultTargetSolverBackend, solve_request  # type: ignore
except Exception:  # pragma: no cover
    from src.solvers import SolverRequest, DefaultTargetSolverBackend, solve_request  # type: ignore

from pathlib import Path
from tools.activity_log import get_logger as _get_activity_logger

# Global repo root + activity logger (Asia/Tehran)
REPO_ROOT = Path(__file__).resolve().parent.parent

# Canonical base directory for UI-resolved repo paths.
# Some panels historically referenced BASE_DIR; keep it stable and deterministic.
BASE_DIR = REPO_ROOT

def _activity_logger():
    lg = _get_activity_logger(st, REPO_ROOT, tz_name="Asia/Tehran")
    # One-time marker so users can confirm logging is working
    if "activity_log_inited"not in st.session_state:
        st.session_state["activity_log_inited"] = True
        try:
            if bool(st.session_state.get("activity_log_auto", True)):
                lg.log_event("UI", "LogInitialized", {"tz": "Asia/Tehran"})
        except Exception:
            pass
    return lg

def _alog(mode: str, action: str, payload: dict | None = None):
    try:
        if bool(st.session_state.get("activity_log_auto", True)):
            _activity_logger().log_event(mode, action, payload or {})
    except Exception:
        pass



def _invalidate_mode_caches(reason: str = "") -> None:
    """Clear cached outputs/artifacts across modes when a truth-relevant UI contract changes.

    This prevents stale Telemetry (e.g., NaN KPIs) after changing intent/machine type/policy.
    Deterministic: only clears UI caches; never changes evaluator physics.
    """
    try:
        keys = [
            # Point Designer
            "pd_last_outputs","pd_last_artifact","pd_last_log_lines","pd_last_run_ts","pd_last_inputs_hash",
            "pd_last_forensics","pd_last_forensics_inputs_hash",
            "last_point_out","last_point_inp","last_solver_log",
            # Systems Mode
            "systems_last_solve_artifact","systems_last_outputs","systems_last_inputs_hash",
            "systems_targets","systems_variables","systems_last_log_lines",
            # Scan Lab / Cartography
            "scan_cartography_artifact","scan_last_run","scan_last_outputs",
            # Pareto / Optimizer
            "opt_last_run_id","opt_last_meta","opt_last_records","opt_last_best",
            # Publication Benchmarks UI caches
            "pb_last_pack","pb_last_delta","pb_last_topology",
            # Compare
            "cmp_slot_A","cmp_slot_B","cmp_slot_A_meta","cmp_slot_B_meta",
        ]
        for k in keys:
            st.session_state.pop(k, None)
        if reason:
            st.session_state["ui_last_invalidation_reason"] = str(reason)
    except Exception:
        pass



def _alog_exc(mode: str, action: str, exc: BaseException):
    try:
        if bool(st.session_state.get("activity_log_auto", True)):
            _activity_logger().log_exception(mode, action, exc)
    except Exception:
        pass


# --- Forward-definition bootstrap (v175.6) ---
# --- Forward-definition bootstrap (v175.6.2) ---
def _bootstrap_forward_defs(target_names=None) -> None:
    """Predefine later top-level defs so early UI can reference them.

    Streamlit executes this script top-to-bottom. Some panels are defined later
    in this file but referenced earlier (e.g. by Panel Availability Map).
    This helper AST-parses *this* file and execs top-level defs (functions/classes)
    into the current globals() *without* executing their bodies.

    If `target_names` is provided, only those defs are loaded.
    """
    try:
        import ast
        from pathlib import Path

        src = Path(__file__).read_text(encoding="utf-8")
        mod = ast.parse(src)
        g = globals()

        targets = set(target_names) if target_names else None

        def _allow(name: str) -> bool:
            if not name:
                return False
            if targets is not None and name not in targets:
                return False
            # Only bootstrap panels and key helpers; avoid random internals.
            if name.startswith("_v"):
                return True
            if name in {"_render_with_contract", "_resolve_panel_function"}:
                return True
            return False

        for node in mod.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            name = getattr(node, "name", None)
            if not _allow(name):
                continue
            if name in g:
                continue
            try:
                code = compile(ast.Module([node], type_ignores=[]), filename=str(__file__), mode="exec")
                exec(code, g, g)
            except Exception:
                # Best-effort; skip anything that can't be safely defined.
                continue
    except Exception:
        return

_bootstrap_forward_defs()

from ui.panel_availability import PanelState, PanelStatus, default_status
from ui.panel_contracts import get_panel_contracts
from ui.state import SessionStateModel


# =====================
# Phase-1 UI Stabilization: early-safe state helpers (v372.8)
# =====================
# Rationale: prevent forward-reference failures and tab-scope leakage under Streamlit rerun semantics.
# These helpers are intentionally minimal and deterministic; they do not modify physics truth.

def _v92_state_get():
    import streamlit as st
    st.session_state.setdefault("shams_state", SessionStateModel())
    s = st.session_state["shams_state"]
    if getattr(s, "run_history", None) is None:
        s.run_history = []
    if getattr(s, "pinned_run_ids", None) is None:
        s.pinned_run_ids = []
    return s

def _v92_state_clear_point():
    import streamlit as st
    s = _v92_state_get()
    s.last_point_inputs = None
    s.last_point_outputs = None
    s.last_point_artifact = None
    s.last_point_radial_png = None
    for k in ["pd_last_outputs", "pd_last_artifact", "pd_last_radial_png_bytes"]:
        if k in st.session_state:
            del st.session_state[k]

def _phase1_stabilize_cache_aliases() -> None:
    """Maintain canonical cache keys while preserving backward-compat keys.

    Canonical (Phase-1 contract):
      - pd_last_outputs
      - systems_last_solution
      - scan_last_grid
      - pareto_last_front
    """
    import streamlit as st
    ss = st.session_state

    # Systems
    if "systems_last_solution"not in ss and "last_systems_solution"in ss:
        ss["systems_last_solution"] = ss.get("last_systems_solution")

    # Scan
    if "scan_last_grid"not in ss:
        if "scan_last_outputs"in ss:
            ss["scan_last_grid"] = ss.get("scan_last_outputs")
        elif "scan_cartography_artifact"in ss:
            ss["scan_last_grid"] = ss.get("scan_cartography_artifact")

    # Pareto
    if "pareto_last_front"not in ss and "pareto_last"in ss:
        ss["pareto_last_front"] = ss.get("pareto_last")

    # Point Designer: keep legacy aliases alive
    if "pd_last_outputs"in ss and "last_point_out"not in ss:
        ss["last_point_out"] = ss.get("pd_last_outputs")
    if "pd_last_artifact"in ss and "last_point_artifact"not in ss:
        ss["last_point_artifact"] = ss.get("pd_last_artifact")


from ui.pareto_language import PARETO_LOCK_LINE, PARETO_OPTIMAL_DEF, TRUST_BOUNDARIES, FREEZE_STAMP
from ui.optimizer_console import render_external_optimizer_launcher, render_optimizer_evidence_packs
from ui.language_freeze import CANON as _LANG, FORBIDDEN_PHRASES as _FORBIDDEN
from ui.decks.point_designer_hooks import (
    render_point_designer_hero,
    render_point_designer_trace,
    render_point_designer_export,
    render_point_designer_constraint_diff,
    render_point_designer_no_solution_atlas,
)
from ui.decks.system_suite_hooks import render_system_suite_header
from ui.authority_dashboard import render_overlay_authority_dashboard, merge_overlay_session_into_inputs
from ui.session_api import set_point_evaluation

try:
    from schema.governance_presets import apply_governance_preset, tritium_tight_closure_default
except ImportError:
    from src.schema.governance_presets import apply_governance_preset, tritium_tight_closure_default

# --- UI helpers (v87, additive) ---

# --- Panel Availability Map helpers (v174, additive) ---
def _dedupe_checks(checks_list):
    """Remove duplicate checks while preserving order."""
    seen = set()
    out = []
    for c in (checks_list or []):
        key = None
        try:
            if isinstance(c, dict):
                key = c.get("id") or c.get("name") or c.get("title")
            else:
                key = getattr(c, "id", None) or getattr(c, "name", None) or getattr(c, "title", None)
        except Exception:
            key = None
        if key is None:
            key = repr(c)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out

_PANEL_FN_CACHE = {}

def _resolve_panel_function(fn_name: str):
    """Resolve a panel function by name across the codebase.
    Streamlit runs ui/app.py as __main__, so we must search broadly.
    Uses a cache to avoid repeated module walks.
    """
    if not fn_name:
        return None
    if fn_name in _PANEL_FN_CACHE:
        return _PANEL_FN_CACHE[fn_name]

    # Fast paths
    try:
        cand = globals().get(fn_name)
        if callable(cand):
            _PANEL_FN_CACHE[fn_name] = cand
            return cand
    except Exception:
        pass

    import sys
    try:
        main_mod = sys.modules.get("__main__")
        cand = getattr(main_mod, fn_name, None) if main_mod is not None else None
        if callable(cand):
            _PANEL_FN_CACHE[fn_name] = cand
            return cand
    except Exception:
        pass

    
    # If still not found, try bootstrapping the specific def from later in this file.
    try:
        _bootstrap_forward_defs([fn_name])
        cand = globals().get(fn_name)
        if callable(cand):
            _PANEL_FN_CACHE[fn_name] = cand
            return cand
    except Exception:
        pass

# Robust path: import-walk ui.* modules and search for attribute
    try:
        import ui as _ui_pkg
        import pkgutil as _pkgutil
        import importlib as _importlib
        for m in _pkgutil.walk_packages(_ui_pkg.__path__, _ui_pkg.__name__ + "."):
            modname = m.name
            try:
                mod = _importlib.import_module(modname)
            except Exception:
                continue
            try:
                cand = getattr(mod, fn_name, None)
                if callable(cand):
                    _PANEL_FN_CACHE[fn_name] = cand
                    return cand
            except Exception:
                continue
    except Exception:
        pass

    _PANEL_FN_CACHE[fn_name] = None
    return None


def _render_panel_status_card(status: PanelStatus):
    import streamlit as st
    if status.state == PanelState.AVAILABLE:
        return
    if status.state == PanelState.NOT_GENERATED:
        st.info(status.message)
        if status.missing:
            st.write("Missing artifacts:")
            st.code("\n".join(status.missing))
        return
    if status.state == PanelState.BLOCKED:
        st.warning(status.message)
        return
    if status.state == PanelState.NOT_APPLICABLE:
        st.caption(status.message)
        return
    if status.state == PanelState.DEMO_SUBSTITUTED:
        st.caption(status.message)
        return

def _render_with_contract(panel_fn_name: str, panel_callable):
    import streamlit as st
    contracts = get_panel_contracts()
    c = contracts.get(panel_fn_name)
    if c is None:
        # No contract registered: still render, but never allow silent emptiness
        try:
            panel_callable()
        except Exception as e:
            st.warning(f"Panel error: {e}")
        return
    from ui.panel_availability import evaluate_contract
    status = evaluate_contract(c, st.session_state)
    if status.state != PanelState.AVAILABLE:
        _render_panel_status_card(status)
        return
    try:
        panel_callable()
    except Exception as e:
        st.warning(f"Panel error: {e}")



def _v175_panel_availability_map_panel():
    import streamlit as st
    from ui.panel_contracts import get_panel_contracts
    from ui.panel_availability import evaluate_contract, PanelState

    st.subheader("Panel Availability Map")
    st.caption("Self-explaining UI: every panel reports whether it is available, missing required artifacts, blocked, or not applicable.")

    contracts = get_panel_contracts()
    rows = []
    counts = {s.name: 0 for s in PanelState}

    for fn_name, c in contracts.items():
        status = evaluate_contract(c, st.session_state)
        counts[status.state.name] = counts.get(status.state.name, 0) + 1
        rows.append({
            "panel_fn": fn_name,
            "title": c.title,
            "state": status.state.name,
            "missing_required": ", ".join(status.missing or []),
        })

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Available", counts.get("AVAILABLE", 0))
    c2.metric("Not generated", counts.get("NOT_GENERATED", 0))
    c3.metric("Blocked", counts.get("BLOCKED", 0))
    c4.metric("Not applicable", counts.get("NOT_APPLICABLE", 0))
    c5.metric("Demo-substituted", counts.get("DEMO_SUBSTITUTED", 0))

    states = ["ALL"] + sorted({r["state"] for r in rows})
    pick = st.selectbox("Filter by state", states, index=0, key="v175_pam_filter")
    show = [r for r in rows if pick == "ALL"or r["state"] == pick]

    st.write("Panels:")
    st.dataframe(show, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("### Open a panel here")
    opts = ["(select)"] + [f'{r["title"]}  -  {r["panel_fn"]}' for r in rows]
    sel = st.selectbox("Choose panel", opts, index=0, key="v175_pam_open_pick")
    if sel != "(select)":
        fn_name = sel.rsplit("-", 1)[-1].strip()
        st.session_state["v175_pam_focus"] = fn_name

    focus = st.session_state.get("v175_pam_focus")
    if focus:
        st.markdown(f"#### Focus: `{focus}`")
        fn = _resolve_panel_function(focus)
        if callable(fn):
            _render_with_contract(focus, fn)
        else:
            st.warning("Selected panel function not found in this UI build.")

def _render_provenance_sidebar():
    with st.sidebar:
        st.subheader("Run Provenance")
        try:
            v = (BASE_DIR / "VERSION").read_text().strip()
        except Exception:
            v = "unknown"
        st.code(v)
        st.markdown("---")
        st.subheader("Session")
        _exit_confirm = st.checkbox("Confirm exit", value=False, key="shams_exit_confirm")
        if st.button("Exit SHAMS", type="primary", use_container_width=True, disabled=not _exit_confirm, key="shams_exit_btn"):
            st.info("SHAMS UI shutdown requested by user.")
            # Hard-exit is the only reliable cross-platform Streamlit shutdown mechanism.
            _os._exit(0)
        st.caption("Authoritative feasibility lives in SHAMS core. Sandbox results are non-authoritative.")

def _feasibility_narrative(point):
    feas = point.get("feasible", False)
    mins = point.get("min_signed_margin", None)
    acts = point.get("active_constraints", [])
    if feas:
        return f"Feasible. Min margin = {mins:.3g}."if isinstance(mins, (int,float)) else "Feasible."
    return f"Infeasible. Limiting constraints: {', '.join(acts[:3]) if acts else 'unknown'}."

def _margin_waterfall(records):
    # records: list of dicts with name + signed_margin
    import pandas as pd
    rows = []
    for r in records:
        name = r.get("name","")
        sm = r.get("signed_margin", None)
        if name and isinstance(sm,(int,float)):
            rows.append({"constraint": name, "signed_margin": sm})
    if not rows:
        st.info("No constraint margins available.")
        return
    df = pd.DataFrame(rows).sort_values("signed_margin")
    st.bar_chart(df.set_index("constraint"))


# ---------------------------------------------------------------------------
# Session-state initialization (prevents AttributeError on first run)
# ---------------------------------------------------------------------------
def _init_session_state() -> None:

    # NOTE: phase1_core import happens later in this file. We defensively import
    # PointInputs here to avoid NameError during early session-state init.
    try:
        from phase1_core import PointInputs as _PointInputs
    except Exception:
        _PointInputs = None

    defaults = {
        # If PointInputs is not available for any reason, fall back to None and let
        # downstream code initialize it in a controlled path.
        "last_point_inp": (_PointInputs(R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=20.0)
                           if _PointInputs is not None else None),
        "last_point_out": None,
        "last_solver_log": None,
        "explain_mode": True,
        "expert_mode": False,
        "design_intent": "Power Reactor (net-electric)",
        "scan_df": None,
        "scan_meta": None,
        "scan_log_lines": [],
        "scan_log_text": "",
        "scan_progress": 0.0,
        "scan_queue": [],
        "scan_running": False,
        "scan_future": None,
        "scan_executor": None,

        # Phase 7+ UI persistence
        "de_best_inputs": None,
        "de_best_out": None,
        "de_history": None,
        "robustness_result": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_session_state()
# _sync_point_designer_from_last_point_inp()


# Stable Streamlit keys for Point Designer widgets (presets rely on these)
PD_KEYS = {
    "R0_m": "pd_R0_m",
    "a_m": "pd_a_m",
    "kappa": "pd_kappa",
    "delta": "pd_delta",
    "Bt_T": "pd_Bt_T",
    "Ti_keV": "pd_Ti_keV",
    "Paux_MW": "pd_Paux_MW",
    "H98_tgt": "pd_target_H98",
    "Q_tgt": "pd_target_Q",
    "Ip_lo": "pd_Ip_lo",
    "Ip_hi": "pd_Ip_hi",
    "fG_lo": "pd_fG_lo",
    "fG_hi": "pd_fG_hi",
    # Additional stable keys (used for preset propagation)
    "Ti_over_Te": "pd_Ti_over_Te",
    "Paux_for_Q": "pd_Paux_for_Q",
    "magnet_technology": "pd_magnet_technology",
    "Tcoil_K": "pd_Tcoil_K",
    "include_magnet_technology_authority_v400": "pd_include_magnet_technology_authority_v400",
    "magnet_margin_min_v400": "pd_magnet_margin_min_v400",
    "b_margin_min_v400": "pd_b_margin_min_v400",
    "j_margin_min_v400": "pd_j_margin_min_v400",
    "stress_margin_min_v400": "pd_stress_margin_min_v400",
    "sc_margin_min_v400": "pd_sc_margin_min_v400",
    "t_margin_min_v400": "pd_t_margin_min_v400",
    "p_tf_ohmic_margin_min_v400": "pd_p_tf_ohmic_margin_min_v400",


    # v318.0 profile bundle knobs (stable keys for presets and promotion)
    "profile_mode": "pd_profile_mode",
    "profile_alpha_T": "pd_profile_alpha_T",
    "profile_alpha_n": "pd_profile_alpha_n",
    "profile_shear_shape": "pd_profile_shear_shape",
    "pedestal_enabled": "pd_pedestal_enabled",
    "pedestal_width_a": "pd_pedestal_width_a",
    "include_bootstrap_pressure_selfconsistency": "pd_include_bootstrap_pressure_selfconsistency",
    "f_bootstrap_consistency_abs_max": "pd_f_bootstrap_consistency_abs_max",

    # v371.0 transport contract library keys
    "include_transport_contracts_v371": "pd_include_transport_contracts_v371",
    "H_required_max_optimistic": "pd_H_required_max_optimistic",
    "H_required_max_robust": "pd_H_required_max_robust",

    # v396.0 transport envelope 2.0 keys
    "include_transport_envelope_v396": "pd_include_transport_envelope_v396",
    "transport_spread_max_v396": "pd_transport_spread_max_v396",
    "include_tauE_user_scaling_v396": "pd_include_tauE_user_scaling_v396",
    "tauE_user_C_v396": "pd_tauE_user_C_v396",
    "tauE_user_exp_Ip_v396": "pd_tauE_user_exp_Ip_v396",
    "tauE_user_exp_Bt_v396": "pd_tauE_user_exp_Bt_v396",
    "tauE_user_exp_ne_v396": "pd_tauE_user_exp_ne_v396",
    "tauE_user_exp_Ploss_v396": "pd_tauE_user_exp_Ploss_v396",
    "tauE_user_exp_R_v396": "pd_tauE_user_exp_R_v396",
    "tauE_user_exp_eps_v396": "pd_tauE_user_exp_eps_v396",
    "tauE_user_exp_kappa_v396": "pd_tauE_user_exp_kappa_v396",
    "tauE_user_exp_M_v396": "pd_tauE_user_exp_M_v396",

    # v397.0 profile proxy authority keys
    "include_profile_proxy_v397": "pd_include_profile_proxy_v397",
    "profile_alpha_T_v397": "pd_profile_alpha_T_v397",
    "profile_beta_T_v397": "pd_profile_beta_T_v397",
    "profile_alpha_n_v397": "pd_profile_alpha_n_v397",
    "profile_beta_n_v397": "pd_profile_beta_n_v397",
    "profile_alpha_j_v397": "pd_profile_alpha_j_v397",
    "profile_beta_j_v397": "pd_profile_beta_j_v397",
    "profile_shear_shape_v397": "pd_profile_shear_shape_v397",
    "profile_peaking_p_max_v397": "pd_profile_peaking_p_max_v397",
    "q95_proxy_min_v397": "pd_q95_proxy_min_v397",
    "q0_proxy_min_v397": "pd_q0_proxy_min_v397",
    "bootstrap_localization_max_v397": "pd_bootstrap_localization_max_v397",
    # v372.0 neutronics–materials coupling keys
    "include_neutronics_materials_coupling_v372": "pd_include_nm_coupling_v372",
    "nm_material_class_v372": "pd_nm_material_class_v372",
    "nm_spectrum_class_v372": "pd_nm_spectrum_class_v372",
    "nm_T_oper_C_v372": "pd_nm_T_oper_C_v372",
    "dpa_rate_eff_max_v372": "pd_dpa_rate_eff_max_v372",
    "damage_margin_min_v372": "pd_damage_margin_min_v372",
}


def _push_point_inputs_to_pd_widget_keys(base: Any) -> None:
    """Push a PointInputs-like object into Point Designer widget keys.

    Streamlit evaluates the script top-to-bottom on each rerun.
    If a preset is loaded via a button click, the preset application happens
    *after* the early one-shot sync. To avoid requiring a second click, we
    provide a direct, deterministic propagation routine that can be called
    immediately from the button handler.

    UI-only: this function only mutates widget/session state.
    """
    if base is None:
        return
    try:
        st.session_state[PD_KEYS["R0_m"]] = float(getattr(base, "R0_m"))
        st.session_state[PD_KEYS["a_m"]] = float(getattr(base, "a_m"))
        st.session_state[PD_KEYS["kappa"]] = float(getattr(base, "kappa"))
        st.session_state[PD_KEYS["delta"]] = float(getattr(base, "delta", 0.0) or 0.0)
        st.session_state[PD_KEYS["Bt_T"]] = float(getattr(base, "Bt_T"))
        st.session_state[PD_KEYS["Ti_keV"]] = float(getattr(base, "Ti_keV"))
        st.session_state[PD_KEYS["Paux_MW"]] = float(getattr(base, "Paux_MW"))
    except Exception:
        pass
    # Bounds from preset Ip/fG
    try:
        ip = float(getattr(base, "Ip_MA"))
        st.session_state[PD_KEYS["Ip_lo"]] = max(0.1, 0.80 * ip)
        st.session_state[PD_KEYS["Ip_hi"]] = max(0.2, 1.20 * ip)
    except Exception:
        pass
    try:
        fg = float(getattr(base, "fG"))
        st.session_state[PD_KEYS["fG_lo"]] = max(0.0, fg - 0.20)
        st.session_state[PD_KEYS["fG_hi"]] = min(2.0, fg + 0.20)
    except Exception:
        pass
    # Aux/Q denominator and Ti/Te
    try:
        st.session_state[PD_KEYS["Paux_for_Q"]] = float(getattr(base, "Paux_MW"))
    except Exception:
        pass
    try:
        st.session_state[PD_KEYS["Ti_over_Te"]] = float(getattr(base, "Ti_over_Te", 1.0))
    except Exception:
        pass

    # v371.0 transport contracts
    try:
        st.session_state[PD_KEYS["include_transport_contracts_v371"]] = bool(getattr(base, "include_transport_contracts_v371", False))
        st.session_state[PD_KEYS["H_required_max_optimistic"]] = float(getattr(base, "H_required_max_optimistic", float("nan")))
        st.session_state[PD_KEYS["H_required_max_robust"]] = float(getattr(base, "H_required_max_robust", float("nan")))
    except Exception:
        pass

    # Magnet technology axis (optional in older presets)
    try:
        st.session_state[PD_KEYS["magnet_technology"]] = str(getattr(base, "magnet_technology", "HTS_REBCO") or "HTS_REBCO")
    except Exception:
        pass

    # v318.0: profile bundle knobs (optional in older presets)
    try:
        st.session_state[PD_KEYS["profile_mode"]] = bool(getattr(base, "profile_mode", False))
        st.session_state[PD_KEYS["profile_alpha_T"]] = float(getattr(base, "profile_alpha_T", 1.5))
        st.session_state[PD_KEYS["profile_alpha_n"]] = float(getattr(base, "profile_alpha_n", 1.0))
        st.session_state[PD_KEYS["profile_shear_shape"]] = float(getattr(base, "profile_shear_shape", 0.5))
        st.session_state[PD_KEYS["pedestal_enabled"]] = bool(getattr(base, "pedestal_enabled", False))
        st.session_state[PD_KEYS["pedestal_width_a"]] = float(getattr(base, "pedestal_width_a", 0.05))
        st.session_state[PD_KEYS["include_bootstrap_pressure_selfconsistency"]] = bool(getattr(base, "include_bootstrap_pressure_selfconsistency", False))
        st.session_state[PD_KEYS["f_bootstrap_consistency_abs_max"]] = float(getattr(base, "f_bootstrap_consistency_abs_max", float("nan")))
    except Exception:
        pass
    try:
        st.session_state[PD_KEYS["Tcoil_K"]] = float(getattr(base, "Tcoil_K", 20.0))
    except Exception:
        pass


def apply_reference_preset(ref_key: str) -> None:
    """Load a catalog reference preset into the workspace.

    This is a *UI state* operation:
      - Sets ``last_point_inp`` to the preset PointInputs
      - Sets design intent (reactor vs research) from the catalog metadata
      - Arms a one-shot sync to propagate values into Point Designer widget keys
    """
    cat = reference_catalog()
    if ref_key not in cat:
        raise KeyError(f"Unknown reference preset: {ref_key}")
    ent = cat[ref_key]
    base = ent.get("inputs")
    if base is None:
        raise ValueError(f"Reference preset missing inputs: {ref_key}")

    # Set design intent from catalog
    intent = str(ent.get("intent", "")).strip().lower()
    if intent.startswith("research"):
        st.session_state["design_intent"] = "Experimental Device (research)"
    elif intent:
        st.session_state["design_intent"] = "Power Reactor (net-electric)"

    # Persist as the active workspace input object
    st.session_state["last_point_inp"] = base

    # Immediate propagation into Point Designer widget keys so the Configure
    # panel updates on the same click (no second click required).
    _push_point_inputs_to_pd_widget_keys(base)
    st.session_state["pd_needs_sync"] = False


def apply_legacy_reference_machine(name: str) -> None:
    """Load legacy REFERENCE_MACHINES entry (dict-like) into the workspace."""
    if name not in REFERENCE_MACHINES:
        raise KeyError(f"Unknown legacy preset: {name}")
    d = dict(REFERENCE_MACHINES[name] or {})
    try:
        base = make_point_inputs(**d)
    except Exception as e:
        raise ValueError(f"Legacy preset could not be converted to PointInputs: {name} ({e})")
    st.session_state["last_point_inp"] = base
    _push_point_inputs_to_pd_widget_keys(base)
    st.session_state["pd_needs_sync"] = False


def _compute_run_summary_from_out(out: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a deterministic, UI-safe run summary from outputs.

    Important: this must not depend on which Telemetry deck is visible.
    """
    try:
        cons = evaluate_constraints(out or {})
    except Exception:
        cons = []
    # Hard constraints only
    hard = []
    for c in (cons or []):
        try:
            if str(getattr(c, "severity", "hard")).strip().lower() == "hard":
                hard.append(c)
        except Exception:
            pass
    # Sort worst-first (most negative margin)
    try:
        hard_sorted = sorted(hard, key=lambda c: float(getattr(c, "margin", float("inf"))))
    except Exception:
        hard_sorted = list(hard)

    tight: List[Dict[str, Any]] = []
    for c in hard_sorted[:8]:
        try:
            tight.append(
                {
                    "name": str(getattr(c, "name", "")),
                    "passed": bool(getattr(c, "passed", False)),
                    "margin_frac": float(getattr(c, "margin", float("nan"))),
                    "value": getattr(c, "value", None),
                    "limit": getattr(c, "limit", None),
                    "units": getattr(c, "units", None),
                    "sense": getattr(c, "sense", None),
                    "group": getattr(c, "group", "general"),
                }
            )
        except Exception:
            pass

    # Power closure diagnostic
    closure = float("nan")
    try:
        pin = float(out.get("Pin_MW", float("nan")))
        ploss = float(out.get("Ploss_MW", float("nan")))
        if np.isfinite(pin) and np.isfinite(ploss):
            closure = pin - ploss
    except Exception:
        pass

    return {
        "headline": {
            "Q_DT_eqv": float(out.get("Q_DT_eqv", float("nan"))) if isinstance(out, dict) else float("nan"),
            "H98": float(out.get("H98", float("nan"))) if isinstance(out, dict) else float("nan"),
            "P_net_e_MW": float(out.get("P_net_e_MW", float("nan"))) if isinstance(out, dict) else float("nan"),
        },
        "power_closure_MW": closure,
        "tightest_hard_constraints": tight,
    }
# One-shot synchronization: when a preset is loaded we set this flag, and on the next
# rerun we push preset values into Point Designer widget keys.
def _render_magnet_authority_panel(out: Dict[str, Any]) -> None:
    """Render Magnet Technology Authority panel (v328.0).

    UI-only: reads frozen truth outputs and displays contract-driven limits and margins.
    """
    if not isinstance(out, dict) or not out:
        return

    with st.expander("Magnet Authority — Technology Regime (v328.0)", expanded=False):
        regime = str(out.get("magnet_regime", "UNKNOWN"))
        tech = str(out.get("magnet_technology", ""))
        contract_sha = str(out.get("magnet_contract_sha256", ""))[:12]
        cls = str(out.get("magnet_fragility_class", "UNKNOWN"))
        mmin = out.get("magnet_margin_min", float("nan"))

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Regime", regime)
        with c2:
            st.metric("Tech string", tech if tech else "—")
        with c3:
            st.metric("Class", cls)
        with c4:
            try:
                st.metric("Min margin (frac)", f"{float(mmin):.3g}")
            except Exception:
                st.metric("Min margin (frac)", str(mmin))

        st.caption(f"Contract SHA-256 (prefix): {contract_sha if contract_sha else '—'}")

        # Build a compact table of key limits and values
        rows = []
        def _add(name: str, vkey: str, lkey: str, units: str):
            v = out.get(vkey, float('nan'))
            l = out.get(lkey, float('nan'))
            try:
                v_f = float(v)
                l_f = float(l)
                if (v_f == v_f) or (l_f == l_f):
                    margin = (l_f - v_f) / max(abs(l_f), 1e-9) if (v_f == v_f and l_f == l_f) else float('nan')
                else:
                    margin = float('nan')
            except Exception:
                v_f, l_f, margin = v, l, float('nan')
            rows.append({
                "Quantity": name,
                "Value": v_f,
                "Limit": l_f,
                "Margin(frac)": margin,
                "Units": units,
            })

        _add("TF peak field", "B_peak_T", "B_peak_allow_T", "T")
        _add("TF von Mises stress", "sigma_vm_MPa", "sigma_allow_MPa", "MPa")
        _add("TF engineering J", "J_eng_A_mm2", "J_eng_max_A_mm2", "A/mm^2")
        _add("Coil nuclear heat", "coil_heat_nuclear_MW", "coil_heat_nuclear_max_MW", "MW")
        # SC margin (>=)
        try:
            rows.append({
                "Quantity": "SC critical-surface margin",
                "Value": float(out.get("hts_margin", float("nan"))),
                "Limit": float(out.get("hts_margin_min", float("nan"))),
                "Margin(frac)": float(out.get("hts_margin", float("nan"))) - float(out.get("hts_margin_min", float("nan"))),
                "Units": "-"
            })
        except Exception:
            pass
        try:
            rows.append({
                "Quantity": "Quench proxy margin",
                "Value": float(out.get("quench_proxy_margin", float("nan"))),
                "Limit": float(out.get("quench_proxy_min", float("nan"))),
                "Margin(frac)": float(out.get("quench_proxy_margin", float("nan"))) - float(out.get("quench_proxy_min", float("nan"))),
                "Units": "-"
            })
        except Exception:
            pass

        try:
            import pandas as pd  # type: ignore
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception:
            st.write(rows)

        # Deterministic repair hints (high-level; detailed mapping lives in contract artifact)
        st.markdown("**Deterministic repair levers (non-exhaustive):**")
        st.markdown("- Decrease **Bt** or increase **R0** (reduces required ampere-turns and peak field).")
        st.markdown("- Increase **TF build** (winding/structure) to improve **J** and **stress** margins.")
        st.markdown("- Increase **shielding/build** to reduce **nuclear heat** to coils (when coupled).")

def _sync_point_designer_from_last_point_inp() -> None:
    if not st.session_state.get("pd_needs_sync", False):
        return
    base = st.session_state.get("last_point_inp", None)
    if base is None:
        st.session_state["pd_needs_sync"] = False
        return
    _push_point_inputs_to_pd_widget_keys(base)
    st.session_state["pd_needs_sync"] = False




_sync_point_designer_from_last_point_inp()  # deferred until function is defined

# One-shot candidate apply: any panel may stage a candidate dict for Point Designer.
# This preserves SHAMS law: panels propose; Point Designer remains the frozen truth console.
def _consume_pd_candidate_apply() -> None:
    cand = st.session_state.pop("pd_candidate_apply", None)
    if not isinstance(cand, dict) or not cand:
        return
    try:
        base = make_point_inputs(**cand)
    except Exception:
        try:
            base = PointInputs(**cand)  # type: ignore
        except Exception:
            return
    st.session_state["last_point_inp"] = base
    # Force PD widget sync on next rerun; also push immediately so the same click updates widgets.
    try:
        _push_point_inputs_to_pd_widget_keys(base)
        st.session_state["pd_needs_sync"] = False
    except Exception:
        st.session_state["pd_needs_sync"] = True


def stage_pd_candidate_apply(cand: dict, source: str, note: str | None = None) -> None:
    """Canonical cross-panel handoff to Point Designer + provenance breadcrumb.

    Panels propose candidates. Point Designer evaluates frozen truth.

    v327.4: staging is delegated to ui.handoff to ensure deterministic DSG node-id propagation
    without requiring evaluator execution.
    """
    try:
        from ui.handoff import stage_pd_candidate_apply as _stage  # type: ignore
    except Exception:
        # fallback relative import for environments that package ui as a module
        from .handoff import stage_pd_candidate_apply as _stage  # type: ignore
    _stage(cand=cand, source=source, note=note)

def _verification_report_paths():
    rep = os.path.join(ROOT, "verification", "report.json")
    reqs = os.path.join(ROOT, "requirements", "SHAMS_REQS.yaml")
    reqs_json = os.path.join(ROOT, "requirements", "SHAMS_REQS.json")
    runner = os.path.join(ROOT, "verification", "run_verification.py")
    return rep, reqs, reqs_json, runner

def _verification_needs_run():
    rep, reqs, reqs_json, runner = _verification_report_paths()
    if not os.path.exists(rep):
        return True
    try:
        rep_m = os.path.getmtime(rep)
        deps = [p for p in [reqs, reqs_json, runner] if os.path.exists(p)]
        if not deps:
            return False
        dep_m = max(os.path.getmtime(p) for p in deps)
        return rep_m < dep_m
    except Exception:
        return False

def _run_verification_capture():
    """
    Run verification runner using the current Python interpreter.
    Returns: (ok: bool, stdout: str, stderr: str, seconds: float)
    """
    rep, reqs, reqs_json, runner = _verification_report_paths()
    t0 = time.time()
    if not os.path.exists(runner):
        return False, "", f"Missing verification runner: {runner}", 0.0
    try:
        proc = subprocess.run(
            [sys.executable, runner],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        dt = time.time() - t0
        ok = (proc.returncode == 0) and os.path.exists(rep)
        return ok, (proc.stdout or ""), (proc.stderr or ""), dt
    except Exception as e:
        dt = time.time() - t0
        return False, "", f"{type(e).__name__}: {e}", dt


from phase1_core import (
    PointInputs,
    solve_Ip_for_H98_with_Q_match,
    solve_Ip_for_H98_with_Q_match_stream,
    solve_sparc_envelope,
    solve_for_targets,
    solve_for_targets_stream,
    SolveResult,
    optimize_design,
)
from frontier.frontier import find_nearest_feasible
from models.reference_machines import REFERENCE_MACHINES, reference_catalog
from phase1_models import BH_COEFFS
from constraints.constraints import evaluate_constraints
from solvers.optimize import scan_feasible_and_pareto, pareto_front
from docs.variable_registry import registry_dataframe
from shams_io.run_artifact import build_run_artifact
from shams_io.plotting import plot_radial_build_from_artifact, plot_summary_pdf
from solvers.sensitivity import finite_difference_sensitivities


# --- Defensive constructor: UI may pass knobs that are absent in older/newer src/PointInputs
# This keeps the UI stable across PointInputs refactors (extra fields are ignored).
_POINTINPUTS_FIELDS = {f.name for f in fields(PointInputs)}

def make_point_inputs(**kwargs) -> PointInputs:
    """Create PointInputs using only supported dataclass fields."""
    filtered = {k: v for k, v in kwargs.items() if k in _POINTINPUTS_FIELDS}
    return PointInputs(**filtered)



# -----------------------------
# UI helpers
# -----------------------------
def _safe_get(obj, key: str, default=None):
    """Dict/dataclass-safe getter.

    SHAMS UI sometimes handles base objects loaded from JSON artifacts (dict)
    or from in-memory dataclass/namespace objects. This helper preserves
    deterministic fallback semantics without attribute-access crashes.
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _num(label: str, value: float, step: float, fmt: str = None, help: str = None, min_value=None, max_value=None, key: str = None):
    # Streamlit raises if default value is outside [min_value, max_value].
    # Clamp defensively so the UI remains robust even if bounds change.
    v = float(value)
    if min_value is not None:
        try:
            v = max(v, float(min_value))
        except Exception:
            pass
    if max_value is not None:
        try:
            v = min(v, float(max_value))
        except Exception:
            pass
    kwargs = {}
    if fmt: kwargs["format"] = fmt
    if help: kwargs["help"] = help
    if min_value is not None: kwargs["min_value"] = min_value
    if max_value is not None: kwargs["max_value"] = max_value
    return st.number_input(label, value=v, step=float(step), key=key, **kwargs) if key else st.number_input(label, value=v, step=float(step), **kwargs)


def _warn_unrealistic_point_inputs(pi: Any, context: str = "") -> None:
    """Non-blocking, UI-only warnings for obviously unrealistic user inputs.

    This must not change any model/solver behavior; it only surfaces warnings.
    """
    if pi is None:
        return
    # (lo, hi, message)
    checks = [
        ("R0_m", 0.5, 15.0, "Major radius R0 [m] looks unusual"),
        ("a_m", 0.1, 5.0, "Minor radius a [m] looks unusual"),
        ("kappa", 1.0, 3.5, "Elongation κ looks unusual"),
        ("delta", -0.8, 0.8, "Triangularity δ looks unusual"),
        ("Bt_T", 0.5, 25.0, "Toroidal field Bt [T] looks unusual"),
        ("Ip_MA", 0.1, 30.0, "Plasma current Ip [MA] looks unusual"),
        ("Ti_keV", 0.1, 40.0, "Ion temperature Ti [keV] looks unusual"),
        ("fG", 0.05, 1.5, "Greenwald fraction fG looks unusual"),
        ("Paux_MW", 0.0, 300.0, "Auxiliary power Paux [MW] looks unusual"),
        ("t_shield_m", 0.05, 2.0, "Shield thickness t_shield [m] looks unusual"),
    ]
    warns: List[str] = []
    for name, lo, hi, msg in checks:
        if not hasattr(pi, name):
            continue
        try:
            v = float(getattr(pi, name))
        except Exception:
            continue
        if (v < lo) or (v > hi):
            warns.append(f"- {msg}: **{name}={v:g}** (expected roughly {lo:g}–{hi:g})")
    if warns:
        title = "Unrealistic inputs"+ (f"({context})"if context else "")
        st.warning(title + "\n"+ "\n".join(warns))


# -----------------------------
# Scan Lab parameter metadata (UI-only)
# -----------------------------

# Human-friendly physics block names (used in tooltips + mapping table)
_PHYS_BLOCKS: Dict[str, str] = {
    "Geometry": "Machine geometry / size assumptions",
    "Magnets & radial build": "TF/HTS coil build, inboard stack closure, peak field mapping, stress",
    "0-D plasma core": "0-D profiles, fusion power, temperatures, density, basic scalings",
    "Confinement": "Energy confinement (IPB98-like) + confinement multipliers",
    "H-mode access": "L-H threshold (Martin-08-like) + margin screening",
    "Stability & limits": "q95, \u03b2N, bootstrap fraction and related operational screens",
    "Power balance & radiation": "Zeff/dilution/radiation and alpha deposition assumptions",
    "Divertor / SOL": "SOL power loading proxy (PSOL/R) and divertor heat-flux screen",
    "Neutronics": "TBR proxy + HTS fluence/lifetime proxy",
    "Electrical balance": "Recirculating power closure and net electric power screen",
    "Numerics": "Solver bounds/tolerance and feasibility filtering",
}

# For Scan Lab UI: which parameters are mandatory vs optional + which physics blocks they affect.
_SCAN_PARAM_META: Dict[str, Dict[str, Any]] = {
    # Machine / plasma assumptions
    "R0": {"req": True, "blocks": ["Geometry", "Magnets & radial build", "0-D plasma core", "Divertor / SOL"]},
    "B0": {"req": True, "blocks": ["Magnets & radial build", "0-D plasma core", "Confinement", "Stability & limits"]},
    "tshield": {"req": True, "blocks": ["Magnets & radial build", "Neutronics"]},
    "Paux": {"req": True, "blocks": ["0-D plasma core", "Power balance & radiation", "H-mode access", "Electrical balance"]},
    "Paux_for_Q": {"req": True, "blocks": ["0-D plasma core"]},
    "Ti_over_Te": {"req": True, "blocks": ["0-D plasma core", "Power balance & radiation"]},

    # Axes
    "Ti": {"req": True, "blocks": ["0-D plasma core", "Confinement", "Power balance & radiation"]},
    "H98": {"req": True, "blocks": ["Confinement"]},
    "a": {"req": True, "blocks": ["Geometry", "0-D plasma core", "Stability & limits", "Divertor / SOL", "Magnets & radial build"]},
    "Q": {"req": True, "blocks": ["0-D plasma core", "Electrical balance"]},
    "g_conf": {"req": True, "blocks": ["Confinement"]},

    # Solver bounds & screens
    "Ip_bounds": {"req": True, "blocks": ["Numerics", "0-D plasma core", "Stability & limits", "Magnets & radial build"]},
    "fG_bounds": {"req": True, "blocks": ["Numerics", "0-D plasma core"]},
    "tol": {"req": True, "blocks": ["Numerics"]},

    # Screening knobs (plasma)
    "Zeff": {"req": True, "blocks": ["Power balance & radiation"]},
    "dilution_fuel": {"req": True, "blocks": ["Power balance & radiation", "0-D plasma core"]},
    "extra_rad_factor": {"req": True, "blocks": ["Power balance & radiation"]},
    "alpha_loss_frac": {"req": True, "blocks": ["Power balance & radiation"]},
    "kappa": {"req": True, "blocks": ["Stability & limits", "0-D plasma core"]},
    "q95_min": {"req": True, "blocks": ["Stability & limits"]},
    "betaN_max": {"req": True, "blocks": ["Stability & limits"]},
    "C_bs": {"req": True, "blocks": ["Stability & limits"]},
    "f_bs_max": {"req": True, "blocks": ["Stability & limits"]},
    "PSOL_over_R_max": {"req": True, "blocks": ["Divertor / SOL"]},

    # Optional toggle
    "require_Hmode": {"req": False, "blocks": ["H-mode access"]},
    "PLH_margin": {"req": False, "blocks": ["H-mode access"]},

    # Clean design knobs (engineering screens)
    "tblanket_m": {"req": False, "blocks": ["Magnets & radial build", "Neutronics"]},
    "t_vv_m": {"req": False, "blocks": ["Magnets & radial build"]},
    "t_gap_m": {"req": False, "blocks": ["Magnets & radial build"]},
    "t_tf_struct_m": {"req": False, "blocks": ["Magnets & radial build"]},
    "t_tf_wind_m": {"req": False, "blocks": ["Magnets & radial build"]},
    "Bpeak_factor": {"req": False, "blocks": ["Magnets & radial build"]},
    "sigma_allow_MPa": {"req": False, "blocks": ["Magnets & radial build"]},
    "Tcoil_K": {"req": False, "blocks": ["Magnets & radial build"]},
    "hts_margin_min": {"req": False, "blocks": ["Magnets & radial build"]},
    "Vmax_kV": {"req": False, "blocks": ["Magnets & radial build"]},
    "q_div_max_MW_m2": {"req": False, "blocks": ["Divertor / SOL"]},
    "q_midplane_max_MW_m2": {"req": False, "blocks": ["Divertor / SOL"]},
    "TBR_min": {"req": False, "blocks": ["Neutronics"]},
    "hts_lifetime_min_yr": {"req": False, "blocks": ["Neutronics"]},
    "P_net_min_MW": {"req": False, "blocks": ["Electrical balance"]},
}


def _scan_badge(param_key: str) -> str:
    meta = _SCAN_PARAM_META.get(param_key)
    # Default to optional if unknown
    is_req = bool(meta.get("req")) if isinstance(meta, dict) else False
    return "Mandatory"if is_req else "Optional"


def _scan_blocks(param_key: str) -> List[str]:
    meta = _SCAN_PARAM_META.get(param_key)
    if not isinstance(meta, dict):
        return []
    return [b for b in meta.get("blocks", []) if b in _PHYS_BLOCKS]


def _scan_label(base: str, param_key: str) -> str:
    # number_input labels do not render markdown; keep it simple + consistent.
    return f"{base} · {_scan_badge(param_key)}"


def _scan_help(base_help: str, param_key: str) -> str:
    blocks = _scan_blocks(param_key)
    if not blocks:
        return base_help
    lines = [base_help.strip(), "", "Maps to physics blocks:"]
    for b in blocks:
        lines.append(f"- {b}: {_PHYS_BLOCKS[b]}")
    return "\n".join(lines).strip()

def kpi_row(items: List[Tuple[str, Any]]):
    cols = st.columns(len(items))
    for c, (k, v) in zip(cols, items):
        c.metric(k, v)


def _numeric_cols(df: pd.DataFrame) -> List[str]:
    cols = []
    for c in df.columns:
        try:
            if pd.api.types.is_numeric_dtype(df[c]):
                cols.append(c)
        except Exception:
            pass
    return cols


def plot_scatter(df: pd.DataFrame, x: str, y: str, color: str | None = None, title: str | None = None):
    """Matplotlib scatter with optional numeric color."""
    if df is None or df.empty:
        st.info("No data to plot.")
        return
    if x not in df or y not in df:
        st.warning("Select valid x/y columns.")
        return

    d = df[[x, y] + ([color] if color and color in df else [])].dropna()
    if d.empty:
        st.info("No finite rows for this plot (after dropping NaNs).")
        return
    # Matplotlib is optional: if missing, fall back to Streamlit's built-in charts.
    if not _HAVE_MPL:
        st.warning("Plotting is limited because 'matplotlib' is not installed. Install it (pip install matplotlib) for full plotting.")
        # Streamlit fallback (no colorbar support)
        try:
            st.scatter_chart(d, x=x, y=y)
        except Exception:
            st.line_chart(d[[x, y]].rename(columns={x: "x", y: "y"}))
        return

    fig = plt.figure(figsize=(6.8, 4.6))
    ax = plt.gca()
    if color and color in d and pd.api.types.is_numeric_dtype(d[color]):
        sc = ax.scatter(d[x], d[y], c=d[color], s=22, alpha=0.85)
        cb = plt.colorbar(sc, ax=ax)
        cb.set_label(color)
    else:
        ax.scatter(d[x], d[y], s=22, alpha=0.85)

    ax.set_xlabel(x)
    ax.set_ylabel(y)
    if title:
        ax.set_title(title)
    ax.grid(True, alpha=0.25)
    st.pyplot(fig, clear_figure=True)


def plot_bars(values: Dict[str, float], title: str):
    keys = [k for k in values.keys() if isinstance(values.get(k), (int, float)) and math.isfinite(float(values.get(k))) ]
    if not keys:
        st.caption("No plottable values available.")
        return
    if not _HAVE_MPL:
        st.warning("Bar charts are limited because 'matplotlib' is not installed. Install it (pip install matplotlib) for full plotting.")
        import pandas as _pd
        s = _pd.Series({k: float(values[k]) for k in keys})
        try:
            st.bar_chart(s)
        except Exception:
            st.write(s)
        return

    fig = plt.figure(figsize=(6.8, 4.4))
    ax = plt.gca()
    ax.bar(range(len(keys)), [float(values[k]) for k in keys])
    ax.set_xticks(range(len(keys)), keys, rotation=35, ha="right")
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.25)
    st.pyplot(fig, clear_figure=True)

def badge(check):
    """Render PASS/FAIL/WARN/SKIPPED badge.
    Accepts either a check dict with 'status' or a legacy ok flag.
    """
    if isinstance(check, dict):
        stt = check.get('status')
        if stt == 'SKIPPED':
            return ' SKIPPED'
        if stt == 'WARN':
            return ' WARN'
        if stt == 'FAIL':
            return ' FAIL'
        if stt == 'PASS':
            return ' PASS'
        # fallback
        ok = check.get('ok')
    else:
        ok = check
    if ok is None:
        return ' SKIPPED'
    return ' PASS' if ok else ' FAIL'


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)

def top_violations(checks: List[Dict[str, Any]], n: int = 3) -> List[Dict[str, Any]]:
    bad = [c for c in checks if c.get('status') == 'FAIL']

    # sort by relative violation if available
    def score(c):
        if c.get("value") is None or c.get("limit") is None:
            return 0.0
        v, lim = c["value"], c["limit"]
        if not (finite(v) and finite(lim)) or lim == 0:
            return 0.0
        if c.get("sense") == "max":
            return (v - lim) / abs(lim)
        if c.get("sense") == "min":
            return (lim - v) / abs(lim)
        return 0.0
    bad.sort(key=score, reverse=True)
    return bad[:n]

def top_warnings(checks: List[Dict[str, Any]], n: int = 3) -> List[Dict[str, Any]]:
    ws = [c for c in checks if c.get('status') == 'WARN']
    def score(c):
        v = c.get('value'); lim = c.get('limit'); sense = c.get('sense')
        if v is None or lim is None or not finite(v) or not finite(lim):
            return 0.0
        if sense == 'max':
            return max(0.0, (v - lim) / abs(lim))
        if sense == 'min':
            return max(0.0, (lim - v) / abs(lim))
        return 0.0
    ws.sort(key=score, reverse=True)
    return ws[:n]

def compute_checks(out: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Turn flat outputs into a structured constraint list.

    IMPORTANT:
    - Checks are only evaluated when the needed physics is enabled *and* the value is finite.
    - If a model/physics block is disabled (or produced NaN), the check is marked SKIPPED.
    - Checks can be WARNING-level or HARD FAIL depending on how far they are from the limit.
    """
    checks: List[Dict[str, Any]] = []


    # global warning behavior knobs (can be overridden per-check via explicit warn_limit)
    warn_frac_max = float(out.get("_warn_frac_max", 0.90))  # for max constraints: WARN if v > warn_frac*limit
    warn_frac_min = float(out.get("_warn_frac_min", 1.10))  # for min constraints: WARN if v < warn_frac*limit

    def add(name, status, value=None, limit=None, sense=None, notes="", severity="hard", warn_limit=None):
        """status in {'PASS','FAIL','WARN','SKIPPED'}"""
        ok = None
        if status == "PASS":
            ok = True
        elif status == "FAIL":
            ok = False
        elif status == "WARN":
            ok = True  # warn is still 'ok' for legacy consumers
        elif status == "SKIPPED":
            ok = None
        checks.append({
            "name": name,
            "status": status,
            "ok": ok,
            "value": value,
            "limit": limit,
            "warn_limit": warn_limit,
            "sense": sense,
            "notes": notes,
            "severity": severity,
        })

        # ok can be True/False/None (None => skipped)
        checks.append({"name": name, "ok": ok if ok in (True, False, None) else bool(ok),
                       "value": value, "limit": limit, "sense": sense, "notes": notes})

    def fin(x) -> bool:
        return isinstance(x, (int, float)) and math.isfinite(x)
    def eval_max(name, key_value, key_limit, notes="", severity="hard", warn_limit=None):
        v = out.get(key_value)
        lim = out.get(key_limit)
        if (not fin(v)) or (not fin(lim)):
            add(name, "SKIPPED", v, lim, "max", notes, severity=severity, warn_limit=warn_limit)
            return
        wl = warn_limit
        if wl is None:
            wl = warn_frac_max * lim
        if v > lim:
            add(name, "FAIL", v, lim, "max", notes, severity=severity, warn_limit=wl)
        elif v > wl:
            add(name, "WARN", v, lim, "max", notes, severity=severity, warn_limit=wl)
        else:
            add(name, "PASS", v, lim, "max", notes, severity=severity, warn_limit=wl)

    def eval_min(name, key_value, key_limit, notes="", severity="hard", warn_limit=None):
        v = out.get(key_value)
        lim = out.get(key_limit)
        if (not fin(v)) or (not fin(lim)):
            add(name, "SKIPPED", v, lim, "min", notes, severity=severity, warn_limit=warn_limit)
            return
        wl = warn_limit
        if wl is None:
            wl = warn_frac_min * lim
        # for min constraints, warn if v is between lim and wl (wl > lim)
        if v < lim:
            add(name, "FAIL", v, lim, "min", notes, severity=severity, warn_limit=wl)
        elif v < wl:
            add(name, "WARN", v, lim, "min", notes, severity=severity, warn_limit=wl)
        else:
            add(name, "PASS", v, lim, "min", notes, severity=severity, warn_limit=wl)    # --- Build closure ---
    if "radial_build_ok"in out:
        v = out.get("radial_build_ok")
        if not fin(v):
            add("Radial build closure", "SKIPPED", out.get("rb_total_inboard_m"), out.get("rinboard_available_m"), "max",
                "Requires inboard stack thickness ≤ available inboard space (R0 - a).")
        else:
            add("Radial build closure", "PASS"if (v > 0.5) else "FAIL", out.get("rb_total_inboard_m"), out.get("rinboard_available_m"), "max",
                "Requires inboard stack thickness ≤ available inboard space (R0 - a).")

    # --- Magnet stress ---


    if "sigma_hoop_MPa"in out and "sigma_allow_MPa"in out:
        eval_max("TF hoop stress", "sigma_hoop_MPa", "sigma_allow_MPa",
                 "Hoop stress proxy must be below allowable structural stress.")

    # --- HTS margin ---
    if "hts_margin"in out and "hts_margin_min"in out:
        eval_min("HTS margin", "hts_margin", "hts_margin_min",
                 "HTS operating margin proxy vs (B,T) must exceed minimum.")

    # --- Dump voltage ---
    if "V_dump_kV"in out and "Vmax_kV"in out:
        eval_max("Dump voltage", "V_dump_kV", "Vmax_kV",
                 "Fast discharge voltage must not exceed protection limit.")

    # --- Divertor heat flux ---

    if "q_div_MW_m2"in out and "q_div_max_MW_m2"in out:
        eval_max("Divertor heat flux", "q_div_MW_m2", "q_div_max_MW_m2",
                 "Peak divertor heat flux proxy must be below limit.")

    # --- Tritium breeding ratio ---
    if "TBR"in out and "TBR_min"in out:
        eval_min("TBR", "TBR", "TBR_min",
                 "Tritium breeding ratio proxy must exceed minimum.")

    # --- TBR proxy validity-domain (v321) ---
    if "TBR_domain_ok"in out:
        ok = out.get("TBR_domain_ok")
        enf = out.get("neutronics_domain_enforce", 0.0)
        if not fin(ok):
            add("TBR validity domain", "SKIPPED", ok, 1.0, "min", "Proxy validity-domain check not available.")
        else:
            if (fin(enf) and enf > 0.5):
                add("TBR validity domain", "PASS"if (ok > 0.5) else "FAIL", ok, 1.0, "min", "If enforced, TBR proxy must be inside declared validity domain.")
            else:
                add("TBR validity domain", "PASS"if (ok > 0.5) else "WARN", ok, 1.0, "min", "Not enforced by default; WARN means the proxy is out-of-domain.")

    # --- HTS lifetime ---
    if "hts_lifetime_yr"in out and "hts_lifetime_min_yr"in out:
        eval_min("HTS lifetime", "hts_lifetime_yr", "hts_lifetime_min_yr",
                 "Neutron lifetime proxy of HTS must exceed minimum.")

    # --- Net electric power ---
    if "P_net_e_MW"in out and "P_net_min_MW"in out:
        eval_min("Net electric power", "P_net_e_MW", "P_net_min_MW",
                 "Net electric power must exceed minimum (system closure).")

    # --- H-mode access (only if enforced) ---
    # If require_Hmode is False or physics is disabled, this becomes SKIPPED.
    if "require_Hmode"in out and "LH_ok"in out:
        req = out.get("require_Hmode")
        lh_ok = out.get("LH_ok")
        if not (fin(req) and req > 0.5):
            add("H‑mode access", None, lh_ok, 1.0, "min",
                "H‑mode not required (or LH physics disabled).")
        else:
            if not fin(lh_ok):
                add("H‑mode access", None, lh_ok, 1.0, "min",
                    "H‑mode required, but LH physics not available for this point.")
            else:
                add("H‑mode access", lh_ok > 0.5, lh_ok, 1.0, "min",
                    "If H‑mode required, point must be above LH threshold with margin.")

    return checks


# -----------------------------
# Scan runner (UI-native)
# -----------------------------
def frange(start: float, stop: float, step: float) -> List[float]:
    vals: List[float] = []
    if step == 0:
        return [start]
    x = start
    if step > 0:
        while x <= stop + 1e-12:
            vals.append(float(x))
            x += step
    else:
        while x >= stop - 1e-12:
            vals.append(float(x))
            x += step
    return vals

def run_scan(spec: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    A refactor of the CLI scan loop into a UI-callable function.

    Returns:
      df_feasible: rows of extended-feasible points (same spirit as 'feasible_ext' sheet)
      meta: dict with scan settings + summary stats
    """
    Ti_grid = frange(spec["Ti_start"], spec["Ti_stop"], spec["Ti_step"] if spec["Ti_stop"] >= spec["Ti_start"] else -abs(spec["Ti_step"]))
    H_grid = frange(spec["H98_start"], spec["H98_stop"], abs(spec["H98_step"]))
    a_grid = frange(spec["a_min"], spec["a_max"], abs(spec["a_step"]))
    Q_grid = frange(spec["Q_start"], spec["Q_stop"], abs(spec["Q_step"]))
    g_grid = frange(spec["gconf_start"], spec["gconf_stop"], abs(spec["gconf_step"]))


    # --- Scan Lab: optional UI progress + logging hooks (kept no-op for non-UI use) ---
    progress_cb = spec.get("_progress_cb")  # callable(fraction: float, info: dict) -> None
    log_cb = spec.get("_log_cb")            # callable(line: str) -> None
    log_lines: List[str] = []

    def _log(line: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        s = f"[{ts}] {line}"
        log_lines.append(s)
        if callable(log_cb):
            try:
                log_cb(s)
            except Exception:
                pass

    def _progress(i: int, n: int, **info: Any) -> None:
        if callable(progress_cb) and n > 0:
            try:
                progress_cb(min(max(i / n, 0.0), 1.0), info)
            except Exception:
                pass

    n_total = max(1, len(g_grid) * len(Ti_grid) * len(H_grid) * len(a_grid) * len(Q_grid))
    _log(f"Scan initialized: {len(g_grid)} g_conf × {len(Ti_grid)} Ti × {len(H_grid)} H98 × {len(a_grid)} a × {len(Q_grid)} Q => {n_total} evaluations")
    i_eval = 0

    rows: List[Dict[str, Any]] = []
    best_g = None

    # --- v327.3: pipeline DSG edge automation (best-effort; does not change truth) ---
    dsg_parent = spec.get("_dsg_parent_node_id")
    if not dsg_parent:
        try:
            dsg_parent = st.session_state.get("dsg_selected_node_id") or st.session_state.get("active_design_node_id")
        except Exception:
            dsg_parent = None

    scan_node_ids: List[str] = []
    scan_edge_note = f"scan: g_conf[{len(g_grid)}] Ti[{len(Ti_grid)}] H98[{len(H_grid)}] a[{len(a_grid)}] Q[{len(Q_grid)}]"


    for g_conf in g_grid:
        for Ti in Ti_grid:
            for Hreq in H_grid:
                for a in a_grid:
                    for Qtar in Q_grid:
                        # Solve at reduced target (same logic as CLI driver)

                        i_eval += 1
                        _progress(i_eval, n_total,
                                  stage="setup",
                                  g_conf=float(g_conf), Ti_keV=float(Ti), H98_req=float(Hreq), a_m=float(a), Q_target=float(Qtar))
                        _log(f"Eval {i_eval}/{n_total}: g_conf={g_conf:.3g}, Ti={Ti:.3g} keV, H98_req={Hreq:.3g}, a={a:.3g} m, Q={Qtar:.3g}")
                        _log("- Building point inputs (geometry, fields, density/temperature assumptions)")

                        H_base_target = Hreq / max(g_conf, 1e-9)

                        base = make_point_inputs(
                            R0_m=spec["R0"],
                            a_m=a,
                            kappa=spec["kappa"],
                            Bt_T=spec["B0"],
                            Ip_MA=0.5*(spec["Ip_min"]+spec["Ip_max"]),
                            Ti_keV=Ti,
                            fG=0.8,
                            t_shield_m=spec["tshield"],
                            Paux_MW=spec["Paux"],
                            Ti_over_Te=spec["Ti_over_Te"],
                            zeff=spec["Zeff"],
                            dilution_fuel=spec["dilution_fuel"],
                            fuel_mode="DT",
                            include_secondary_DT=include_secondary_DT,
                            tritium_retention=0.5,
                            tau_T_loss_s=5.0,
                            extra_rad_factor=spec["extra_rad_factor"],
                            alpha_loss_frac=spec["alpha_loss_frac"],
                            C_bs=spec["C_bs"],
                            require_Hmode=spec["require_Hmode"],
                            PLH_margin=spec["PLH_margin"],
                            # --- Clean design knobs (passed through PointInputs defaults if present in your src)
                            **spec.get("clean_knobs", {}),
                        )


                        _log("- Solving nested system: outer Ip for H98, inner fG for Q (bisection)")
                        _progress(i_eval, n_total, stage="solve")
                        sol_inp, sol_out, ok = solve_Ip_for_H98_with_Q_match(
                            base=base,
                            target_H98=H_base_target,
                            target_Q=Qtar,
                            Ip_min=spec["Ip_min"],
                            Ip_max=spec["Ip_max"],
                            fG_min=spec["fG_min"],
                            fG_max=spec["fG_max"],
                            tol=spec["tol"],
                            Paux_for_Q_MW=spec["Paux_for_Q"],
                        )
                        if not ok:
                            _log("- Solver failed to bracket/converge for this combo (skipping)")
                            continue

                        # Effective confinement
                        H98_eff = g_conf * sol_out["H98"]
                        sol_out["H98_eff"] = H98_eff


                        _log("- Evaluating physics proxies (power balance, confinement, operational limits)")
                        _progress(i_eval, n_total, stage="evaluate")
                        # Standard ext checks from CLI
                        ok_ext = True
                        if sol_out["ne20"] > 1.2:
                            ok_ext = False
                        if sol_out.get('q95_proxy', 1e9) < spec["q95_min"]:
                            ok_ext = False
                        if sol_out.get("betaN_proxy", 0.0) > spec["betaN_max"]:
                            ok_ext = False
                        if sol_out.get("f_bs_proxy", 0.0) > spec["f_bs_max"]:
                            ok_ext = False
                        PSOL_over_R = sol_out["Ploss_MW"] / spec["R0"]
                        sol_out["PSOL_over_R"] = PSOL_over_R
                        if PSOL_over_R > spec["PSOL_over_R_max"]:
                            ok_ext = False
                        if spec["require_Hmode"] and sol_out.get("LH_ok", 1.0) < 0.5:
                            ok_ext = False
                        if H98_eff < Hreq:
                            ok_ext = False
                        if sol_out["Q_DT_eqv"] < Qtar:
                            ok_ext = False

                        # Clean design checks (if present)
                        checks = compute_checks(sol_out)
                        if any((not c["ok"]) for c in checks):
                            ok_ext = False

                        if not ok_ext:
                            _log("- Failed screening checks (skipping)")
                            continue

                        if best_g is None or g_conf < best_g:
                            best_g = g_conf

                        _log("- Feasible point found (adding to results)")
                        _progress(i_eval, n_total, stage="record")
                        row = dict(sol_out)
                        row.update({
                            "g_conf": g_conf,
                            "Ti_keV": Ti,
                            "Q_target": Qtar,
                            "H98_required": Hreq,
                            "a_m": a,
                            "Ip_MA": sol_inp.Ip_MA,
                            "f_G": sol_inp.fG,
                            "Paux_MW": sol_inp.Paux_MW,
                            "Paux_for_Q_MW": spec["Paux_for_Q"],
                            "H98_eff": H98_eff,
                        })

                        # --- v327.3: DSG pipeline capture for scan points (best-effort) ---
                        try:
                            g = st.session_state.get("_shams_dsg")
                            if g is not None:
                                node = g.record(
                                    inp=sol_inp,
                                    out=dict(sol_out),
                                    ok=True,
                                    message="scan_feasible",
                                    elapsed_s=0.0,
                                    origin="ScanLab",
                                    parents=[str(dsg_parent)] if dsg_parent else None,
                                    tags=["scan", "feasible"],
                                    edge_kind="scan",
                                    edge_note=scan_edge_note,
                                )
                                scan_node_ids.append(node.node_id)
                                st.session_state["active_design_node_id"] = node.node_id
                        except Exception:
                            pass                        # --- v327.4: pipeline-native dsg_node_id column for scan tables ---
                        try:
                            if "dsg_node_id"not in row:
                                _nid = None
                                try:
                                    _nid = node.node_id  # type: ignore[name-defined]
                                except Exception:
                                    _nid = None
                                if not _nid:
                                    from evaluator.cache_key import sha256_cache_key
                                    _nid = sha256_cache_key(sol_inp)
                                row["dsg_node_id"] = str(_nid)
                        except Exception:
                            pass

                        rows.append(row)

    df = pd.DataFrame(rows)
    meta = dict(spec)
    meta["best_g_conf_found"] = best_g if best_g is not None else "NONE"
    meta["n_feasible"] = int(len(df))

    # Strip non-serializable UI callbacks from meta and attach log text
    meta.pop("_progress_cb", None)
    meta.pop("_log_cb", None)
    meta["scan_log_text"] = "\n".join(log_lines)
    # --- v327.3: expose scan DSG node IDs for downstream panels ---
    try:
        meta["dsg_parent_node_id"] = str(dsg_parent) if dsg_parent else ""
        meta["dsg_scan_node_ids"] = list(scan_node_ids)
        st.session_state["scan_last_node_ids"] = list(scan_node_ids)
        st.session_state["scan_last_parent_node_id"] = str(dsg_parent) if dsg_parent else ""
        _dsg_save_best_effort()
    except Exception:
        pass
    _log(f"Scan complete: feasible={meta['n_feasible']} best_g_conf_found={meta['best_g_conf_found']}")

    return df, meta

def df_to_excel_bytes(df: pd.DataFrame, meta: Dict[str, Any]) -> bytes:
    """
    Export feasible dataframe + meta into an Excel workbook (in-memory).
    """
    import openpyxl
    from openpyxl.styles import Font

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "feasible_ext"

    if df.empty:
        ws.append(["NO_FEASIBLE_POINTS"])
    else:
        ws.append(list(df.columns))
        for c in range(1, len(df.columns)+1):
            ws.cell(row=1, column=c).font = Font(bold=True)
        ws.freeze_panes = "A2"
        for _, r in df.iterrows():
            ws.append([r.get(c) for c in df.columns])

    # meta sheet
    wsM = wb.create_sheet("meta")
    wsM.append(["key", "value"])
    wsM["A1"].font = Font(bold=True)
    for k, v in meta.items():
        # keep meta compact
        if isinstance(v, dict):
            continue
        if isinstance(v, list):
            continue
        wsM.append([k, v])
    wsM.freeze_panes = "A2"

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title=APP_NAME, layout="wide")


# v276: keep last run artifact for cross-panels
if "last_run_artifact"not in st.session_state:
    st.session_state["last_run_artifact"] = {}

_render_branding_header()
_shams_status_strip_placeholder = st.empty()

def _shams_status_strip():
    # Top-of-page professional status strip (Review-room instrumentation)
    locked, task, started, is_owner = _shams_runlock.status(st.session_state.get("_shams_owner_token"), app_start_ts=st.session_state.get("_shams_app_start_ts"))
    prev_locked = bool(st.session_state.get("_shams_prev_locked", False))
    prev_task = st.session_state.get("_shams_prev_task")

    # Completion detection: was locked, now unlocked
    if prev_locked and not locked and prev_task:
        try:
            if not st.session_state.get("silence_mode", False):
                st.toast(f"Sequence Complete: {prev_task}")
        except Exception:
            pass

    st.session_state["_shams_prev_locked"] = locked
    st.session_state["_shams_prev_task"] = task

    with _shams_status_strip_placeholder.container():
        if locked and task:
            age_s = int(_shams_time.time() - float(started or _shams_time.time()))
            st.info(f"**Running Sequence** · {task} · t+{age_s}s · All other solver actions are locked.")
            # Show a concise tail of the Black-Box Chronicle
            try:
                _lg = _activity_logger()
                tail_text = _lg.path.read_text(encoding="utf-8", errors="replace") if _lg.path.exists() else ""
                tail_lines = tail_text.splitlines()[-20:] if tail_text else []
                if tail_lines:
                    with st.expander("Black-Box Chronicle tail (live)", expanded=False):
                        st.code("\n".join(tail_lines), language="")
            except Exception:
                pass
        else:
            # Calm "ready"strip for experts
            st.caption("Status: Ready · Helm Console armed · Awaiting next sequence.")

_shams_status_strip()

st.session_state.setdefault('shams_state', SessionStateModel())
# ---- UI polish (CSS) ----
# Streamlit theming is usually done via .streamlit/config.toml, but we keep it self-contained.
st.markdown(
    """
<style>
  /* Slightly tighter overall spacing */
  .block-container { padding-top: 2.2rem; padding-bottom: 3.4rem; }
  h1 { margin-top: 0.25rem; line-height: 1.15; }

  /* Header spacing: avoid negative letter-spacing which can overlap glyphs at some zoom levels */
  h1, h2, h3 { letter-spacing: 0; }

  /* Metric cards: increase contrast and soften edges */
  [data-testid="stMetric"] {
    padding: 0.75rem 0.75rem;
    border-radius: 16px;
    border: 1px solid rgba(49, 51, 63, 0.15);
    background: rgba(255, 255, 255, 0.03);
  }

  /* Buttons */
  div.stButton > button {
    border-radius: 14px;
    padding: 0.55rem 0.9rem;
    font-weight: 650;
  }

  /* Expander */
  details {
    border-radius: 14px;
    border: 1px solid rgba(49, 51, 63, 0.12);
    padding: 0.25rem 0.4rem;
  }

  /* Code blocks */
  pre {
    border-radius: 14px;
  }

  /* Dataframes */
  .stDataFrame { border-radius: 14px; overflow: hidden; }
</style>
    """,
    unsafe_allow_html=True,
)

# Persistent footer (render early so st.stop paths still show it)
_render_footer()
st.sidebar.markdown("## Helm Console - Expert Navigation")

# Session & Authority (professional, read-mostly posture)
_forge_review_mode = bool(st.session_state.get("forge_review_mode", False))
_posture = "Review Mode (locked)"if _forge_review_mode else "Explore Mode"
st.sidebar.caption("Captain’s Ledger")
st.sidebar.markdown(f"""- **Posture:** {_posture}
- **Authority:** Frozen evaluator
- **Workspace:** Non-authoritative""")

st.session_state.explain_mode = st.sidebar.toggle(
    "Explain mode (show equations & reasons)",
    value=bool(st.session_state.get("explain_mode", True)),
    help="Teaching mode: show model equations, assumptions, and why constraints bind.",
)

with st.sidebar.expander("Advanced controls", expanded=False):
    st.session_state.expert_mode = st.toggle(
        "Expert controls",
        value=bool(st.session_state.get("expert_mode", False)),
        disabled=_forge_review_mode,
        help="Expose solver tolerances and optimizer internals. Disabled in Review Mode.",
    )

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Design Intent - influences what counts as "hard"in Systems/Optimization
# ---------------------------------------------------------------------------
_design_intent_prev = st.session_state.get("design_intent", "Power Reactor (net-electric)")
with st.sidebar.expander("Reactor Covenant", expanded=False):
    st.session_state["design_intent"] = st.selectbox(
        "Intent",
        ["Power Reactor (net-electric)", "Experimental Device (research)"],
        index=0 if ("reactor"in _design_intent_prev.lower() or _design_intent_prev.lower().startswith("power")) else 1,
        help="Reactor intent enforces strict engineering/plant constraints (e.g., TBR, stress, heat flux). Research intent relaxes/softens some constraints to explore physics-relevant machines.",
    )

# (Design contract continues below in Verification/Fidelity panels)

if st.session_state.get("design_intent") != _design_intent_prev:

    _invalidate_mode_caches("design_intent_changed")

    try:
        from schema.governance_presets import apply_governance_preset, tritium_tight_closure_default
    except ImportError:
        from src.schema.governance_presets import apply_governance_preset, tritium_tight_closure_default
    try:
        _lpi = st.session_state.get("last_point_inp")
        if _lpi is not None:
            from dataclasses import asdict
            _fields = asdict(_lpi) if hasattr(_lpi, "__dataclass_fields__") else dict(_lpi)
            apply_governance_preset(_fields, design_intent=str(st.session_state.get("design_intent", "")))
            st.session_state["include_tritium_tight_closure"] = bool(
                _fields.get("include_tritium_tight_closure", tritium_tight_closure_default(str(st.session_state.get("design_intent", ""))))
            )
    except Exception:
        pass

    try:
        _alog("UI", "DesignIntentChanged", {"from": _design_intent_prev, "to": st.session_state.get("design_intent")})
    except Exception:
        pass

def _design_intent_key() -> str:
    s = str(st.session_state.get("design_intent", "Power Reactor (net-electric)")).strip().lower()
    if s.startswith("experimental") or s.startswith("research") or ("research"in s):
        return "research"
    return "reactor"

# Canonical constraint enforcement sets (names must match constraint 'name' strings)
# NOTE: q95 is enforced hard in both intents per user request.
_INTENT_HARD = {
    "reactor": {"q95", "q_div", "P_SOL/R", "sigma_vm", "B_peak", "HTS margin", "TBR", "NWL"},
    "research": {"q95"},
}
_INTENT_SOFT = {
    "reactor": set(),
    "research": {"q_div", "P_SOL/R", "sigma_vm", "B_peak", "HTS margin", "NWL"},  # shown, not enforced as hard
}
_INTENT_IGNORE = {
    "reactor": set(),
    "research": {"TBR"},  # research machines may not aim for breeding blanket
}

def _hard_constraint_names_for_intent() -> set[str]:
    k = _design_intent_key()
    return set(_INTENT_HARD.get(k, set()))

def _ignored_constraint_names_for_intent() -> set[str]:
    k = _design_intent_key()
    return set(_INTENT_IGNORE.get(k, set()))


def _constraint_policy_snapshot() -> dict:
    """Return an intent-aware constraint policy snapshot (UI/exports)."""
    k = _design_intent_key()
    return {
        "design_intent": str(st.session_state.get("design_intent", "Power Reactor (net-electric)")),
        "intent_key": k,
        "hard_blocking": sorted([str(x) for x in _INTENT_HARD.get(k, set())]),
        "diagnostic_only": sorted([str(x) for x in _INTENT_SOFT.get(k, set())]),
        "ignored": sorted([str(x) for x in _INTENT_IGNORE.get(k, set())]),
    }


def _classify_failed_constraints(failed_names: list[str] | None) -> dict:
    """Classify failed constraint names into blocking/diagnostic/ignored per current intent."""
    failed = [str(x) for x in (failed_names or [])]
    hard_set = _hard_constraint_names_for_intent()
    ign_set = _ignored_constraint_names_for_intent()
    blocking = [c for c in failed if c in hard_set]
    ignored = [c for c in failed if c in ign_set]
    diagnostic = [c for c in failed if (c not in blocking and c not in ignored)]
    return {"blocking": blocking, "diagnostic": diagnostic, "ignored": ignored}








# ---------------------------------------------------------------------------
# Integrity gate (requirements & health)
# ---------------------------------------------------------------------------
with st.sidebar.expander("Integrity Gate - Requirements & Health", expanded=False):
    """A reviewer-safe, deterministic health/requirements check.

    Important: Streamlit executes UI code even when an expander is closed; therefore we avoid
    auto-running anything here. The user explicitly presses the run button.
    """

    rep_path, reqs_path, reqs_json_path, runner_path = _verification_report_paths()

    # Lightweight health checks (no subprocess): these are instantaneous and always safe.
    def _health_rows() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            rows.append({"Check": "Python", "Status": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"})
        except Exception:
            rows.append({"Check": "Python", "Status": "unknown"})

        try:
            repo_ok = os.path.exists(os.path.join(ROOT_DIR, "MANIFEST_SHA256.txt"))
            rows.append({"Check": "Repo manifest", "Status": "present"if repo_ok else "missing"})
        except Exception:
            rows.append({"Check": "Repo manifest", "Status": "unknown"})

        try:
            out_dir = os.path.join(ROOT_DIR, "benchmarks", "publication")
            rows.append({"Check": "Benchmarks folder", "Status": "present"if os.path.isdir(out_dir) else "missing"})
        except Exception:
            rows.append({"Check": "Benchmarks folder", "Status": "unknown"})

        try:
            # Write-permission probe in the current working directory (deterministic + harmless)
            probe_dir = os.path.join(ROOT_DIR, ".shams_probe")
            os.makedirs(probe_dir, exist_ok=True)
            probe_file = os.path.join(probe_dir, "write_test.txt")
            with open(probe_file, "w", encoding="utf-8") as f:
                f.write("ok")
            rows.append({"Check": "Write access", "Status": "ok"})
        except Exception:
            rows.append({"Check": "Write access", "Status": "blocked"})
        return rows

    needs = _verification_needs_run()
    report_exists = os.path.exists(rep_path)
    status_line = (
        "Evidence report: up-to-date"if (report_exists and not needs) else
        "Evidence report: needs update"if report_exists else
        "Evidence report: missing"
    )
    st.caption("Run this only when you want an explicit, archived compliance report. Nothing runs automatically.")
    st.markdown(status_line)

    c1, c2 = st.columns([1, 1])
    force = c1.button("Run gatecheck", use_container_width=True)
    show_logs = c2.toggle("Show logs", value=bool(st.session_state.get("verify_show_logs", False)))
    st.session_state["verify_show_logs"] = show_logs

    # Provide the latest report (if present)
    if report_exists:
        try:
            rep_bytes = Path(rep_path).read_bytes()
            st.download_button(
                "Download evidence report (JSON)",
                data=rep_bytes,
                file_name="shams_verification_report.json",
                mime="application/json",
                use_container_width=True,
            )
        except Exception:
            st.caption("Evidence report download unavailable (read error).")

    with st.expander("Instant health snapshot", expanded=False):
        try:
            st.dataframe(pd.DataFrame(_health_rows()), hide_index=True, use_container_width=True)
        except Exception:
            st.json(_health_rows(), expanded=False)

    if force:
        with st.spinner("Running gatecheck (verification/run_verification.py)..."):
            ok, out, err, dt = _run_verification_capture()
        st.session_state["_last_verify_ok"] = ok
        st.session_state["_last_verify_out"] = out
        st.session_state["_last_verify_err"] = err
        st.session_state["_last_verify_dt"] = dt
        st.rerun()

    if st.session_state.get("_last_verify_dt") is not None:
        ok = bool(st.session_state.get("_last_verify_ok", False))
        (st.success if ok else st.error)(
            f"Last gatecheck: {'PASS' if ok else 'FAIL'} ({st.session_state.get('_last_verify_dt', 0.0):.2f}s)"
        )
        # If failing, surface a short, high-signal reason even when logs are hidden.
        if not ok:
            _e = (st.session_state.get("_last_verify_err", "") or "").strip()
            _o = (st.session_state.get("_last_verify_out", "") or "").strip()
            _msg = ""
            if _e:
                _msg = _e.splitlines()[0]
            elif _o:
                _msg = _o.splitlines()[0]
            if _msg:
                st.caption(f"Gatecheck detail: {_msg} (toggle **Show logs** for full output)")

    if show_logs:
        st.text_area("stdout", value=str(st.session_state.get("_last_verify_out", "")), height=160)
        st.text_area("stderr", value=str(st.session_state.get("_last_verify_err", "")), height=160)


# ---------------------------------------------------------------------------
# Fidelity + Calibration (transparent (systems-code-inspired), transparent)
# ---------------------------------------------------------------------------
with st.sidebar.expander("Model Authority & Closures", expanded=False):
    fid = st.session_state.get("fidelity_config", {})
    plasma = st.selectbox("Plasma", ["0D","1/2D"], index=0 if fid.get("plasma","0D")=="0D"else 1)
    magnets = st.selectbox("Magnets", ["limits","stress"], index=0 if fid.get("magnets","limits")=="limits"else 1)
    exhaust = st.selectbox("Exhaust", ["proxy","enriched"], index=0 if fid.get("exhaust","proxy")=="proxy"else 1)
    neutronics = st.selectbox("Neutronics", ["proxy","enriched"], index=0 if fid.get("neutronics","proxy")=="proxy"else 1)
    profiles = st.selectbox("Profiles", ["off","analytic"], index=0 if fid.get("profiles","off")=="off"else 1)
    economics = st.selectbox("Economics", ["proxy","enriched"], index=0 if fid.get("economics","proxy")=="proxy"else 1)
    st.session_state["fidelity_config"] = {
        "plasma": plasma,
        "magnets": magnets,
        "exhaust": exhaust,
        "neutronics": neutronics,
        "profiles": profiles,
        "economics": economics,
    }


with st.sidebar.expander("Reference calibration (optional)", expanded=False):
    st.caption("Transparent multiplicative factors (default 1.0). These are **declared knobs** (not a black‑box fit). "
               "They are recorded into artifacts for reviewer-safe reproducibility.")

    cL, cR = st.columns([1, 1])
    with cL:
        if st.button("Reset factors to 1.0", use_container_width=True):
            st.session_state["calib_confinement"] = 1.0
            st.session_state["calib_divertor"] = 1.0
            st.session_state["calib_bootstrap"] = 1.0
    with cR:
        st.markdown("**Scope**")
        st.markdown("- Confinement → τₑ / power balance")
        st.markdown("- Divertor → exhaust proxy severity")
        st.markdown("- Bootstrap → I_bs closure")

    st.session_state["calib_confinement"] = st.slider(
        "Confinement factor (H-like multiplier)",
        0.5, 1.5,
        float(st.session_state.get("calib_confinement", 1.0)),
        0.01,
        help="Multiplies the confinement closure used by the frozen evaluator. Use for reference calibration / sensitivity, not tuning for feasibility."
    )
    st.session_state["calib_divertor"] = st.slider(
        "Divertor factor (exhaust proxy multiplier)",
        0.5, 1.5,
        float(st.session_state.get("calib_divertor", 1.0)),
        0.01,
        help="Scales the exhaust/proxy model severity (e.g., q⊥-like gate). Recorded in artifacts."
    )
    st.session_state["calib_bootstrap"] = st.slider(
        "Bootstrap factor (I_bs multiplier)",
        0.5, 1.5,
        float(st.session_state.get("calib_bootstrap", 1.0)),
        0.01,
        help="Scales the bootstrap-current closure output prior to current-drive accounting. Recorded in artifacts."
    )


with st.sidebar.expander("Policy Contracts (feasibility semantics)", expanded=False):
    st.caption("Explicit, reviewer-visible enforcement tiering. This does **not** change physics outputs; it only changes whether selected limits are **blocking** or **diagnostic**.")
    _q95_prev = str(st.session_state.get("q95_enforcement","hard"))
    _fg_prev = str(st.session_state.get("greenwald_enforcement","hard"))
    st.session_state["q95_enforcement"] = st.selectbox(
        "q95 enforcement",
        ["hard", "diagnostic"],
        index=0 if str(st.session_state.get("q95_enforcement","hard")).lower().strip()=="hard"else 1,
        help="hard: blocking feasibility gate. diagnostic: computed and reported, but non-blocking (soft).",
    )
    st.session_state["greenwald_enforcement"] = st.selectbox(
        "Greenwald (fG) enforcement",
        ["hard", "diagnostic"],
        index=0 if str(st.session_state.get("greenwald_enforcement","hard")).lower().strip()=="hard"else 1,
        help="hard: blocking feasibility gate. diagnostic: computed and reported, but non-blocking (soft).",
    )
    st.markdown("**Contract**")
    st.markdown("- These settings affect constraint tiering only (HARD vs SOFT).")
    st.markdown("- They are recorded in artifacts under `_policy_contract`.")
    st.markdown("- No hidden iteration, no softening of physics.")

    if (str(st.session_state.get("q95_enforcement","hard")) != _q95_prev) or (str(st.session_state.get("greenwald_enforcement","hard")) != _fg_prev):
        _invalidate_mode_caches("policy_contract_changed")


with st.sidebar.expander("Technology Readiness (TRL Contracts)", expanded=False):
    st.caption("Explicit maturity tiering for governance and evidence packs. This does **not** re-solve physics; it records assumption tier and suggested caps for optional constraints.")
    _tier_prev = str(st.session_state.get("tech_tier", "TRL7"))
    _tiers = ["TRL3", "TRL5", "TRL7", "TRL9"]
    _tier = str(st.session_state.get("tech_tier", "TRL7")).upper().strip()
    if _tier not in _tiers:
        _tier = "TRL7"
    st.session_state["tech_tier"] = st.selectbox(
        "Technology readiness tier",
        _tiers,
        index=_tiers.index(_tier),
        help="Used to label maturity assumptions and (optionally) suggest default caps such as f_recirc_max and TBR_min. Recorded in outputs as _maturity_contract.",
    )
    try:
        from contracts.tech_tiers import suggested_defaults  # type: ignore
        _sug = dict(suggested_defaults(str(st.session_state.get("tech_tier","TRL7"))))
    except Exception:
        _sug = {}
    if _sug:
        with st.expander("Suggested defaults (optional)", expanded=False):
            st.json(_sug)
            st.caption("These are *suggestions* for optional caps; SHAMS truth is unchanged unless you explicitly apply them to inputs.")
    if str(st.session_state.get("tech_tier","TRL7")) != _tier_prev:
        _invalidate_mode_caches("tech_tier_changed")

with st.sidebar.expander("Benchmark Vault", expanded=False):
    tabs = st.tabs(["Presets", "Benchmarks"])
    with tabs[0]:
        st.caption("Load frozen, reviewer-safe reference machines into the workspace. Presets do **not** modify physics - they set inputs.")
        try:
            _ref_catalog = reference_catalog()
            _ref_keys = sorted(list(_ref_catalog.keys()))
        except Exception:
            _ref_catalog = {}
            _ref_keys = []

        _legacy_names = list(REFERENCE_MACHINES.keys())
        _choices = _ref_keys if _ref_keys else _legacy_names

        _sel = st.selectbox("Preset", _choices, index=0 if _choices else None)
        if _sel and _sel in _ref_catalog:
            _suite = str(_ref_catalog[_sel].get('suite','n/a'))
            _cls = str(_ref_catalog[_sel].get('class','n/a'))
            # User preference: keep details collapsed by default; only user expands.
            with st.expander(f"Suite: {_suite} · Class: {_cls}", expanded=False):
                st.code(_shams_json_dumps(_ref_catalog[_sel], indent=2), language="json")
        elif _sel and _sel in REFERENCE_MACHINES:
            st.markdown("**Legacy preset** (inline table).")
        if st.button("Load preset", use_container_width=True, disabled=not bool(_sel)):
            try:
                if _sel in _ref_catalog:
                    apply_reference_preset(_sel)
                else:
                    apply_legacy_reference_machine(_sel)
                st.success("Preset loaded into workspace inputs.")
            except Exception as e:
                st.error(f"Preset load failed: {e}")

    with tabs[1]:
        st.caption("Benchmark packs are deterministic evidence generators. Use **Publication Benchmarks** for full packs.")
        st.markdown("**Quick actions**")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Show last benchmark pack (if any)", use_container_width=True):
                _p = st.session_state.get("publication_benchmark_last_outdir")
                if _p:
                    st.code(str(_p))
                else:
                    st.info("No benchmark pack recorded in this session yet.")
        with c2:
            st.markdown("Tip: Run ` Publication Benchmarks → Generate Pack` for reviewer-safe CSV+JSON+hashes.")
# (Benchmark Vault rendered above)
_activity_log_sidebar_placeholder = st.sidebar.empty()


def _render_activity_log_sidebar() -> None:
    try:
        _lg = _activity_logger()
        with _activity_log_sidebar_placeholder.container():
            st.markdown("### Black-Box Chronicle")
            st.toggle(
                "Auto-log (recommended)",
                value=bool(st.session_state.get("activity_log_auto", True)),
                key="activity_log_auto",
            )
            _tail = st.number_input(
                "Show last N lines",
                min_value=50,
                max_value=2000,
                value=int(st.session_state.get("activity_log_tail", 200)),
                step=50,
                key="activity_log_tail",
            )

            # Always read from disk so the view reflects everything logged,
            # even if it happened later in this same run.
            try:
                tail_text = _lg.path.read_text(encoding="utf-8", errors="replace") if _lg.path.exists() else ""
            except Exception:
                tail_text = ""
            if int(_tail) > 0 and tail_text:
                tail_lines = tail_text.splitlines()[-int(_tail) :]
                tail_text = "\n".join(tail_lines)

            st.text_area(
                "Log (tail)",
                value=tail_text,
                height=220,
                key="activity_log_view",
                disabled=True,
            )

            _c1, _c2 = st.columns(2)
            with _c1:
                st.download_button(
                    "Download log",
                    data=(tail_text + "\n"if tail_text else ""),
                    file_name="activity.log",
                    mime="text/plain",
                    use_container_width=True,
                    key="activity_log_download",
                )
            with _c2:
                if st.button("Clear log", use_container_width=True, key="activity_log_clear_btn"):
                    try:
                        _alog("UI", "ClearLog", {})
                    except Exception:
                        pass

                    # Clear log on disk (authoritative: reflect immediately).
                    try:
                        _lg.clear()
                    except Exception:
                        pass
                    try:
                        st.session_state["activity_log_view"] = ""
                    except Exception:
                        pass
                    st.rerun()

            # -------------------------------------------------------------------
            # Session shutdown (Exit SHAMS) — MUST be visible in UI
            # -------------------------------------------------------------------
            st.markdown("---")
            st.markdown("### Session shutdown")
            _exit_confirm = st.checkbox(
                "Confirm exit",
                value=bool(st.session_state.get("shams_exit_confirm", False)),
                key="shams_exit_confirm",
                help="Safety latch to prevent accidental shutdown.",
            )
            if st.button(
                "Exit SHAMS",
                type="primary",
                use_container_width=True,
                disabled=not bool(_exit_confirm),
                key="shams_exit_btn",
                help="Hard-exit Streamlit process. Only reliable cross-platform shutdown.",
            ):
                try:
                    _alog("UI", "ExitRequested", {})
                except Exception:
                    pass
                st.info("SHAMS UI shutdown requested by user.")
                _os._exit(0)
    except Exception:
        # Never block UI.
        return

# Render once immediately so the panel is visible even if a downstream
# st.stop() occurs (some panels intentionally stop execution). We re-render
# again at end-of-file to include same-run events.
try:
    _render_activity_log_sidebar()
except Exception:
    pass

# ---------------------------------------------------------------------------
# Forward-definition bootstrap
#
# This UI file contains many panel functions defined *after* the main routing
# section. Streamlit executes top-to-bottom; if a panel is requested before its
# def is reached, it will appear as "not found". We proactively bootstrap the
# panel defs that are referenced by contracts/layer registry.
# ---------------------------------------------------------------------------
try:
    from ui.layer_registry import get_layer_registry
    _reg = get_layer_registry()
    _panel_names = []
    for _layer in _reg.get("layers", []):
        for _p in _layer.get("panels", []):
            n = _p.get("fn") or _p.get("panel_fn") or _p.get("fn_name")
            if isinstance(n, str) and n.startswith("_v"):
                _panel_names.append(n)
    # Also include all contract-registered panels.
    try:
        from ui.panel_contracts import get_panel_contracts
        _panel_names.extend(list(get_panel_contracts().keys()))
    except Exception:
        pass
    _panel_names = _unique(_panel_names)
    if _panel_names:
        _bootstrap_forward_defs(_panel_names)
except Exception:
    # Never block UI on bootstrap failure.
    pass


# --- Deck Navigation (v372.2 hotfix) ---
# Streamlit tabs reset to the first tab on reruns, which can cause the UI to "jump"back
# to Point Designer when interacting with other decks (and can unbind solver parameter
# names on button-click reruns). We therefore use a deterministic, persisted deck selector.
# Deck IDs are plain strings (UI redesign: emoji removed from navigation and
# routing). The sidebar radio stores the selected label directly; nav_deck_index
# (integer) persists selection across reruns. All `if _deck == "<plain>"` routing
# comparisons throughout app.py use these same plain IDs.
_DECK_LABELS = [
    "Point Designer",
    "Systems Mode",
    "Scan Lab",
    "Pareto Lab",
    "Trade Study Studio",
    "Reactor Design Forge",
    "System Suite",
    "Compare",
    "Publication Benchmarks",
    "Control Room",
]
with st.sidebar:
    st.markdown("## Navigation")
    _sel = st.radio(
        "Deck",
        _DECK_LABELS,
        index=int(st.session_state.get("nav_deck_index", 0)),
        label_visibility="collapsed",
        key="nav_deck_label",
    )
    st.session_state["nav_deck_index"] = _DECK_LABELS.index(_sel)
_deck = _sel

# Phase-1 cache aliasing (no compute, no truth mutation)
try:
    _phase1_stabilize_cache_aliases()
except Exception:
    pass




if _deck == "System Suite":
    from ui.decks.system_suite import render_system_suite
    render_system_suite(sys.modules[__name__])




if _deck == "Publication Benchmarks":
    from ui.decks.publication_benchmarks import render_publication_benchmarks
    render_publication_benchmarks(sys.modules[__name__])

if _deck == "Control Room":
    from ui.decks.control_room import render_control_room
    render_control_room(sys.modules[__name__])
    
# Shared state
if "last_point_out"not in st.session_state:
    st.session_state["last_point_out"] = None
if "last_point_inp"not in st.session_state:
    st.session_state["last_point_inp"] = None
if "scan_df"not in st.session_state:
    st.session_state.scan_df = pd.DataFrame()
if "scan_meta"not in st.session_state:
    st.session_state.scan_meta = {}
if "studies"not in st.session_state:
    st.session_state.studies = []  # list of study config dicts
if "compare_artifacts"not in st.session_state:
    st.session_state.compare_artifacts = {"A": None, "B": None}

# -----------------------------
# Point Designer
# -----------------------------
if _deck == "Point Designer":
    from ui.decks.point_designer import render_point_designer
    render_point_designer(sys.modules[__name__])
if _deck == "Systems Mode":
    from ui.decks.systems_mode import render_systems_mode
    render_systems_mode(sys.modules[__name__])

if _deck == "Scan Lab":
    from ui.decks.scan_lab import render_scan_lab
    render_scan_lab(sys.modules[__name__])
if _deck == "Pareto Lab":
    from ui.decks.pareto_lab import render_pareto_lab
    render_pareto_lab(sys.modules[__name__])


if _deck == "Trade Study Studio":
    from ui.decks.trade_study_studio import render_trade_study_studio
    render_trade_study_studio(sys.modules[__name__])


if _deck == "Reactor Design Forge":
    from ui.decks.reactor_design_forge import render_reactor_design_forge
    render_reactor_design_forge(sys.modules[__name__])


if _deck == "Compare":
    from ui.decks.compare import render_compare
    render_compare(sys.modules[__name__])

# (v372.8.7) Studies manager is rendered inside Control Room → Studies tab (no tab-handle leakage).
# The previous module-scope `with tab_studies:` block was removed to satisfy UI law.




# -----------------------------
# Benchmarks
# -----------------------------
    
        # -----------------------------
        # Variable Registry (auditable meanings/units/sources)
        # -----------------------------

# -----------------------------
# Validation (envelopes)
# -----------------------------


# -----------------------------
# Compliance (requirements + model cards)
# -----------------------------




# -----------------------------
# Artifacts Explorer (new)
# -----------------------------
def _load_json_from_upload(uploaded) -> Dict[str, Any] | None:
    if uploaded is None:
        return None
    try:
        raw = uploaded.getvalue()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)
    except Exception:
        return None


def _safe_df(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    try:
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


def _as_float(x) -> float | None:
    try:
        if x is None:
            return None
        if isinstance(x, bool):
            return None
        return float(x)
    except Exception:
        return None


def _numeric_delta_table(base_out: Dict[str, Any], scen_out: Dict[str, Any], limit: int = 40) -> pd.DataFrame:
    keys = sorted(set(base_out.keys()) | set(scen_out.keys()))
    rows = []
    for k in keys:
        a = _as_float(base_out.get(k))
        b = _as_float(scen_out.get(k))
        if a is None or b is None:
            continue
        d = b - a
        # skip near-identical
        if abs(d) < 1e-12:
            continue
        rows.append({"metric": k, "baseline": a, "scenario": b, "delta": d, "delta_frac": (d / a) if abs(a) > 1e-12 else None})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.reindex(df["delta"].abs().sort_values(ascending=False).index)
    return df.head(limit)




# -----------------------------
# Case Deck Runner (new)
# -----------------------------


# -----------------------------
# Authority & Confidence (v256.0)
# -----------------------------


# -----------------------------
# Decision Consequences (v257.0)
# -----------------------------


# ----------------------------------
# Authority Dominance Engine (v330.0)
# ----------------------------------


# -----------------------------
# Scenario Delta Viewer (new)
# -----------------------------




# -----------------------------
# Run Library (Workspace)
# -----------------------------

# -----------------------------
# Constraint Cockpit
# -----------------------------


# -----------------------------
# Constraint Inspector (read-only)
# -----------------------------


# -----------------------------
# Sensitivity Explorer
# -----------------------------

# -----------------------------
# Feasibility Map Viewer
# -----------------------------


# -----------------------------
# UI Upgrade Pack v53 (UI-only): decision/provenance/knobs/regression/study dashboard/maturity/assumptions/export/solver introspection
# -----------------------------
def _get_active_artifact(label: str = "Use loaded artifact in session") -> dict | None:
    "Return the currently active artifact (from session_state or upload)."
    art = st.session_state.get("selected_artifact")
    if isinstance(art, dict) and art:
        st.info("Using artifact loaded into session (Run Library / Feasibility Map).")
        return art
    up = st.file_uploader("Upload shams_run_artifact.json", type=["json"], key=f"active_artifact_upload_{label}")
    return _load_json_from_upload(up)

def _guess_point_inputs_from_artifact(art: dict) -> PointInputs | None:
    "Best-effort extraction of PointInputs from an artifact. Falls back safely."
    if not isinstance(art, dict):
        return None
    cand = {}
    for k in ["inputs", "point", "point_inputs", "design_point", "config", "run_config", "resolved_config"]:
        v = art.get(k)
        if isinstance(v, dict):
            cand.update(v)
    cand.update({k: art.get(k) for k in ["R0_m","a_m","kappa","Bt_T","B0_T","Ip_MA","Ti_keV","fG","Paux_MW","Ti_over_Te","fuel_mode"] if k in art})
    if "B0_T"in cand and "Bt_T"not in cand:
        cand["Bt_T"] = cand["B0_T"]
    if "Ti_Te"in cand and "Ti_over_Te"not in cand:
        cand["Ti_over_Te"] = cand["Ti_Te"]
    if "Ti/Te"in cand and "Ti_over_Te"not in cand:
        cand["Ti_over_Te"] = cand["Ti/Te"]
    try:
        return _make_point_inputs_safe(**cand)
    except Exception:
        return None

def _decision_summary_from_artifact(art: dict) -> dict:
    kpis = art.get("kpis", {}) if isinstance(art.get("kpis"), dict) else {}
    cons = art.get("constraints", []) if isinstance(art.get("constraints"), list) else []
    ledger = art.get("constraint_ledger", {}) if isinstance(art.get("constraint_ledger"), dict) else {}
    feas = bool(art.get("is_feasible")) if "is_feasible"in art else None
    if feas is None:
        feas = all((not bool(c.get("failed"))) for c in cons) if cons else None
    top = ledger.get("top_blockers") if isinstance(ledger.get("top_blockers"), list) else []
    if not top and cons:
        failed = [c for c in cons if c.get("failed")]
        failed = failed[:8]
        top = [{"name": c.get("name"), "group": c.get("group"), "margin": c.get("margin"), "severity": c.get("severity")} for c in failed]
    return {"feasible": feas, "kpis": kpis, "top_blockers": top, "ledger": ledger, "constraints": cons}

def _download_json_button(label: str, data: dict, fname: str, key: str):
    try:
        st.download_button(label, data=json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"),
                           file_name=fname, mime="application/json", key=key)
    except Exception as e:
        st.warning(f"Download not available: {e}")



























# --- Copyright notice
st.markdown('---')
st.caption('© 2026 Afshin Arjhangmehr - SHAMS–FUSION-X')


# =====================
# v88 UI helpers (append-only)
# =====================
def _v88_continuation_explorer(path):
    import pandas as pd, streamlit as st
    if not path:
        st.info("No continuation path available.")
        return
    df = pd.DataFrame(path)
    st.line_chart(df.select_dtypes("number"))

def _v88_boundary_map(points):
    import pandas as pd, streamlit as st
    if not points:
        st.info("No scan points available.")
        return
    df = pd.DataFrame(points)
    if "x"in df.columns and "min_signed_margin"in df.columns:
        st.scatter_chart(df, x="x", y="min_signed_margin", color="feasible")

def _v88_export_svg(fig, name):
    import io, streamlit as st
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    st.download_button(
        f"Download {name}.svg",
        data=buf.getvalue(),
        file_name=f"{name}.svg",
        mime="image/svg+xml",
    )


# =====================
# v89 UI helpers (append-only)
# =====================
def _v89_margin_waterfall_fig(constraints):
    import matplotlib.pyplot as plt
    rows = []
    for r in constraints or []:
        name = r.get("name","")
        sm = r.get("signed_margin", None)
        if name and isinstance(sm, (int,float)):
            rows.append((name, float(sm)))
    if not rows:
        return None
    rows.sort(key=lambda x: x[1])
    names = [n for n,_ in rows][:40]
    vals = [v for _,v in rows][:40]
    fig, ax = plt.subplots()
    ax.barh(names, vals)
    ax.axvline(0.0)
    ax.set_xlabel("signed_margin")
    ax.set_title("Constraint Margin Waterfall")
    fig.tight_layout()
    return fig

def _v89_boundary_heatmap(points, xcol, ycol):
    import numpy as np
    import matplotlib.pyplot as plt
    xs = [p.get(xcol) for p in points]
    ys = [p.get(ycol) for p in points]
    xs = [x for x in xs if isinstance(x,(int,float))]
    ys = [y for y in ys if isinstance(y,(int,float))]
    if not xs or not ys:
        return None
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    nx, ny = 40, 40
    grid = np.full((ny, nx), np.nan)
    counts = np.zeros((ny, nx), dtype=int)
    hits = np.zeros((ny, nx), dtype=int)
    for p in points:
        x = p.get(xcol); y = p.get(ycol)
        if not isinstance(x,(int,float)) or not isinstance(y,(int,float)):
            continue
        ix = int((x - x_min) / (x_max - x_min + 1e-12) * (nx-1))
        iy = int((y - y_min) / (y_max - y_min + 1e-12) * (ny-1))
        counts[iy, ix] += 1
        hits[iy, ix] += 1 if p.get("feasible", False) else 0
    mask = counts > 0
    grid[mask] = hits[mask] / counts[mask]
    fig, ax = plt.subplots()
    im = ax.imshow(grid, origin="lower", extent=[x_min,x_max,y_min,y_max], aspect="auto")
    ax.set_xlabel(xcol)
    ax.set_ylabel(ycol)
    ax.set_title("Feasibility Boundary Map (binned feasibility fraction)")
    fig.colorbar(im, ax=ax, label="feasible fraction")
    fig.tight_layout()
    return fig

def _v89_constraint_intersections(points, topn=10):
    from collections import Counter
    c = Counter()
    for p in points:
        if p.get("feasible", False):
            continue
        acts = p.get("active_constraints", [])
        if not isinstance(acts, list):
            continue
        acts = [a for a in acts if isinstance(a,str) and a][:6]
        for i in range(len(acts)):
            for j in range(i+1, len(acts)):
                pair = tuple(sorted((acts[i], acts[j])))
                c[pair] += 1
    return c.most_common(topn)


# =====================
# v89.1 UI state persistence helpers (append-only)
# =====================
def _v89_1_render_cached_point():
    import streamlit as st
    if "pd_last_outputs"not in st.session_state or "pd_last_artifact"not in st.session_state:
        st.info("No cached Point Designer result yet. Click 'Evaluate Point' to compute one.")
        return
    st.info("Showing last Point Designer results (cached). Downloads should not clear results.")

    out = st.session_state["pd_last_outputs"]
    artifact = st.session_state["pd_last_artifact"]

    # KPI summary (best effort)
    try:
        with st.expander("Point summary (cached)", expanded=False):
            kpis = headline_kpis(out)
            for i in range(0, len(kpis), 4):
                kpi_row(kpis[i:i+4])
    except Exception:
        pass

    # Exports (cached bytes if available)
    with st.expander("Exports (external systems codes-style artifacts) - cached", expanded=False):
        try:
            st.download_button(
                "Download run artifact JSON",
                data=_shams_json_dumps(artifact, indent=2, sort_keys=True),
                file_name="shams_run_artifact.json",
                mime="application/json",
                use_container_width=True,
                key="pd_cached_artifact_json",
            )
        except Exception:
            pass

        # Radial build PNG (prefer cached bytes)
        state = st.session_state.get('shams_state', None)
        rb = (
            state.last_point_radial_png
            if state and getattr(state, 'last_point_radial_png', None) is not None
            else st.session_state.get("pd_last_radial_png_bytes", None)
        )
        if isinstance(rb, (bytes, bytearray)) and len(rb) > 0:
            st.download_button(
                "Download radial build PNG",
                data=rb,
                file_name="shams_radial_build.png",
                mime="image/png",
                use_container_width=True,
                key="pd_cached_radial_png",
            )
        else:
            # Generate on demand (still should not clear results since out/artifact is cached)
            try:
                tmpdir = tempfile.mkdtemp(prefix="shams_export_")
                radial_path = os.path.join(tmpdir, "radial_build.png")
                plot_radial_build_from_artifact(artifact, radial_path)
                with open(radial_path, "rb") as f:
                    st.download_button(
                        "Download radial build PNG",
                        data=f.read(),
                        file_name="shams_radial_build.png",
                        mime="image/png",
                        use_container_width=True,
                        key="pd_cached_radial_png_gen",
                    )
            except Exception:
                st.caption("Radial-build export unavailable for this point.")


# =====================
# v89.2 UI state persistence + controls (append-only)
# =====================
def _v89_2_point_cache_ui():
    import streamlit as st
    st.subheader("Cached Point Designer Result")
    c1, c2 = st.columns([1,3])
    with c1:
        if st.button("Clear cached result", key="pd_clear_cache"):
            for k in ["pd_last_outputs", "pd_last_artifact", "pd_last_radial_png_bytes"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.success("Cleared.")
            st.stop()
    with c2:
        st.caption("Cached results persist across reruns (e.g., after downloads).")

    state = st.session_state.get('shams_state', None)
    art = (state.last_point_artifact if state and getattr(state,'last_point_artifact',None) is not None else st.session_state.get("pd_last_artifact", None))
    out = (state.last_point_outputs if state and getattr(state,'last_point_outputs',None) is not None else st.session_state.get("pd_last_outputs", None))
    if art is None or out is None:
        st.info("No cached result yet. Run Point Designer once to populate this.")
        return

    rb = (state.last_point_radial_png if state and getattr(state,'last_point_radial_png',None) is not None else st.session_state.get("pd_last_radial_png_bytes", None))
    if isinstance(rb, (bytes, bytearray)) and len(rb) > 0:
        st.image(rb, caption="Radial build (cached export preview)", use_container_width=True)

    import json as _json
    st.download_button(
        "Download run artifact JSON",
        data=_json.dumps(art, indent=2, sort_keys=True),
        file_name="shams_run_artifact.json",
        mime="application/json",
        use_container_width=True,
        key="pd_dl_artifact_cached",
    )
    if isinstance(rb, (bytes, bytearray)) and len(rb) > 0:
        st.download_button(
            "Download radial build PNG",
            data=rb,
            file_name="shams_radial_build.png",
            mime="image/png",
            use_container_width=True,
            key="pd_dl_radial_cached",
        )



# =====================
# v92 UI state-machine helpers (append-only)
# =====================
# (Defined early in Phase-1 stabilization block to avoid forward-reference failures.)

# v93 UI helpers (append-only)
# =====================
# -----------------------------
# JSON safety helpers (cycle-safe) - required for export/download stability
# -----------------------------
def _v93_validate_before_download(obj, schema_path: str):
    """Return (ok, errors). Uses jsonschema if available, else fallback."""
    import json as _json
    from pathlib import Path
    try:
        sch = _json.loads(Path(schema_path).read_text(encoding="utf-8"))
        try:
            import jsonschema  # type: ignore
            jsonschema.validate(instance=obj, schema=sch)
            return True, []
        except ImportError:
            from tools.validate_schemas import _fallback_validate
            errs = _fallback_validate(obj, sch)
            return (len(errs) == 0), errs
    except Exception as e:
        return False, [repr(e)]

def _v93_paper_figures_pack_panel():
    import streamlit as st
    s = _v92_state_get()
    st.subheader("Paper Figures Pack")
    if not s.has_point():
        st.info("Run Point Designer first; pack is built from cached Point artifact.")
        return
    try:
        from tools.paper_figures_pack import build_figures_pack_bytes
        if st.button("Build paper figures pack", key="v93_build_figpack"):
            s.last_figures_pack_zip = build_figures_pack_bytes(s.last_point_artifact)
            st.success("Figures pack built.")
        b = getattr(s, "last_figures_pack_zip", None)
        if isinstance(b, (bytes, bytearray)) and len(b) > 0:
            st.download_button(
                "Download paper_figures_pack.zip",
                data=b,
                file_name="paper_figures_pack.zip",
                mime="application/zip",
                use_container_width=True,
                key="v93_dl_figpack",
            )
    except Exception:
        st.caption("Figures pack unavailable.")


def _v93_stateful_scan_panel():
    import streamlit as st
    s = _v92_state_get()
    st.subheader("Scan Ledger (cached artifact)")
    if s.last_scan_points is None:
        st.info("No cached scan yet.")
        return
    scan_obj = {"kind":"shams_feasible_set","meta": s.last_scan_meta or {}, "points": s.last_scan_points}
    ok, errs = _v93_validate_before_download(scan_obj, "schemas/shams_feasible_set.schema.json")
    if ok: st.success("Schema: PASS")
    else:
        st.warning("Schema: FAIL")
        for e in errs[:10]: st.write("- "+ str(e))
    st.download_button("Download feasible_scan.json (stateful)",
                       data=_json.dumps(scan_obj, indent=2, sort_keys=True),
                       file_name="feasible_scan.json", mime="application/json",
                       use_container_width=True, key="v93_dl_scan_stateful")

def _v93_stateful_systems_panel():
    import streamlit as st
    s = _v92_state_get()
    st.subheader("Run Ledger (cached artifacts)")
    if s.last_systems_result is None:
        if s.has_point():
            st.info("No cached systems yet (no successful Systems solve). Point artifact is available - run a Systems solve to generate a Systems artifact.")
        else:
            st.info("No cached systems yet.")
        return
    ok, errs = _v93_validate_before_download(s.last_systems_result, "schemas/shams_run_artifact.schema.json")
    if ok: st.success("Schema: PASS")
    else:
        st.warning("Schema: FAIL")
        for e in errs[:10]: st.write("- "+ str(e))
    st.download_button("Download systems_artifact.json (stateful)",
                       data=_shams_json_dumps(s.last_systems_result, indent=2, sort_keys=True),
                       file_name="systems_artifact.json", mime="application/json",
                       use_container_width=True, key="v93_dl_systems_stateful")


def _v182_render_latest_systems_solve_results(*, artifact: dict, point_artifact: dict | None = None, key_prefix: str = "v182_latest"):
    """Render the latest Systems *solve* results from a cached run artifact.

    This MUST be safe across Streamlit reruns (e.g., download_button triggers rerun).
    Therefore it takes a fully self-contained artifact and does not rely on locals.
    """
    import streamlit as st
    import json

    # Schema hardening: upgrade + validate (non-fatal; never blocks UI)
    try:
        try:
            from src.systems.schema import upgrade_systems_artifact, validate_systems_artifact
        except Exception:  # pragma: no cover
            from systems.schema import upgrade_systems_artifact, validate_systems_artifact
        artifact = upgrade_systems_artifact(artifact or {})
        _issues = validate_systems_artifact(artifact)
        if _issues:
            with st.expander("Schema warnings (non-fatal)", expanded=False):
                for msg in _issues:
                    st.warning(msg)
    except Exception:
        pass
    try:
        outs = (artifact or {}).get('headline') or (artifact or {}).get('outputs') or {}
    except Exception:
        outs = {}

    st.markdown("### Latest Systems solve results")
    # Unique suffix so this function can be called multiple times in the same Streamlit run
    try:
        _rid = (artifact or {}).get("rid") or (artifact or {}).get("run_id") or (artifact or {}).get("metadata", {}).get("rid")
    except Exception:
        _rid = None
    try:
        _suffix = str(_rid) if _rid else __import__("hashlib").sha1(__import__("json").dumps(artifact, sort_keys=True).encode("utf-8")).hexdigest()[:10]
    except Exception:
        _suffix = "na"
    _k_art = f"{key_prefix}_dl_systems_artifact_{_suffix}"
    _k_zip = f"{key_prefix}_dl_systems_bundle_{_suffix}"

    # Always-available downloads (do not depend on a button-click run path)
    st.download_button(
        "Download systems-mode run artifact JSON",
        data=_shams_json_dumps(artifact, indent=2, sort_keys=True),
        file_name="shams_run_artifact_systems.json",
        mime="application/json",
        use_container_width=True,
        key=_k_art,
    )

    # Optional export bundle (safe; uses cached artifacts)
    try:
        from tools.export.bundle import build_export_bundle_bytes
        bundle_bytes = build_export_bundle_bytes(
            repo_root=BASE_DIR,
            point_artifact=point_artifact,
            systems_artifact=artifact,
            scan_artifact=None,
            pareto_artifact=None,
            opt_artifact=None,
            feasible_search_artifact=None,
            include_readme=True,
        )
        st.download_button(
            "Download export bundle ZIP",
            data=bundle_bytes,
            file_name="shams_export_bundle_systems.zip",
            mime="application/zip",
            use_container_width=True,
            key=_k_zip,
        )
    except Exception as _e:
        st.caption(f"Export bundle unavailable: {_e}")

    # Key results
    kcols = st.columns(4)
    def _k(col, key, fmt="{:.3g}"):
        try:
            v = float(outs.get(key, float('nan')))
        except Exception:
            v = float('nan')
        with col:
            st.metric(key, fmt.format(v) if v == v else "NaN")

    _k(kcols[0], "Q_DT_eqv")
    _k(kcols[1], "H98")
    _k(kcols[2], "P_e_net_MW")
    _k(kcols[3], "q_div_MW_m2")

    # Constraints table (if present)
    try:
        rows = (artifact or {}).get('constraints')
        if isinstance(rows, list) and rows:
            with st.expander("Constraints & margins (cached)", expanded=False):
                import pandas as pd
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
    except Exception:
        pass

def _v184_render_latest_feasible_search_results(*, report: dict, key_prefix: str = "v184_fs_latest") -> None:
    """Rerun-safe renderer for Feasible Design Search results.

    The search is easy to 'lose' in Streamlit after a button click because the app reruns and
    the workflow step may change. This renderer provides a stable, cached view.
    """
    import streamlit as st
    try:
        import pandas as pd
    except Exception:
        pd = None  # type: ignore

    if not isinstance(report, dict) or not report:
        st.info("No cached feasible-search results yet.")
        return

    ok = bool(report.get('ok'))
    reason = str(report.get('reason', ''))
    obj = str(report.get('objective', ''))
    ts_unix = report.get('ts_unix')
    try:
        ts_str = datetime.datetime.fromtimestamp(float(ts_unix)).strftime('%Y-%m-%d %H:%M:%S') if ts_unix else ''
    except Exception:
        ts_str = ''

    if ok:
        st.success(f"Feasible Search: **OK** - {reason} - best objective: {report.get('best_obj')} {('(' + ts_str + ')') if ts_str else ''}")
    else:
        st.warning(f"Feasible Search: **NO RESULT** - {reason} {('(' + ts_str + ')') if ts_str else ''}")

    # Compact summary
    st.json({k: report.get(k) for k in ['ok','reason','objective','budget','topk','multi_seed_runs','radius','seed','vars','start_feasible','best_obj','best_V'] if k in report})

    # Download JSON (stable key prefix avoids duplicates)
    try:
        st.download_button(
            label="Download feasible-search artifact JSON",
            data=_shams_json_dumps(report, indent=2, sort_keys=True),
            file_name="feasible_search_artifact.json",
            mime="application/json",
            key=f"{key_prefix}_dl_fs_artifact",
            use_container_width=True,
        )
    except Exception:
        pass

    # Candidates table
    try:
        cands = list(report.get('candidates', []) or [])
        if cands and pd is not None:
            rows = []
            for i, c in enumerate(cands):
                x = c.get('x', {}) or {}
                m = c.get('margins', {}) or {}
                row = {'rank': i+1, 'obj': c.get('obj'), 'V': c.get('V'), 'feasible': c.get('feasible')}
                # Common margins (if present)
                for nm in ['q95','q_div','P_SOL/R','B_peak','sigma_vm','HTS margin','TBR','NWL']:
                    if nm in m:
                        row[f'm_{nm}'] = m.get(nm)
                # Variables
                for k in (report.get('vars', []) or []):
                    row[k] = x.get(k)
                rows.append(row)
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
    except Exception:
        pass

def _v93_stateful_sandbox_panel():
    import streamlit as st
    s = _v92_state_get()
    st.subheader("Forge Cache (stateful sandbox)")
    if s.last_sandbox_run is None:
        st.info("No cached sandbox yet.")
        return
    st.download_button("Download sandbox_run.json (stateful)",
                       data=_json.dumps(s.last_sandbox_run, indent=2, sort_keys=True),
                       file_name="sandbox_run.json", mime="application/json",
                       use_container_width=True, key="v93_dl_sandbox_stateful")


# =====================
# v94 Run Records + Unified Export (append-only)
# =====================
def _v94_record_run(kind: str, payload: dict):
    import time
    s = _v92_state_get()
    try:
        s.run_history.append({
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "kind": kind,
            "summary": {
                "feasible": payload.get("meta", {}).get("feasible", payload.get("feasible", None)),
                "version": payload.get("version", None),
            },
        })
    except Exception:
        pass

def _v94_run_records_page():
    import streamlit as st
    s = _v92_state_get()
    st.subheader("Run Records")
    st.caption("Timeline of actions in this session.")
    if not s.run_history:
        st.info("No run records yet.")
        return
    for i, r in enumerate(reversed(s.run_history[-50:]), 1):
        st.write(f"{i}. {r.get('ts','?')} - {r.get('kind','?')} - {r.get('summary',{})}")

def _v94_unified_export_bundle_panel():
    import streamlit as st
    from pathlib import Path
    s = _v92_state_get()
    st.subheader("Unified Export Bundle")
    st.caption("One zip: artifacts + capsule + schemas + figures pack. Best-effort.")
    if not (s.has_point() or s.last_systems_result or s.last_scan_points or s.last_sandbox_run):
        st.info("Nothing cached yet. Run at least one mode first.")
        return

    scan_obj = None
    if s.last_scan_points is not None:
        scan_obj = {"kind":"shams_feasible_set","meta": s.last_scan_meta or {}, "points": s.last_scan_points}

    # Validation summary (best-effort)
    if s.has_point():
        ok, errs = _v93_validate_before_download(s.last_point_artifact, "schemas/shams_run_artifact.schema.json")
        if ok: st.success("Point artifact schema: PASS")
        else:
            st.warning("Point artifact schema: FAIL")
            for e in errs[:8]: st.write("- "+ str(e))
    if scan_obj is not None:
        ok, errs = _v93_validate_before_download(scan_obj, "schemas/shams_feasible_set.schema.json")
        if ok: st.success("Scan feasible set schema: PASS")
        else:
            st.warning("Scan feasible set schema: FAIL")
            for e in errs[:8]: st.write("- "+ str(e))

    try:
        from tools.export.bundle import build_export_bundle_bytes
        if st.button("Build unified export bundle", key="v94_build_bundle"):
            b = build_export_bundle_bytes(
                repo_root=Path("."),
                point_artifact=s.last_point_artifact if s.has_point() else None,
                systems_artifact=s.last_systems_result,
                feasible_search_artifact=getattr(s, "last_feasible_search_artifact", None),
                certified_search_artifact=st.session_state.get("last_certified_search_artifact", None),
                repair_evidence_artifact=st.session_state.get("last_repair_evidence_artifact", None),
                interval_refinement_artifact=st.session_state.get("last_interval_refinement_artifact", None),
                scan_artifact=scan_obj,
                pareto_artifact=getattr(s, "last_pareto_artifact", None),
                opt_artifact=getattr(s, "last_opt_artifact", None),
                sandbox_run=s.last_sandbox_run,
                figures_pack_zip=getattr(s, "last_figures_pack_zip", None),
            )
            st.session_state["v94_bundle_bytes"] = b
            st.success("Bundle built.")
        b = st.session_state.get("v94_bundle_bytes", None)
        if isinstance(b, (bytes, bytearray)) and len(b) > 0:
            st.download_button("Download shams_export_bundle.zip", data=b,
                               file_name="shams_export_bundle.zip", mime="application/zip",
                               use_container_width=True, key="v94_dl_bundle")
    except Exception as e:
        st.error(f"Bundle builder unavailable: {e!r}")



# =====================
# v98 validation gate (append-only)
# =====================
def _v98_validation_gate_ui(title: str, ok: bool, errs):
    import streamlit as st
    if ok:
        st.success(f"{title}: schema PASS")
        return True
    st.error(f"{title}: schema FAIL (download allowed, but NOT publishable)")
    for e in (errs or [])[:12]:
        st.write("- "+ str(e))
    return False


# =====================

# =====================
# v98 Run Ledger (append-only)
# =====================
def _v98_state_init_runlists():
    import streamlit as st
    s = _v92_state_get()
    if getattr(s, "run_history", None) is None: s.run_history = []
    if getattr(s, "pinned_run_ids", None) is None: s.pinned_run_ids = []
    # v130: persistent run vault (opt-in, default ON)
    if 'vault_enabled' not in st.session_state:
        st.session_state['vault_enabled'] = True
    if 'vault_limit' not in st.session_state:
        st.session_state['vault_limit'] = 50
    return s

def _v98_make_run_id(prefix: str) -> str:
    import time, random
    return f"{prefix}_{int(time.time())}_{random.randint(1000,9999)}"

def _v98_record_run(kind: str, payload, mode: str = "") -> str:
    import streamlit as st
    from tools import run_vault
    from pathlib import Path
    import time
    s = _v98_state_init_runlists()
    rid = _v98_make_run_id(kind)
    s.run_history.append({"id": rid, "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "kind": kind, "mode": mode, "payload": payload})
    try:
        _alog(mode or kind, 'RecordRun', {'rid': rid, 'kind': kind})
    except Exception:
        pass  # ActivityLogRecordRun

    # v130: persist to vault (storage only) - must never break UI
    try:
        if bool(st.session_state.get("vault_enabled", True)):
            root = Path(__file__).resolve().parents[1]
            run_vault.write_entry(root=root, kind=kind, payload=payload, mode=mode, tags={"rid": rid})
    except Exception:
        pass

    return rid


def _v98_json_diff(a, b, path=""):
    diffs = []
    if type(a) != type(b):
        diffs.append(path or "<root>"); return diffs
    if isinstance(a, dict):
        keys = set(a.keys()) | set(b.keys())
        for k in sorted(keys):
            diffs += _v98_json_diff(a.get(k, "<missing>"), b.get(k, "<missing>"), (path + "/"+ str(k)) if path else "/"+ str(k))
        return diffs
    if isinstance(a, list):
        n = max(len(a), len(b))
        for i in range(n):
            diffs += _v98_json_diff(a[i] if i < len(a) else "<missing>", b[i] if i < len(b) else "<missing>", f"{path}[{i}]")
        return diffs
    if a != b: diffs.append(path or "<root>")
    return diffs

def _v98_run_ledger_page():
    import streamlit as st
    s = _v98_state_init_runlists()
    st.subheader("Run Ledger")
    st.caption("Session-persistent run artifacts with pin/compare.")
    if not s.run_history:
        st.info("No recorded runs yet.")
        return
    for r in reversed(s.run_history[-100:]):
        rid = r.get("id")
        c1,c2,c3 = st.columns([3,1,1])
        with c1: st.write(f"**{rid}** - {r.get('ts')} - {r.get('kind')} ({r.get('mode')})")
        with c2:
            pinned = rid in s.pinned_run_ids
            if st.button("Unpin"if pinned else "Pin", key=f"pin_{rid}"):
                if pinned: s.pinned_run_ids.remove(rid)
                else: s.pinned_run_ids.append(rid)
                st.rerun()
        with c3:
            st.download_button("JSON", data=_json.dumps(r.get("payload", {}), indent=2, sort_keys=True), file_name=f"{rid}.json", mime="application/json", key=f"dl_{rid}")
    st.divider()
    st.subheader("Compare two pinned runs")
    pins = list(s.pinned_run_ids)
    if len(pins) < 2:
        st.info("Pin at least two runs to compare.")
        return
    a_id = st.selectbox("Run A", pins, key="cmp_a")
    b_id = st.selectbox("Run B", pins, index=1, key="cmp_b")
    A = next((x for x in s.run_history if x.get("id")==a_id), None)
    B = next((x for x in s.run_history if x.get("id")==b_id), None)
    if A and B:
        diffs = _v98_json_diff(A.get("payload",{}), B.get("payload",{}))
        st.write(f"Changed fields: {len(diffs)}")
        for d in diffs[:200]: st.write("- "+ d)


def _v98_process_handoff_panel():
    import streamlit as st
    s = _v92_state_get()
    st.subheader("external systems codes Handoff")
    st.caption("Exports a external systems codes-oriented handoff JSON (SHAMS upstream feasibility auditor).")
    if not s.has_point():
        st.info("Run Point Designer first.")
        return
    from tools.interoperability.process_handoff import make_process_handoff
    ho = make_process_handoff(s.last_point_artifact)
    ok, errs = _v93_validate_before_download(ho, "schemas/process_handoff.schema.json")
    _v98_validation_gate_ui("external systems codes handoff", ok, errs)
    st.download_button("Download process_handoff.json", data=_json.dumps(ho, indent=2, sort_keys=True),
                       file_name="process_handoff.json", mime="application/json", use_container_width=True, key="v98_dl_process_handoff")


# =====================
# v99 Session Report Export (append-only)
# =====================
def _v99_session_report_panel():
    import streamlit as st
    s = _v98_state_init_runlists()
    st.subheader("Session Report Export")
    st.caption("Exports a single zip: run ledger + pinned runs + diffs. Optional: include unified export bundle if built.")
    if not s.run_history:
        st.info("No runs recorded yet.")
        return

    include_bundle = st.checkbox("Include unified export bundle (if already built)", value=True, key="v99_inc_bundle")
    if st.button("Build session report zip", key="v99_build_report"):
        try:
            from tools.export.session_report import build_session_report_zip
            bundle = st.session_state.get("v94_bundle_bytes", None) if include_bundle else None
            b = build_session_report_zip(
                version=str(getattr(s, "version", None) or "v99"),
                run_history=list(s.run_history),
                pinned_ids=list(s.pinned_run_ids or []),
                unified_export_bundle_bytes=bundle if isinstance(bundle, (bytes, bytearray)) else None,
            )
            st.session_state["v99_session_report_zip"] = b
            st.success("Session report built.")
        except Exception as e:
            st.error(f"Failed to build session report: {e!r}")

    b = st.session_state.get("v99_session_report_zip", None)
    if isinstance(b, (bytes, bytearray)) and len(b) > 0:
        st.download_button(
            "Download shams_session_report.zip",
            data=b,
            file_name="shams_session_report.zip",
            mime="application/zip",
            use_container_width=True,
            key="v99_dl_report",
        )


# =====================
# v103 Audit Pack + Atlas + Sandbox Plus panels (append-only)
# =====================
def _v103_audit_pack_panel():
    import streamlit as st
    s = _v98_state_init_runlists()
    st.subheader("Audit Pack")
    st.caption("Single zip: selected artifacts + schemas + environment + manifest (journal/regulator-ready).")
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    picked = st.multiselect("Include runs", options=ids, default=list(s.pinned_run_ids or []), key="v103_audit_pick")
    include_pf = st.checkbox("Include pip freeze (best-effort)", value=True, key="v103_audit_pf")
    if st.button("Build audit pack zip", key="v103_build_audit"):
        try:
            from tools.audit_pack import build_audit_pack_zip
            run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
            arts = []
            for rid in picked:
                r = run_map.get(rid)
                if r and isinstance(r.get("payload"), dict):
                    arts.append(r["payload"])
            b = build_audit_pack_zip(version="v103", artifacts=arts, schema_dir="schemas", include_pip_freeze=include_pf)
            st.session_state["v103_audit_zip"] = b
            st.success("Audit pack built.")
        except Exception as e:
            st.error(f"Failed: {e!r}")
    b = st.session_state.get("v103_audit_zip")
    if isinstance(b, (bytes, bytearray)) and len(b) > 0:
        st.download_button("Download shams_audit_pack.zip", data=b, file_name="shams_audit_pack.zip", mime="application/zip", use_container_width=True, key="v103_dl_audit")

def _v103_atlas_panel():
    import streamlit as st
    st.subheader("Feasibility Boundary Atlas")
    st.caption("Deterministic nearest-feasible sweeps using SHAMS frontier search (audit-ready).")
    s = _v92_state_get()
    if not getattr(s, "last_point_inp", None):
        st.info("Run Point Designer first (uses last point inputs).")
        return
    base = s.last_point_inp
    # Default lever bounds (conservative, user-editable)
    levers = {
        "R0_m": (max(0.5, float(getattr(base, "R0_m", 2.0))*0.7), float(getattr(base, "R0_m", 2.0))*1.3),
        "a_m": (max(0.2, float(getattr(base, "a_m", 0.6))*0.7), float(getattr(base, "a_m", 0.6))*1.3),
        "Bt_T": (max(1.0, float(getattr(base, "Bt_T", 12.0))*0.7), float(getattr(base, "Bt_T", 12.0))*1.3),
        "Ip_MA": (max(0.1, float(getattr(base, "Ip_MA", 8.0))*0.7), float(getattr(base, "Ip_MA", 8.0))*1.3),
        "fG": (max(0.1, float(getattr(base, "fG", 0.8))*0.7), min(1.2, float(getattr(base, "fG", 0.8))*1.3)),
    }
    n_random = st.slider("Random samples", 20, 300, 80, 10, key="v103_atlas_n")
    seed = st.number_input("Seed", value=0, step=1, key="v103_atlas_seed")
    if st.button("Build Atlas", key="v103_build_atlas"):
        try:
            from tools.frontier_atlas import build_feasibility_atlas
            atlas = build_feasibility_atlas(base, levers=levers, targets=None, n_random=int(n_random), seed=int(seed), n_slices=5)
            st.session_state["v103_atlas"] = atlas
            _v98_record_run("atlas", atlas, mode="feasibility_atlas")
            st.success("Atlas built and recorded in Run Ledger.")
        except Exception as e:
            st.error(f"Atlas failed: {e!r}")
    atlas = st.session_state.get("v103_atlas")
    if isinstance(atlas, dict):
        st.write("Reports:", int(atlas.get("n_reports", 0)))
        st.download_button("Download feasibility_atlas.json", data=_json.dumps(atlas, indent=2, sort_keys=True),
                           file_name="feasibility_atlas.json", mime="application/json", use_container_width=True, key="v103_dl_atlas")

def _v103_sandbox_plus_panel():
    import streamlit as st
    st.subheader("Optimizer Sandbox Plus")
    st.caption("Safe orchestration layer: random/LHS exploration with feasibility-first behavior and full logs.")
    s = _v92_state_get()
    if not getattr(s, "last_point_inp", None):
        st.info("Run Point Designer first (uses last point inputs as baseline).")
        return
    base = s.last_point_inp
    strat = st.selectbox("Strategy", ["random", "lhs"], index=0, key="v103_sb_strat")
    obj = st.selectbox("Objective", ["min_R0", "min_Bpeak", "max_Pnet", "min_recirc"], index=0, key="v103_sb_obj")
    max_evals = st.slider("Max evals", 20, 1000, 200, 20, key="v103_sb_evals")
    seed = st.number_input("Seed", value=0, step=1, key="v103_sb_seed")
    levers = {
        "R0_m": (max(0.5, float(getattr(base, "R0_m", 2.0))*0.7), float(getattr(base, "R0_m", 2.0))*1.3),
        "a_m": (max(0.2, float(getattr(base, "a_m", 0.6))*0.7), float(getattr(base, "a_m", 0.6))*1.3),
        "Bt_T": (max(1.0, float(getattr(base, "Bt_T", 12.0))*0.7), float(getattr(base, "Bt_T", 12.0))*1.3),
        "Ip_MA": (max(0.1, float(getattr(base, "Ip_MA", 8.0))*0.7), float(getattr(base, "Ip_MA", 8.0))*1.3),
        "fG": (max(0.1, float(getattr(base, "fG", 0.8))*0.7), min(1.2, float(getattr(base, "fG", 0.8))*1.3)),
    }
    if st.button("Run Sandbox Plus", key="v103_run_sandbox_plus"):
        try:
            from tools.sandbox_plus import run_sandbox
            run = run_sandbox(base, levers=levers, objective=obj, max_evals=int(max_evals), seed=int(seed), strategy=strat)
            st.session_state["v103_sandbox_plus"] = run
            _v98_record_run("sandbox_plus", run, mode="optimizer_sandbox_plus")
            st.success("Sandbox run complete and recorded.")
        except Exception as e:
            st.error(f"Sandbox failed: {e!r}")
    run = st.session_state.get("v103_sandbox_plus")
    if isinstance(run, dict):
        st.download_button("Download sandbox_plus.json", data=_json.dumps(run, indent=2, sort_keys=True),
                           file_name="sandbox_plus.json", mime="application/json", use_container_width=True, key="v103_dl_sandbox_plus")


# =====================
# v104 Feasible Space Topology (append-only)
# =====================
def _v104_topology_panel():
    import streamlit as st
    from tools.topology import build_feasible_topology, extract_feasible_points_from_payload

    st.subheader("Feasible Space Topology")
    st.caption("Builds a connectivity graph of feasible designs (components = design 'islands').")

    s = _v98_state_init_runlists()
    if not s.run_history:
        st.info("No runs recorded yet.")
        return

    # pick source runs (default pinned)
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    default_ids = list(s.pinned_run_ids or [])
    picked = st.multiselect("Source runs", options=ids, default=default_ids, key="v104_topology_pick")
    eps = st.slider("Connectivity threshold (scaled distance)", 0.05, 0.50, 0.18, 0.01, key="v104_topology_eps")
    max_pts = st.slider("Max points (cap)", 50, 600, 300, 10, key="v104_topology_cap")

    if st.button("Build topology", key="v104_build_topology"):
        try:
            run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
            pts = []
            for rid in picked:
                payload = (run_map.get(rid) or {}).get("payload")
                if isinstance(payload, dict):
                    pts += extract_feasible_points_from_payload(payload)
            topo = build_feasible_topology(pts, eps=float(eps), max_points=int(max_pts))
            st.session_state["v104_topology"] = topo
            _v98_record_run("topology", topo, mode="feasible_topology")
            st.success(f"Topology built: {topo.get('n_points',0)} points, {len(topo.get('components',[]))} components.")
        except Exception as e:
            st.error(f"Topology build failed: {e!r}")

    topo = st.session_state.get("v104_topology")
    if isinstance(topo, dict):
        comps = topo.get("components", [])
        st.write({
            "points": int(topo.get("n_points", 0)),
            "edges": int(topo.get("n_edges", 0)),
            "components": int(len(comps) if isinstance(comps, list) else 0),
            "largest_component": int(len(comps[0]) if isinstance(comps, list) and comps else 0),
        })
        if isinstance(comps, list) and comps:
            st.write("Component sizes:", [len(c) for c in comps[:10]])
        st.download_button("Download feasible_topology.json",
                           data=_json.dumps(topo, indent=2, sort_keys=True),
                           file_name="feasible_topology.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v104_dl_topology")


# =====================
# v105 Constraint Dominance & Sensitivity (append-only)
# =====================
def _v105_constraint_dominance_panel():
    import streamlit as st
    from tools.constraint_dominance import build_constraint_dominance_report

    st.subheader("Constraint Dominance")
    st.caption("Ranks which constraints most strongly limit feasibility (failures + near-boundary).")

    s = _v98_state_init_runlists()
    if not s.run_history:
        st.info("No runs recorded yet.")
        return

    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    default_ids = list(s.pinned_run_ids or [])
    picked = st.multiselect("Source runs (run artifacts only)", options=ids, default=default_ids, key="v105_dom_pick")
    near = st.slider("Near-boundary threshold (margin_frac)", 0.00, 0.25, 0.05, 0.01, key="v105_dom_near")
    fail_w = st.slider("Failure weight", 1.0, 10.0, 4.0, 0.5, key="v105_dom_failw")

    if st.button("Build dominance report", key="v105_build_dom"):
        try:
            run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
            payloads = []
            for rid in picked:
                payload = (run_map.get(rid) or {}).get("payload")
                if isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact":
                    payloads.append(payload)
            rep = build_constraint_dominance_report(payloads, near_threshold=float(near), fail_weight=float(fail_w))
            st.session_state["v105_dom"] = rep
            _v98_record_run("dominance", rep, mode="constraint_dominance")
            st.success(f"Built dominance report for {rep.get('n_rows',0)} constraint rows.")
        except Exception as e:
            st.error(f"Dominance failed: {e!r}")

    rep = st.session_state.get("v105_dom")
    if isinstance(rep, dict):
        ranked = rep.get("constraints_ranked", [])
        if isinstance(ranked, list) and ranked:
            top = ranked[:8]
            st.write([{"name": r.get("name"), "score": r.get("dominance_score"), "fail_rate": r.get("fail_rate"), "near_rate": r.get("near_boundary_rate")} for r in top])
        st.download_button("Download constraint_dominance_report.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True),
                           file_name="constraint_dominance_report.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v105_dl_dom")


# =====================
# v106 Failure Mode Taxonomy (append-only)
# =====================
def _v106_failure_taxonomy_panel():
    import streamlit as st
    from tools.failure_taxonomy import build_failure_taxonomy_report

    st.subheader("Failure Mode Taxonomy")
    st.caption("Classifies infeasible run artifacts by dominant failing constraint and aggregates failure modes.")

    s = _v98_state_init_runlists()
    if not s.run_history:
        st.info("No runs recorded yet.")
        return

    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    default_ids = list(s.pinned_run_ids or [])
    picked = st.multiselect("Source runs (run artifacts only)", options=ids, default=default_ids, key="v106_fail_pick")

    if st.button("Build failure taxonomy", key="v106_build_fail"):
        try:
            run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
            payloads = []
            for rid in picked:
                payload = (run_map.get(rid) or {}).get("payload")
                if isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact":
                    payloads.append(payload)
            rep = build_failure_taxonomy_report(payloads)
            st.session_state["v106_fail"] = rep
            _v98_record_run("failures", rep, mode="failure_taxonomy")
            st.success(f"Built failure taxonomy for {rep.get('n_failures',0)} failing runs.")
        except Exception as e:
            st.error(f"Failure taxonomy failed: {e!r}")

    rep = st.session_state.get("v106_fail")
    if isinstance(rep, dict):
        st.write({"failures": rep.get("n_failures"), "modes": len(rep.get("counts_by_mode",{}))})
        top = list(rep.get("counts_by_mode", {}).items())[:10]
        if top:
            st.write([{"mode": k, "count": v} for k,v in top])
        st.download_button("Download failure_taxonomy_report.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True),
                           file_name="failure_taxonomy_report.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v106_dl_fail")


# =====================
# v107 Feasibility Science Pack (append-only)
# =====================
def _v107_science_pack_panel():
    import streamlit as st
    from tools.science_pack import build_feasibility_science_pack

    st.subheader("Feasibility Science Pack")
    st.caption("One-click export: topology + dominance + failures + publishable report + zip.")

    s = _v98_state_init_runlists()
    if not s.run_history:
        st.info("No runs recorded yet.")
        return

    # Pull latest artifacts from session state if present, else try to find from run history
    topo = st.session_state.get("v104_topology")
    dom = st.session_state.get("v105_dom")
    fail = st.session_state.get("v106_fail")

    # fallback: scan run history for latest by mode
    def _latest_by_mode(mode_name: str):
        for r in reversed(s.run_history or []):
            if (r.get("mode") == mode_name) and isinstance(r.get("payload"), dict):
                return r.get("payload")
        return None

    if topo is None:
        topo = _latest_by_mode("feasible_topology")
    if dom is None:
        dom = _latest_by_mode("constraint_dominance")
    if fail is None:
        fail = _latest_by_mode("failure_taxonomy")

    ready = isinstance(topo, dict) and isinstance(dom, dict) and isinstance(fail, dict)
    st.write({
        "topology_loaded": isinstance(topo, dict),
        "dominance_loaded": isinstance(dom, dict),
        "failures_loaded": isinstance(fail, dict),
        "ready": ready,
    })
    if not ready:
        st.info("Build topology, dominance, and failure taxonomy first.")
        return

    version = st.text_input("Pack version label", value="v107", key="v107_pack_version")
    if st.button("Build Feasibility Science Pack", key="v107_build_pack"):
        try:
            pack = build_feasibility_science_pack(
                topology=topo,
                dominance=dom,
                failures=fail,
                source_run_ids=list(s.pinned_run_ids or []),
                version=str(version),
            )
            st.session_state["v107_pack"] = pack
            # record summary only (zip bytes excluded from run ledger)
            _v98_record_run("science_pack", {"kind": "shams_feasibility_science_pack_summary", "summary": pack.get("summary")}, mode="feasibility_science_pack")
            st.success("Science pack built.")
        except Exception as e:
            st.error(f"Science pack failed: {e!r}")

    pack = st.session_state.get("v107_pack")
    if isinstance(pack, dict):
        st.write(pack.get("summary", {}))
        zip_bytes = pack.get("zip_bytes")
        if isinstance(zip_bytes, (bytes, bytearray)):
            st.download_button(
                "Download feasibility_science_pack.zip",
                data=bytes(zip_bytes),
                file_name="feasibility_science_pack.zip",
                mime="application/zip",
                use_container_width=True,
                key="v107_dl_pack_zip",
            )
        manifest = dict(pack)
        manifest.pop("zip_bytes", None)
        st.download_button(
            "Download science_pack_manifest.json",
            data=_json.dumps(manifest, indent=2, sort_keys=True),
            file_name="science_pack_manifest.json",
            mime="application/json",
            use_container_width=True,
            key="v107_dl_pack_manifest",
        )


# =====================
# v108 external systems codes Downstream Export (append-only)
# =====================
def _v108_process_downstream_panel():
    import streamlit as st
    from tools.process_downstream import build_process_downstream_bundle

    st.subheader("external systems codes Downstream Export")
    st.caption("Exports SHAMS run artifacts to a transparent (systems-code-inspired) table so external systems codes becomes downstream.")

    s = _v98_state_init_runlists()
    if not s.run_history:
        st.info("No runs recorded yet.")
        return

    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    default_ids = list(s.pinned_run_ids or [])
    picked = st.multiselect("Run artifacts to export", options=ids, default=default_ids, key="v108_proc_pick")
    version = st.text_input("Export version label", value="v108", key="v108_proc_version")

    if st.button("Build external systems codes downstream bundle", key="v108_proc_build"):
        try:
            run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
            payloads = []
            for rid in picked:
                payload = (run_map.get(rid) or {}).get("payload")
                if isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact":
                    payloads.append(payload)
            pack = build_process_downstream_bundle(payloads, version=str(version), source_run_ids=list(picked))
            st.session_state["v108_proc_pack"] = pack
            # record summary only
            _v98_record_run("process_downstream", {"kind":"shams_process_downstream_summary","summary":pack.get("summary")}, mode="process_downstream")
            st.success("external systems codes downstream bundle built.")
        except Exception as e:
            st.error(f"Export failed: {e!r}")

    pack = st.session_state.get("v108_proc_pack")
    if isinstance(pack, dict):
        st.write(pack.get("summary", {}))
        zip_bytes = pack.get("zip_bytes")
        if isinstance(zip_bytes, (bytes, bytearray)):
            st.download_button(
                "Download process_downstream_bundle.zip",
                data=bytes(zip_bytes),
                file_name="process_downstream_bundle.zip",
                mime="application/zip",
                use_container_width=True,
                key="v108_proc_dl_zip",
            )
        manifest = dict(pack)
        manifest.pop("zip_bytes", None)
        st.download_button(
            "Download process_downstream_manifest.json",
            data=_json.dumps(manifest, indent=2, sort_keys=True),
            file_name="process_downstream_manifest.json",
            mime="application/json",
            use_container_width=True,
            key="v108_proc_dl_manifest",
        )


# =====================
# v109 Island Inspector (append-only)
# =====================
def _v109_island_inspector_panel():
    import streamlit as st
    from tools.component_dominance import build_component_dominance_report

    st.subheader("Island Inspector")
    st.caption("Per-feasible-island dominance + boundary-near failure modes.")

    s = _v98_state_init_runlists()
    # Get topology + failure taxonomy from session/run ledger
    topo = st.session_state.get("v104_topology")
    dom = st.session_state.get("v105_dom")  # not required, but should exist for prior steps
    fail = st.session_state.get("v106_fail")

    def _latest_by_mode(mode_name: str):
        for r in reversed(s.run_history or []):
            if (r.get("mode") == mode_name) and isinstance(r.get("payload"), dict):
                return r.get("payload")
        return None

    if topo is None:
        topo = _latest_by_mode("feasible_topology")
    if fail is None:
        fail = _latest_by_mode("failure_taxonomy")

    st.write({"topology_loaded": isinstance(topo, dict), "failures_loaded": isinstance(fail, dict)})
    if not isinstance(topo, dict):
        st.info("Build topology first.")
        return

    # choose run artifacts to assign
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    default_ids = list(s.pinned_run_ids or [])
    picked = st.multiselect("Run artifacts to use (feasible ones define islands)", options=ids, default=default_ids, key="v109_pick_runs")
    near = st.slider("Near-boundary threshold (margin_frac)", 0.00, 0.25, 0.05, 0.01, key="v109_near")
    fail_w = st.slider("Failure weight", 1.0, 10.0, 4.0, 0.5, key="v109_failw")

    if st.button("Build component dominance report", key="v109_build"):
        try:
            run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
            payloads = []
            for rid in picked:
                payload = (run_map.get(rid) or {}).get("payload")
                if isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact":
                    payloads.append(payload)
            rep = build_component_dominance_report(topology=topo, run_artifacts=payloads, failure_taxonomy=fail, near_threshold=float(near), fail_weight=float(fail_w))
            st.session_state["v109_components"] = rep
            _v98_record_run("islands", rep, mode="component_dominance")
            st.success(f"Built component report for {rep.get('n_components',0)} components.")
        except Exception as e:
            st.error(f"v109 failed: {e!r}")

    rep = st.session_state.get("v109_components")
    if isinstance(rep, dict):
        comps = rep.get("components", [])
        if isinstance(comps, list) and comps:
            st.write("Top components (by size):")
            st.write([{
                "component": c.get("component_index"),
                "size_pts": c.get("component_size_points"),
                "runs": c.get("n_feasible_runs_assigned"),
                "top_constraint": (c.get("dominance_top_constraints") or [{}])[0].get("name") if isinstance(c.get("dominance_top_constraints"), list) and c.get("dominance_top_constraints") else None,
                "top_failure_mode": (c.get("top_failure_modes_near_component") or [{}])[0].get("mode") if isinstance(c.get("top_failure_modes_near_component"), list) and c.get("top_failure_modes_near_component") else None,
            } for c in comps[:12]])
        st.download_button("Download component_dominance_report.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True),
                           file_name="component_dominance_report.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v109_dl_report")


# =====================
# v110 Boundary Atlas v2 (append-only)
# =====================
def _v110_boundary_atlas_panel():
    import streamlit as st
    from tools.boundary_atlas_v2 import build_boundary_atlas_v2
    from tools.plot_boundary_atlas_v2 import main as _plot_cli  # not used directly

    st.subheader("Feasibility Boundary Atlas v2")
    st.caption("Extracts explicit feasible/infeasible boundaries for lever-pair slices, with failure-mode labels (best-effort).")

    s = _v98_state_init_runlists()
    topo = st.session_state.get("v104_topology")
    fail = st.session_state.get("v106_fail")

    def _latest_by_mode(mode_name: str):
        for r in reversed(s.run_history or []):
            if (r.get("mode") == mode_name) and isinstance(r.get("payload"), dict):
                return r.get("payload")
        return None

    if fail is None:
        fail = _latest_by_mode("failure_taxonomy")

    # Use pinned runs as sources; include atlas/sandbox/topology artifacts if present in history
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    default_ids = list(s.pinned_run_ids or [])
    picked = st.multiselect("Source run artifacts (infeasible + feasible)", options=ids, default=default_ids, key="v110_pick_runs")
    q = st.slider("Boundary proximity quantile (lower = tighter)", 0.05, 0.80, 0.25, 0.05, key="v110_q")
    maxpairs = st.slider("Max lever pairs", 1, 8, 6, 1, key="v110_maxpairs")

    if st.button("Build Boundary Atlas v2", key="v110_build"):
        try:
            run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
            payloads = []
            for rid in picked:
                payload = (run_map.get(rid) or {}).get("payload")
                if isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact":
                    payloads.append(payload)
            rep = build_boundary_atlas_v2(payloads, failure_taxonomy=fail, max_pairs=int(maxpairs), proximity_quantile=float(q))
            st.session_state["v110_boundary_atlas"] = rep
            _v98_record_run("atlas_v2", rep, mode="boundary_atlas_v2")
            st.success(f"Built atlas slices: {len(rep.get('slices', []))}")
        except Exception as e:
            st.error(f"v110 failed: {e!r}")

    rep = st.session_state.get("v110_boundary_atlas")
    if isinstance(rep, dict):
        st.write({"slices": len(rep.get("slices", [])), "lever_pairs": rep.get("lever_pairs")})
        st.download_button("Download boundary_atlas_v2.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True),
                           file_name="boundary_atlas_v2.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v110_dl_json")


# =====================
# v111 Design Family Explorer (append-only)
# =====================
def _v111_design_family_panel():
    import streamlit as st
    from tools.design_family import build_design_family_report

    st.subheader("Design Family Explorer")
    st.caption("Safe local exploration within a feasible island (no optimization).")

    s = _v98_state_init_runlists()
    topo = st.session_state.get("v104_topology")
    def _latest_by_mode(mode_name: str):
        for r in reversed(s.run_history or []):
            if (r.get("mode") == mode_name) and isinstance(r.get("payload"), dict):
                return r.get("payload")
        return None
    if topo is None:
        topo = _latest_by_mode("feasible_topology")

    if not isinstance(topo, dict):
        st.info("Build topology first.")
        return

    comps = topo.get("components", [])
    ncomp = len(comps) if isinstance(comps, list) else 0
    st.write({"n_components": ncomp})

    # choose baseline run (for full PointInputs)
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    default_id = (list(s.pinned_run_ids or [])[:1] or [ids[0] if ids else None])[0]
    baseline_id = st.selectbox("Baseline run artifact (provides full inputs)", options=[None] + ids, index=(1 if default_id in ids else 0), key="v111_base_id")
    comp_idx = st.number_input("Component index", min_value=0, max_value=max(0, ncomp-1), value=0, step=1, key="v111_comp_idx")
    n_samples = st.slider("Samples", 10, 240, 120, 10, key="v111_ns")
    radius = st.slider("Local radius (fraction of lever span)", 0.01, 0.25, 0.08, 0.01, key="v111_rad")
    seed = st.number_input("Seed", min_value=0, max_value=10_000_000, value=0, step=1, key="v111_seed")

    if st.button("Run Design Family Explorer", key="v111_run"):
        try:
            run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
            payload = (run_map.get(baseline_id) or {}).get("payload") if baseline_id else None
            if not (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact"):
                st.error("Baseline run artifact not found. Pin/select a valid run artifact first.")
                return
            base_inputs = payload.get("inputs", {})
            if not isinstance(base_inputs, dict):
                st.error("Baseline inputs invalid.")
                return

            rep = build_design_family_report(
                topology=topo,
                component_index=int(comp_idx),
                baseline_inputs=base_inputs,
                n_samples=int(n_samples),
                radius_frac=float(radius),
                seed=int(seed),
            )
            st.session_state["v111_family"] = rep
            _v98_record_run("design_family", rep, mode="design_family")
            st.success("Design family report built.")
        except Exception as e:
            st.error(f"v111 failed: {e!r}")

    rep = st.session_state.get("v111_family")
    if isinstance(rep, dict):
        st.write({
            "component_index": rep.get("component_index"),
            "n_samples": rep.get("n_samples"),
            "feasible_fraction": rep.get("feasible_fraction"),
            "top_worst_hard": (rep.get("worst_hard_ranked") or [{}])[0],
        })
        st.download_button("Download design_family_report.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True),
                           file_name="design_family_report.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v111_dl_json")


# =====================
# v112 Literature Overlay (append-only)
# =====================
def _v112_literature_overlay_panel():
    import streamlit as st
    from tools.literature_overlay import template_payload, validate_literature_points
    from tools.literature_overlay import extract_xy_points

    st.subheader("Literature Overlay")
    st.caption("Upload a JSON of reference points (ITER/ARC/SPARC/etc.) and overlay on Boundary Atlas slices. SHAMS ships only a template.")

    if "v112_overlay"not in st.session_state:
        st.session_state["v112_overlay"] = template_payload(version="v112")

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Download overlay template JSON",
            data=_json.dumps(template_payload(version="v112"), indent=2, sort_keys=True),
            file_name="literature_points_template.json",
            mime="application/json",
            use_container_width=True,
            key="v112_dl_template",
        )
    with c2:
        up = st.file_uploader("Upload literature_points.json", type=["json"], key="v112_upload")
        if up is not None:
            try:
                payload = _json.loads(up.getvalue().decode("utf-8"))
                errs = validate_literature_points(payload)
                st.session_state["v112_overlay"] = payload
                if errs:
                    st.warning(f"Loaded with warnings: {errs[:8]}")
                else:
                    st.success("Overlay loaded.")
            except Exception as e:
                st.error(f"Failed to parse JSON: {e!r}")

    overlay = st.session_state.get("v112_overlay")
    st.write({"n_points": len((overlay or {}).get("points", [])) if isinstance(overlay, dict) else None})

    atlas = st.session_state.get("v110_boundary_atlas")
    if isinstance(atlas, dict) and isinstance(overlay, dict):
        slices = atlas.get("slices", [])
        if isinstance(slices, list) and slices:
            st.write("Preview overlay-able slices (first 6):")
            prev = []
            for sl in slices[:6]:
                if not isinstance(sl, dict):
                    continue
                kx = sl.get("lever_x"); ky = sl.get("lever_y")
                if isinstance(kx, str) and isinstance(ky, str):
                    prev.append({"x": kx, "y": ky, "points_available": len(extract_xy_points(overlay, kx, ky))})
            st.write(prev)


# =====================
# v113 Design Decision Layer (append-only)
# =====================
def _v113_design_decision_panel():
    import streamlit as st
    from tools.design_decision_layer import build_design_candidates, build_design_decision_pack

    st.subheader("Design Decision Layer")
    st.caption("Build defensible design candidates + comparison table + exportable decision pack (no optimization).")

    s = _v98_state_init_runlists()

    topo = st.session_state.get("v104_topology")
    comp = st.session_state.get("v109_components")
    atlas = st.session_state.get("v110_boundary_atlas")
    fam = st.session_state.get("v111_family")
    overlay = st.session_state.get("v112_overlay")

    # pick candidate artifacts from pinned runs (feasible only)
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    default_ids = list(s.pinned_run_ids or [])
    picked = st.multiselect("Candidate source run artifacts (feasible ones)", options=ids, default=default_ids, key="v113_pick")
    maxc = st.slider("Max candidates", 1, 20, 12, 1, key="v113_maxc")

    if st.button("Build candidates + decision pack", key="v113_build"):
        try:
            run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
            artifacts = []
            for rid in picked:
                payload = (run_map.get(rid) or {}).get("payload")
                if isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact":
                    artifacts.append(payload)

            candidates = build_design_candidates(
                artifacts=artifacts,
                topology=topo if isinstance(topo, dict) else None,
                component_dominance=comp if isinstance(comp, dict) else None,
                boundary_atlas_v2=atlas if isinstance(atlas, dict) else None,
                design_family_report=fam if isinstance(fam, dict) else None,
                literature_overlay=overlay if isinstance(overlay, dict) else None,
                max_candidates=int(maxc),
            )
            pack = build_design_decision_pack(candidates=candidates, version="v113")
            st.session_state["v113_candidates"] = candidates
            st.session_state["v113_pack"] = pack
            _v98_record_run("design_decision_pack", {"candidates": candidates, "manifest": pack.get("manifest")}, mode="design_decision_pack")
            st.success(f"Built {len(candidates)} candidates.")
        except Exception as e:
            st.error(f"v113 failed: {e!r}")

    candidates = st.session_state.get("v113_candidates")
    pack = st.session_state.get("v113_pack")
    if isinstance(candidates, list) and candidates:
        st.write("Candidate preview (first 5):")
        st.write([{
            "id": c.get("source_artifact_id"),
            "component": c.get("component_index"),
            "worst": (c.get("feasibility") or {}).get("worst_hard"),
            "margin": (c.get("feasibility") or {}).get("worst_hard_margin_frac"),
            "family_feas": (c.get("robustness") or {}).get("family_feasible_fraction"),
        } for c in candidates[:5]])
        st.download_button("Download candidates.json",
                           data=_json.dumps({"candidates": candidates}, indent=2, sort_keys=True),
                           file_name="candidates.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v113_dl_candidates")

    if isinstance(pack, dict) and isinstance(pack.get("zip_bytes"), (bytes, bytearray)):
        st.download_button("Download design_decision_pack.zip",
                           data=pack["zip_bytes"],
                           file_name="design_decision_pack.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v113_dl_pack")


# =====================
# v114 Preference-Aware Decision Layer (append-only)
# =====================
def _v114_preference_panel():
    import streamlit as st
    from tools.preference_layer import template_preferences, annotate_candidates_with_preferences, pareto_sets_from_annotations
    from tools.design_decision_layer import build_design_decision_pack

    st.subheader("Preference-Aware Decision Layer")
    st.caption("Preference sliders annotate candidates (scores + Pareto sets). No optimization; no auto-selection.")

    # candidates from v113
    candidates = st.session_state.get("v113_candidates")
    if not (isinstance(candidates, list) and candidates):
        st.info("Build v113 candidates first (Design Decision Layer).")
        return

    if "v114_prefs"not in st.session_state:
        st.session_state["v114_prefs"] = template_preferences()

    prefs = st.session_state["v114_prefs"]
    weights = (prefs.get("weights") if isinstance(prefs, dict) else None)
    if not isinstance(weights, dict):
        weights = {}

    st.write("Weights (0 disables a metric).")
    c1, c2 = st.columns(2)
    with c1:
        weights["margin"] = st.slider("margin (worst constraint margin)", 0.0, 2.0, float(weights.get("margin", 1.0)), 0.1, key="v114_w_margin")
        weights["robustness"] = st.slider("robustness (family feasible fraction)", 0.0, 2.0, float(weights.get("robustness", 1.0)), 0.1, key="v114_w_rob")
        weights["boundary_clearance"] = st.slider("boundary clearance (2D proxy)", 0.0, 2.0, float(weights.get("boundary_clearance", 0.7)), 0.1, key="v114_w_bd")
    with c2:
        weights["compactness"] = st.slider("compactness (smaller R0)", 0.0, 2.0, float(weights.get("compactness", 0.3)), 0.1, key="v114_w_comp")
        weights["low_aux_power"] = st.slider("low aux power (smaller Paux)", 0.0, 2.0, float(weights.get("low_aux_power", 0.2)), 0.1, key="v114_w_paux")

    prefs["weights"] = weights
    st.session_state["v114_prefs"] = prefs

    metrics = st.multiselect("Pareto metrics (normalized)", options=["margin","robustness","boundary_clearance","compactness","low_aux_power"],
                             default=["margin","robustness","boundary_clearance"], key="v114_metrics")

    if st.button("Annotate + compute Pareto sets", key="v114_run"):
        try:
            ann = annotate_candidates_with_preferences(candidates, prefs)
            pareto = pareto_sets_from_annotations(ann, metrics=metrics, max_fronts=3)
            st.session_state["v114_ann"] = ann
            st.session_state["v114_pareto"] = pareto
            st.success("v114 annotations + Pareto computed.")
        except Exception as e:
            st.error(f"v114 failed: {e!r}")

    ann = st.session_state.get("v114_ann")
    pareto = st.session_state.get("v114_pareto")

    if isinstance(ann, dict):
        # show top composite scores (best-effort)
        cands = ann.get("candidates", [])
        preview = []
        if isinstance(cands, list):
            for c in cands:
                if not isinstance(c, dict):
                    continue
                pa = c.get("preference_annotation_v114", {})
                comp = pa.get("composite_score") if isinstance(pa, dict) else None
                preview.append({
                    "id": c.get("source_artifact_id"),
                    "composite_score": comp,
                    "worst": (c.get("feasibility") or {}).get("worst_hard"),
                    "margin": (c.get("feasibility") or {}).get("worst_hard_margin_frac"),
                })
            preview.sort(key=lambda r: (r.get("composite_score") is None, -(r.get("composite_score") or -1e9)))
        st.write("Preview (top 8 by composite score; annotation only):")
        st.write(preview[:8])

        st.download_button("Download preference_annotation_bundle.json",
                           data=_json.dumps(ann, indent=2, sort_keys=True),
                           file_name="preference_annotation_bundle_v114.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v114_dl_ann")

    if isinstance(pareto, dict):
        st.write({"pareto_metrics": pareto.get("metrics"), "n_points": pareto.get("n_points"), "front_sizes": [len(f) for f in (pareto.get("fronts") or []) if isinstance(f, list)]})
        st.download_button("Download pareto_sets.json",
                           data=_json.dumps(pareto, indent=2, sort_keys=True),
                           file_name="pareto_sets_v114.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v114_dl_pareto")

    if isinstance(ann, dict) and isinstance(pareto, dict):
        # build a justification + pack (adds decision_justification.json inside zip)
        justification = {
            "kind": "shams_decision_justification_v114",
            "created_utc": ann.get("created_utc"),
            "preferences": prefs,
            "pareto_sets": pareto,
            "n_candidates": len((ann.get("candidates") or [])) if isinstance(ann.get("candidates"), list) else None,
            "disclaimer": "Annotations only. No optimization. No auto-selected best design.",
        }
        pack = build_design_decision_pack(candidates=candidates, version="v114", decision_justification=justification)
        st.download_button("Download v114 design_decision_pack.zip (with justification)",
                           data=pack["zip_bytes"],
                           file_name="design_decision_pack_v114.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v114_dl_pack")


# =====================
# v115 External Optimizer Sandbox (append-only)
# =====================
def _v115_optimizer_sandbox_panel():
    import streamlit as st
    from tools.optimizer_interface import template_request, template_response, evaluate_optimizer_proposal, build_optimizer_import_pack

    st.subheader("External Optimizer Sandbox")
    st.caption("Import external optimizer proposals as *read-only* candidates. SHAMS re-evaluates physics+constraints and records a run artifact.")

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Download optimizer_request_template.json",
            data=_json.dumps(template_request(version="v115"), indent=2, sort_keys=True),
            file_name="optimizer_request_template.json",
            mime="application/json",
            use_container_width=True,
            key="v115_dl_req",
        )
    with c2:
        st.download_button(
            "Download optimizer_response_template.json",
            data=_json.dumps(template_response(version="v115"), indent=2, sort_keys=True),
            file_name="optimizer_response_template.json",
            mime="application/json",
            use_container_width=True,
            key="v115_dl_resp_tpl",
        )

    up = st.file_uploader("Upload optimizer_response.json (proposal)", type=["json"], key="v115_upload_resp")
    if up is None:
        st.info("Upload a proposal response to evaluate it inside SHAMS.")
        return

    try:
        payload = _json.loads(up.getvalue().decode("utf-8"))
    except Exception as e:
        st.error(f"Failed to parse JSON: {e!r}")
        return

    if payload.get("kind") != "shams_optimizer_response":
        st.error("JSON kind must be 'shams_optimizer_response'.")
        return

    if st.button("Evaluate proposal in SHAMS (frozen physics)", key="v115_eval"):
        try:
            out = evaluate_optimizer_proposal(payload)
            art = out["artifact"]
            ctx = out["context"]
            st.session_state["v115_last_artifact"] = art
            st.session_state["v115_last_context"] = ctx
            # record in ledger
            _v98_record_run("optimizer_proposal", {"artifact": art, "context": ctx}, mode="optimizer_import_v115")
            st.success("Proposal evaluated and recorded in Run Ledger.")
        except Exception as e:
            st.error(f"Evaluation failed: {e!r}")

    art = st.session_state.get("v115_last_artifact")
    ctx = st.session_state.get("v115_last_context")

    if isinstance(ctx, dict):
        st.write("Import context:")
        st.write({k: ctx.get(k) for k in ["result", "disclaimer"]})

    if isinstance(art, dict) and art.get("kind") == "shams_run_artifact":
        st.write("Evaluated artifact summary:")
        cs = art.get("constraints_summary", {})
        st.write({
            "id": art.get("id"),
            "feasible": (cs.get("feasible") if isinstance(cs, dict) else None),
            "worst_hard": (cs.get("worst_hard") if isinstance(cs, dict) else None),
            "worst_margin": (cs.get("worst_hard_margin_frac") if isinstance(cs, dict) else None),
        })
        st.download_button("Download evaluated_run_artifact.json",
                           data=_json.dumps(art, indent=2, sort_keys=True),
                           file_name="evaluated_run_artifact.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v115_dl_eval_art")

        pack = build_optimizer_import_pack(
            request_template=template_request(version="v115"),
            response_template=template_response(version="v115"),
            evaluated_artifact=art,
            import_context=ctx if isinstance(ctx, dict) else None,
            version="v115",
        )
        st.download_button("Download optimizer_import_pack.zip",
                           data=pack["zip_bytes"],
                           file_name="optimizer_import_pack.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v115_dl_pack")


# =====================
# v116 Design Handoff Pack (append-only)
# =====================
def _v116_handoff_pack_panel():
    import streamlit as st
    from tools.handoff_pack import build_handoff_pack

    st.subheader("Design Handoff Pack")
    st.caption("Export an engineering-ready handoff bundle for any run artifact (inputs YAML, constraints CSV, figures, manifest).")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("No runs in ledger yet. Run a point evaluation first.")
        return

    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Select run artifact", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v116_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    art = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None

    if art is None:
        st.error("Selected run does not contain a run artifact payload.")
        return

    if st.button("Build handoff pack", key="v116_build"):
        try:
            pack = build_handoff_pack(artifact=art, version="v116")
            st.session_state["v116_pack"] = pack
            _v98_record_run("handoff_pack", {"manifest": pack.get("manifest"), "source_artifact_id": art.get("id")}, mode="handoff_pack_v116")
            st.success("Handoff pack built.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    pack = st.session_state.get("v116_pack")
    if isinstance(pack, dict) and isinstance(pack.get("zip_bytes"), (bytes, bytearray)):
        st.download_button("Download handoff_pack.zip",
                           data=pack["zip_bytes"],
                           file_name=f"handoff_pack_{rid}.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v116_dl_pack")
        st.download_button("Download handoff manifest.json",
                           data=_json.dumps(pack.get("manifest", {}), indent=2, sort_keys=True),
                           file_name="handoff_pack_manifest.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v116_dl_manifest")


# =====================
# v117 Tolerance Envelope (append-only)
# =====================
def _v117_tolerance_envelope_panel():
    import streamlit as st
    from tools.tolerance_envelope import template_tolerance_spec, evaluate_tolerance_envelope, envelope_summary_csv

    st.subheader("Tolerance Envelope")
    st.caption("Deterministic tolerance envelope around a selected run artifact. No Monte Carlo, no optimization.")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("No runs in ledger yet. Run a point evaluation first.")
        return

    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Select baseline run artifact", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v117_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    art = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if art is None:
        st.error("Selected run does not contain a run artifact payload.")
        return

    if "v117_spec"not in st.session_state:
        st.session_state["v117_spec"] = template_tolerance_spec()

    spec = st.session_state["v117_spec"]
    tmap = spec.get("tolerances") if isinstance(spec, dict) else {}
    if not isinstance(tmap, dict):
        tmap = {}

    mode = st.selectbox("Tolerance mode", options=["relative","absolute"], index=0 if spec.get("mode","relative")=="relative"else 1, key="v117_mode")
    include_mid = st.checkbox("Include edge midpoints", value=bool(spec.get("include_edge_midpoints", True)), key="v117_mid")
    max_samples = st.number_input("Max samples", min_value=10, max_value=500, value=200, step=10, key="v117_max")

    st.write("Tolerances (per lever):")
    cols = st.columns(3)
    keys = ["Bt_T","Ip_MA","R0_m","a_m","fG","Ti_keV","Paux_MW","kappa"]
    for i,k in enumerate(keys):
        with cols[i % 3]:
            default = float(tmap.get(k, 0.0) or 0.0)
            tmap[k] = st.number_input(f"{k} tol", min_value=0.0, max_value=1e6, value=default, step=0.005 if mode=="relative"else 0.5, key=f"v117_tol_{k}")

    spec["mode"] = mode
    spec["include_edge_midpoints"] = include_mid
    spec["tolerances"] = tmap
    st.session_state["v117_spec"] = spec

    st.download_button("Download tolerance_spec.json",
                       data=_json.dumps(spec, indent=2, sort_keys=True),
                       file_name="tolerance_spec_v117.json",
                       mime="application/json",
                       use_container_width=True,
                       key="v117_dl_spec")

    if st.button("Run tolerance envelope", key="v117_run"):
        try:
            rep = evaluate_tolerance_envelope(baseline_artifact=art, tolerance_spec=spec, version="v117", max_samples=int(max_samples))
            st.session_state["v117_report"] = rep
            _v98_record_run("tolerance_envelope", {"summary": rep.get("summary"), "source_artifact_id": rid}, mode="tolerance_envelope_v117")
            st.success("Tolerance envelope computed.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    rep = st.session_state.get("v117_report")
    if isinstance(rep, dict) and rep.get("kind") == "shams_tolerance_envelope_report":
        st.write("Summary:")
        st.write(rep.get("summary", {}))
        st.download_button("Download tolerance_envelope_report.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True),
                           file_name="tolerance_envelope_report_v117.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v117_dl_report")
        st.download_button("Download tolerance_envelope_summary.csv",
                           data=envelope_summary_csv(rep),
                           file_name="tolerance_envelope_summary_v117.csv",
                           mime="text/csv",
                           use_container_width=True,
                           key="v117_dl_csv")


# =====================
# v118 Optimizer Downstream Workflow (append-only)
# =====================
def _v118_optimizer_downstream_panel():
    import streamlit as st
    from tools.optimizer_downstream import template_batch_response, evaluate_optimizer_batch, build_downstream_report_zip
    from tools.preference_layer import template_preferences
    from tools.tolerance_envelope import template_tolerance_spec

    st.subheader("Optimizer Downstream Workflow")
    st.caption("Upload a batch of optimizer proposals; SHAMS evaluates, filters feasible, runs tolerance envelopes, builds candidates, applies preferences+Pareto, and exports one bundle.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("Download optimizer_batch_template.json",
                           data=_json.dumps(template_batch_response(), indent=2, sort_keys=True),
                           file_name="optimizer_batch_template.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v118_dl_batch_tpl")
    with c2:
        st.download_button("Download preferences_template.json",
                           data=_json.dumps(template_preferences(), indent=2, sort_keys=True),
                           file_name="preferences_template.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v118_dl_prefs_tpl")
    with c3:
        st.download_button("Download tolerance_spec_template.json",
                           data=_json.dumps(template_tolerance_spec(), indent=2, sort_keys=True),
                           file_name="tolerance_spec_template.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v118_dl_tol_tpl")

    up = st.file_uploader("Upload optimizer_batch.json", type=["json"], key="v118_up_batch")
    if up is None:
        st.info("Upload a batch proposal JSON to run v118.")
        return

    try:
        batch = _json.loads(up.getvalue().decode("utf-8"))
    except Exception as e:
        st.error(f"Failed to parse JSON: {e!r}")
        return

    if batch.get("kind") != "shams_optimizer_batch_response":
        st.error("JSON kind must be 'shams_optimizer_batch_response'.")
        return

    max_env = st.number_input("Max envelope samples per feasible point", min_value=8, max_value=80, value=24, step=4, key="v118_max_env")
    max_cand = st.number_input("Max candidates", min_value=1, max_value=50, value=12, step=1, key="v118_max_cand")

    # Optional: use current v114 prefs if present, else template
    prefs = st.session_state.get("v114_prefs")
    if not isinstance(prefs, dict):
        prefs = template_preferences()
    spec = st.session_state.get("v117_spec")
    if not isinstance(spec, dict):
        spec = template_tolerance_spec()

    if st.button("Run v118 downstream report", key="v118_run"):
        try:
            out = evaluate_optimizer_batch(batch_payload=batch, tolerance_spec=spec, max_envelope_samples=int(max_env), max_candidates=int(max_cand), preferences=prefs)
            rep = out["report"]
            pack_bytes = out["decision_pack_zip_bytes"]
            st.session_state["v118_report"] = rep
            st.session_state["v118_pack_bytes"] = pack_bytes
            bundle = build_downstream_report_zip(report_obj=rep, decision_pack_zip_bytes=pack_bytes)
            st.session_state["v118_bundle"] = bundle
            _v98_record_run("optimizer_downstream", {"summary": rep.get("batch_meta"), "decision_pack_manifest": rep.get("decision_pack_manifest")}, mode="optimizer_downstream_v118")
            st.success("v118 downstream report built.")
        except Exception as e:
            st.error(f"v118 failed: {e!r}")

    rep = st.session_state.get("v118_report")
    bundle = st.session_state.get("v118_bundle")
    if isinstance(rep, dict):
        st.write("Batch meta:")
        st.write(rep.get("batch_meta", {}))
        st.write("Decision justification summary:")
        dj = rep.get("decision_justification", {}) if isinstance(rep.get("decision_justification"), dict) else {}
        st.write({k: dj.get(k) for k in ["n_proposals","n_feasible","n_candidates","n_envelopes"]})
        st.download_button("Download optimizer_downstream_report_v118.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True),
                           file_name="optimizer_downstream_report_v118.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v118_dl_report")

    pack_bytes = st.session_state.get("v118_pack_bytes")
    if isinstance(pack_bytes, (bytes, bytearray)):
        st.download_button("Download design_decision_pack_v118.zip",
                           data=pack_bytes,
                           file_name="design_decision_pack_v118.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v118_dl_pack")

    if isinstance(bundle, dict) and isinstance(bundle.get("zip_bytes"), (bytes, bytearray)):
        st.download_button("Download optimizer_downstream_bundle_v118.zip",
                           data=bundle["zip_bytes"],
                           file_name="optimizer_downstream_bundle_v118.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v118_dl_bundle")


# =====================
# v119 Authority Pack (append-only)
# =====================
def _v119_authority_pack_panel():
    import streamlit as st
    from tools.authority_pack import build_authority_pack

    st.subheader("Authority Pack")
    st.caption("Build a single publishable evidence bundle: version, patch notes, requirements freeze (best-effort), command log, methods appendix, and selected artifacts.")

    # try to find latest generated artifacts from self-test run folder if present in session state
    audit_zip = st.session_state.get("last_audit_pack_zip_bytes")
    downstream_zip = None
    handoff_zip = None

    # If users ran v118/v116 panels in-session, these may exist:
    bundle = st.session_state.get("v118_bundle")
    if isinstance(bundle, dict) and isinstance(bundle.get("zip_bytes"), (bytes, bytearray)):
        downstream_zip = bytes(bundle["zip_bytes"])
    hp = st.session_state.get("v116_pack")
    if isinstance(hp, dict) and isinstance(hp.get("zip_bytes"), (bytes, bytearray)):
        handoff_zip = bytes(hp["zip_bytes"])

    cmdlog = st.text_area("Command log (editable)", value="\n".join([
        "python -m tools.ui_self_test --outdir out_ui_self_test",
        "python -m tools.verify_package",
        "python -m tools.verify_figures",
        "python -m tools.tests.test_plot_layout",
        "python -m tools.regression_suite",
    ]), height=140, key="v119_cmdlog")

    if st.button("Build Authority Pack", key="v119_build"):
        try:
            pack = build_authority_pack(
                repo_root=".",
                version="v119",
                audit_pack_zip=audit_zip,
                downstream_bundle_zip=downstream_zip,
                handoff_pack_zip=handoff_zip,
                command_log=[l for l in cmdlog.splitlines() if l.strip()],
            )
            st.session_state["v119_pack"] = pack
            _v98_record_run("authority_pack", {"manifest": pack.get("manifest")}, mode="authority_pack_v119")
            st.success("Authority pack built.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    pack = st.session_state.get("v119_pack")
    if isinstance(pack, dict) and isinstance(pack.get("zip_bytes"), (bytes, bytearray)):
        st.download_button("Download authority_pack_v119.zip",
                           data=pack["zip_bytes"],
                           file_name="authority_pack_v119.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v119_dl_zip")
        st.download_button("Download authority manifest.json",
                           data=_json.dumps(pack.get("manifest", {}), indent=2, sort_keys=True),
                           file_name="authority_pack_manifest_v119.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v119_dl_manifest")


# =====================
# v120 Constitutional panels (append-only)
# =====================
def _v120_constitution_panel():
    import streamlit as st
    from tools.constitution import build_constitution_manifest
    from ui.layer_registry import get_layers

    st.subheader("Constitution & Layer Registry")
    st.caption("This panel exposes governance + architecture documents and a cryptographic integrity manifest (SHA256).")

    # Documents
    docs = [
        ("ARCHITECTURE.md", "Architecture (Constitution)"),
        ("GOVERNANCE.md", "Governance & Release Policy"),
        ("LAYER_MODEL.md", "Layer Model"),
        ("NON_OPTIMIZER_MANIFESTO.md", "Non-Optimizer Manifesto"),
        ("CITATION.cff", "Citation (CFF)"),
    ]
    for fn, label in docs:
        try:
            b = open(fn, "rb").read()
            st.download_button(f"Download {label}", data=b, file_name=fn, use_container_width=True, key=f"v120_dl_{fn}")
        except Exception:
            st.warning(f"Missing {fn}")

    st.write("Registered higher layers (UI-accessible):")
    st.table([{"layer": e.layer, "title": e.title, "description": e.description, "panel": e.panel_fn_name} for e in get_layers()])

    man = build_constitution_manifest(repo_root=".", version="v120")
    st.download_button("Download constitution_manifest.json",
                       data=_json.dumps(man, indent=2, sort_keys=True),
                       file_name="constitution_manifest_v120.json",
                       mime="application/json",
                       use_container_width=True,
                       key="v120_dl_manifest")
    st.write("Manifest preview:")
    st.json(man)

def _v120_mission_placeholder_panel():
    import streamlit as st
    st.subheader("Mission Context (v120 placeholder)")
    st.info("Mission contexts are schema-first and will be added as additive layer panels without changing physics.")

def _v120_explainability_placeholder_panel():
    import streamlit as st
    st.subheader("Explainability (v120 placeholder)")
    st.info("Explainability narratives will be added as additive post-processing panels consuming run artifacts.")



# =====================
# v121 Mission Context Layer (L3) - additive UI panel
# =====================
def _v121_mission_context_panel():
    import streamlit as st
    from tools.mission_context import list_builtin_missions, load_mission, apply_mission_overlays, mission_report_csv

    st.subheader("Mission Context")
    st.caption("Advisory mission overlay: evaluates alignment to mission targets and reports gaps. No physics/constraints are changed.")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("No runs in ledger yet. Run a point evaluation first.")
        return

    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Select baseline run artifact", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v121_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    art = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if art is None:
        st.error("Selected run does not contain a run artifact payload.")
        return

    missions = list_builtin_missions("missions")
    if not missions:
        st.error("No missions found in missions/ directory.")
        return

    mfile = st.selectbox("Mission", options=missions, index=0, key="v121_mission_file")
    mission = load_mission(str(Path("missions") / mfile))

    if st.button("Generate mission report", key="v121_run"):
        try:
            rep = apply_mission_overlays(run_artifact=art, mission=mission, version="v121")
            st.session_state["v121_mission_report"] = rep
            _v98_record_run("mission_context", {"mission": mission.get("name"), "gaps_n": len(rep.get("gaps", []))}, mode="mission_context_v121")
            st.success("Mission report generated.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    rep = st.session_state.get("v121_mission_report")
    if isinstance(rep, dict) and rep.get("kind") == "shams_mission_report":
        st.write("Alignment:")
        st.write(rep.get("alignment", {}))
        st.write("Gaps:")
        st.write(rep.get("gaps", []))
        st.download_button("Download mission_report.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True),
                           file_name=f"mission_report_{mission.get('name','mission')}_v121.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v121_dl_json")
        st.download_button("Download mission_gaps.csv",
                           data=mission_report_csv(rep),
                           file_name=f"mission_gaps_{mission.get('name','mission')}_v121.csv",
                           mime="text/csv",
                           use_container_width=True,
                           key="v121_dl_csv")


# =====================
# v122 Explainability Layer (L4) - additive UI panel
# =====================
def _v122_explainability_panel():
    import streamlit as st
    from tools.explainability import build_explainability_report

    st.subheader("Explainability")
    st.caption("Post-processing narrative: why a design fails/succeeds, limiting constraints, robustness and mission context (if available).")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("No runs in ledger yet. Run a point evaluation first.")
        return

    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Select baseline run artifact", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v122_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    art = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if art is None:
        st.error("Selected run does not contain a run artifact payload.")
        return

    # Optional inputs: use latest in-session mission report / envelope report if present
    mission_rep = st.session_state.get("v121_mission_report")
    env_rep = st.session_state.get("v117_report")

    use_mission = st.checkbox("Use latest in-session mission report (if available)", value=isinstance(mission_rep, dict), key="v122_use_mission")
    use_env = st.checkbox("Use latest in-session tolerance envelope (if available)", value=isinstance(env_rep, dict), key="v122_use_env")

    if st.button("Generate explainability report", key="v122_run"):
        try:
            rep = build_explainability_report(
                run_artifact=art,
                mission_report=mission_rep if use_mission else None,
                tolerance_envelope_report=env_rep if use_env else None,
                version="v122",
            )
            st.session_state["v122_explainability_report"] = rep
            _v98_record_run("explainability", {"summary": rep.get("summary")}, mode="explainability_v122")
            st.success("Explainability report generated.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    rep = st.session_state.get("v122_explainability_report")
    if isinstance(rep, dict) and rep.get("kind") == "shams_explainability_report":
        st.write("Summary:")
        st.write(rep.get("summary", {}))
        st.text_area("Narrative", value=rep.get("narrative",""), height=260, key="v122_narr_view")
        st.download_button("Download explainability_report.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True),
                           file_name="explainability_report_v122.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v122_dl_json")
        st.download_button("Download explainability_report.txt",
                           data=(rep.get("narrative","") or "").encode("utf-8"),
                           file_name="explainability_report_v122.txt",
                           mime="text/plain",
                           use_container_width=True,
                           key="v122_dl_txt")


# =====================
# v123 Evidence Graph + v123B Study Kit - additive UI panel
# =====================
def _v123_evidence_and_studykit_panel():
    import streamlit as st
    from tools.evidence_graph import build_evidence_graph, build_traceability_table, traceability_csv
    from tools.study_kit import build_study_kit_zip

    st.subheader("Evidence Graph & Design Study Kit (v123 / v123B)")
    st.caption("Build provenance graph + traceability table, and export a full publishable study kit zip (manifested with SHA256).")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("No runs in ledger yet. Run a point evaluation first.")
        return

    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Select baseline run artifact", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v123_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    art = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if art is None:
        st.error("Selected run does not contain a run artifact payload.")
        return

    # Optional context from session state
    mission_rep = st.session_state.get("v121_mission_report")
    env_rep = st.session_state.get("v117_report")
    expl_rep = st.session_state.get("v122_explainability_report")

    v118_bundle = st.session_state.get("v118_bundle")
    downstream_manifest = None
    downstream_zip = None
    if isinstance(v118_bundle, dict):
        downstream_manifest = v118_bundle.get("manifest")
        if isinstance(v118_bundle.get("zip_bytes"), (bytes, bytearray)):
            downstream_zip = bytes(v118_bundle["zip_bytes"])

    v119_pack = st.session_state.get("v119_pack")
    authority_manifest = None
    authority_zip = None
    if isinstance(v119_pack, dict):
        authority_manifest = v119_pack.get("manifest")
        if isinstance(v119_pack.get("zip_bytes"), (bytes, bytearray)):
            authority_zip = bytes(v119_pack["zip_bytes"])

    decision_manifest = None
    decision_zip = None
    pack_bytes = st.session_state.get("v118_pack_bytes")
    if isinstance(pack_bytes, (bytes, bytearray)):
        decision_zip = bytes(pack_bytes)
        # best-effort manifest from report if present
        rep = st.session_state.get("v118_report")
        if isinstance(rep, dict):
            decision_manifest = rep.get("decision_pack_manifest")

    use_mission = st.checkbox("Use latest in-session mission report", value=isinstance(mission_rep, dict), key="v123_use_mission")
    use_env = st.checkbox("Use latest in-session tolerance envelope", value=isinstance(env_rep, dict), key="v123_use_env")
    use_expl = st.checkbox("Use latest in-session explainability report", value=isinstance(expl_rep, dict), key="v123_use_expl")

    if st.button("Build evidence graph + traceability", key="v123_build_ev"):
        try:
            graph = build_evidence_graph(
                run_artifact=art,
                mission_report=mission_rep if use_mission else None,
                tolerance_envelope_report=env_rep if use_env else None,
                explainability_report=expl_rep if use_expl else None,
                decision_pack_manifest=decision_manifest,
                downstream_bundle_manifest=downstream_manifest,
                authority_pack_manifest=authority_manifest,
                version="v123",
            )
            tab = build_traceability_table(
                run_artifact=art,
                mission_report=mission_rep if use_mission else None,
                tolerance_envelope_report=env_rep if use_env else None,
                explainability_report=expl_rep if use_expl else None,
                version="v123",
            )
            st.session_state["v123_graph"] = graph
            st.session_state["v123_trace_table"] = tab
            _v98_record_run("evidence_graph", {"nodes": len(graph.get("nodes",[])), "edges": len(graph.get("edges",[]))}, mode="evidence_graph_v123")
            st.success("Evidence graph and traceability built.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    graph = st.session_state.get("v123_graph")
    tab = st.session_state.get("v123_trace_table")
    if isinstance(graph, dict) and graph.get("kind") == "shams_evidence_graph":
        st.download_button("Download evidence_graph.json", data=_json.dumps(graph, indent=2, sort_keys=True),
                           file_name="evidence_graph_v123.json", mime="application/json", use_container_width=True, key="v123_dl_graph")
        st.json({"nodes": len(graph.get("nodes",[])), "edges": len(graph.get("edges",[]))})

    if isinstance(tab, dict) and tab.get("kind") == "shams_traceability_table":
        st.download_button("Download traceability_table.json", data=_json.dumps(tab, indent=2, sort_keys=True),
                           file_name="traceability_table_v123.json", mime="application/json", use_container_width=True, key="v123_dl_tab")
        st.download_button("Download traceability.csv", data=traceability_csv(tab),
                           file_name="traceability_v123.csv", mime="text/csv", use_container_width=True, key="v123_dl_csv")
        st.write("Traceability rows:", len(tab.get("rows",[])))

    st.divider()
    st.write("Design Study Kit export (v123B): bundles run artifact + optional context + evidence graph + manifest.")
    if st.button("Build study kit zip", key="v123_build_kit"):
        try:
            if not (isinstance(graph, dict) and isinstance(tab, dict)):
                graph = build_evidence_graph(run_artifact=art, mission_report=mission_rep if use_mission else None,
                                             tolerance_envelope_report=env_rep if use_env else None,
                                             explainability_report=expl_rep if use_expl else None,
                                             decision_pack_manifest=decision_manifest,
                                             downstream_bundle_manifest=downstream_manifest,
                                             authority_pack_manifest=authority_manifest,
                                             version="v123")
                tab = build_traceability_table(run_artifact=art, mission_report=mission_rep if use_mission else None,
                                               tolerance_envelope_report=env_rep if use_env else None,
                                               explainability_report=expl_rep if use_expl else None,
                                               version="v123")
                st.session_state["v123_graph"] = graph
                st.session_state["v123_trace_table"] = tab

            kit = build_study_kit_zip(
                run_artifact=art,
                mission_report=mission_rep if use_mission else None,
                tolerance_envelope_report=env_rep if use_env else None,
                explainability_report=expl_rep if use_expl else None,
                evidence_graph=graph,
                traceability_table=tab,
                authority_pack_zip=authority_zip,
                optimizer_downstream_bundle_zip=downstream_zip,
                decision_pack_zip=decision_zip,
                version="v123B",
            )
            st.session_state["v123_study_kit"] = kit
            _v98_record_run("study_kit", {"files": len((kit.get("manifest") or {}).get("files", {}))}, mode="study_kit_v123B")
            st.success("Study kit built.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    kit = st.session_state.get("v123_study_kit")
    if isinstance(kit, dict) and isinstance(kit.get("zip_bytes"), (bytes, bytearray)):
        st.download_button("Download study_kit_v123B.zip",
                           data=kit["zip_bytes"], file_name="study_kit_v123B.zip",
                           mime="application/zip", use_container_width=True, key="v123_dl_kit")
        st.download_button("Download study_kit_manifest_v123B.json",
                           data=_json.dumps(kit.get("manifest", {}), indent=2, sort_keys=True),
                           file_name="study_kit_manifest_v123B.json", mime="application/json",
                           use_container_width=True, key="v123_dl_kitman")


# =====================
# v124 Feasibility Boundary Atlas - additive UI panel
# =====================
def _v124_feasibility_atlas_panel():
    import streamlit as st
    from tools.feasibility_atlas import build_feasibility_atlas_bundle, available_numeric_levers

    st.subheader("Feasibility Boundary Atlas")
    st.caption("Runs a 2D grid scan around a baseline run, extracts feasibility boundary, and exports a publishable atlas bundle. Additive only (no physics/solver changes).")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("No runs in ledger yet. Run a point evaluation first.")
        return

    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Select baseline run artifact", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v124_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    base = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if base is None:
        st.error("Selected run does not contain a run artifact payload.")
        return

    base_inputs = base.get("inputs", {}) if isinstance(base.get("inputs"), dict) else {}
    levers = available_numeric_levers(base_inputs)
    if len(levers) < 2:
        st.error("Baseline inputs do not contain enough numeric levers for an atlas.")
        return

    col1, col2 = st.columns(2)
    with col1:
        kx = st.selectbox("Lever X", options=levers, index=0, key="v124_kx")
    with col2:
        ky = st.selectbox("Lever Y", options=levers, index=1 if len(levers)>1 else 0, key="v124_ky")

    def _default_range(v):
        try:
            v=float(v)
        except Exception:
            return (0.0, 1.0)
        if abs(v) < 1e-9:
            return (-1.0, 1.0)
        # ±20% around baseline
        return (v*0.8, v*1.2)

    x0 = base_inputs.get(kx)
    y0 = base_inputs.get(ky)
    xlo_def, xhi_def = _default_range(x0)
    ylo_def, yhi_def = _default_range(y0)

    st.write("Ranges (default ±20% around baseline):")
    r1, r2 = st.columns(2)
    with r1:
        xlo = st.number_input("X min", value=float(xlo_def), key="v124_xlo")
        xhi = st.number_input("X max", value=float(xhi_def), key="v124_xhi")
    with r2:
        ylo = st.number_input("Y min", value=float(ylo_def), key="v124_ylo")
        yhi = st.number_input("Y max", value=float(yhi_def), key="v124_yhi")

    c1, c2 = st.columns(2)
    with c1:
        nx = st.slider("Grid NX", min_value=9, max_value=61, value=25, step=2, key="v124_nx")
    with c2:
        ny = st.slider("Grid NY", min_value=9, max_value=61, value=25, step=2, key="v124_ny")

    max_evals = int(nx) * int(ny)
    st.caption(f"Total evaluations: {max_evals} (pure point evaluations + constraints).")

    if st.button("Generate atlas bundle", key="v124_run"):
        try:
            outdir = "out_feasibility_atlas_v124"
            bundle = build_feasibility_atlas_bundle(
                baseline_run_artifact=base,
                lever_x=kx,
                lever_y=ky,
                x_range=(float(xlo), float(xhi)),
                y_range=(float(ylo), float(yhi)),
                nx=int(nx),
                ny=int(ny),
                outdir=outdir,
                version="v124",
            )
            st.session_state["v124_bundle"] = bundle
            _v98_record_run("feasibility_atlas", {"lever_x": kx, "lever_y": ky, "nx": int(nx), "ny": int(ny)}, mode="feasibility_atlas_v124")
            st.success("Atlas generated.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    bundle = st.session_state.get("v124_bundle")
    if isinstance(bundle, dict) and isinstance(bundle.get("zip_bytes"), (bytes, bytearray)):
        st.download_button("Download atlas_bundle_v124.zip",
                           data=bundle["zip_bytes"],
                           file_name="atlas_bundle_v124.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v124_dl_zip")
        st.download_button("Download feasibility_atlas_v124.json",
                           data=_json.dumps(bundle, indent=2, sort_keys=True),
                           file_name="feasibility_atlas_v124.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v124_dl_json")
        st.write("Atlas summary:")
        st.json({"baseline_run_id": bundle.get("baseline_run_id"),
                 "lever_x": bundle.get("lever_x"), "lever_y": bundle.get("lever_y"),
                 "grid": bundle.get("grid"),
                 "n_slices": len((bundle.get("atlas_v2") or {}).get("slices", [])) if isinstance(bundle.get("atlas_v2"), dict) else None})


# =====================
# v125 One-Click Paper Pack - additive UI panel
# =====================
def _v125_paper_pack_panel():
    import streamlit as st
    from tools.mission_context import load_mission, apply_mission_overlays
    from tools.explainability import build_explainability_report
    from tools.evidence_graph import build_evidence_graph, build_traceability_table, traceability_csv
    from tools.feasibility_atlas import build_feasibility_atlas_bundle, available_numeric_levers
    from tools.study_kit import build_study_kit_zip
    from tools.study_orchestrator import build_paper_pack_zip

    st.subheader("One-Click Paper Pack")
    st.caption("Runs post-processing pipeline (mission → explainability → evidence/traceability → atlas → study kit) and exports a single publishable zip + manifest. No physics/solver changes.")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("No runs in ledger yet. Run a point evaluation first.")
        return

    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Select baseline run artifact", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v125_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    base = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if base is None:
        st.error("Selected run does not contain a run artifact payload.")
        return

    st.write("Pipeline options:")
    c1,c2,c3 = st.columns(3)
    with c1:
        do_mission = st.checkbox("Mission overlay", value=True, key="v125_do_mission")
        do_expl = st.checkbox("Explainability", value=True, key="v125_do_expl")
    with c2:
        do_ev = st.checkbox("Evidence+Traceability (v123)", value=True, key="v125_do_ev")
        do_atlas = st.checkbox("Feasibility Atlas (v124)", value=False, key="v125_do_atlas")
    with c3:
        do_kit = st.checkbox("Study Kit (v123B)", value=True, key="v125_do_kit")

    mission_name = None
    mission_rep = None
    if do_mission:
        missions = ["pilot","demo","powerplant"]
        msel = st.selectbox("Mission", options=missions, index=0, key="v125_mission")
        mission_name = msel

    atlas_cfg = None
    if do_atlas:
        base_inputs = base.get("inputs", {}) if isinstance(base.get("inputs"), dict) else {}
        levers = available_numeric_levers(base_inputs)
        if len(levers) >= 2:
            kx = st.selectbox("Atlas lever X", options=levers, index=0, key="v125_kx")
            ky = st.selectbox("Atlas lever Y", options=levers, index=1, key="v125_ky")

            def _default_range(v):
                try: v=float(v)
                except Exception: return (0.0, 1.0)
                if abs(v) < 1e-9: return (-1.0, 1.0)
                return (v*0.9, v*1.1)  # narrower defaults for v125
            x0 = base_inputs.get(kx); y0 = base_inputs.get(ky)
            xlo_def,xhi_def=_default_range(x0); ylo_def,yhi_def=_default_range(y0)
            r1,r2=st.columns(2)
            with r1:
                xlo = st.number_input("X min", value=float(xlo_def), key="v125_xlo")
                xhi = st.number_input("X max", value=float(xhi_def), key="v125_xhi")
            with r2:
                ylo = st.number_input("Y min", value=float(ylo_def), key="v125_ylo")
                yhi = st.number_input("Y max", value=float(yhi_def), key="v125_yhi")
            nx = st.slider("Atlas NX", min_value=9, max_value=41, value=15, step=2, key="v125_nx")
            ny = st.slider("Atlas NY", min_value=9, max_value=41, value=15, step=2, key="v125_ny")
            atlas_cfg = {"lever_x": kx, "lever_y": ky, "x_range": (float(xlo), float(xhi)), "y_range": (float(ylo), float(yhi)), "nx": int(nx), "ny": int(ny)}
        else:
            st.warning("Not enough numeric inputs to run atlas from this baseline.")
            do_atlas = False

    if st.button("Build Paper Pack", key="v125_run"):
        try:
            # Mission report (post-processing)
            if do_mission and mission_name:
                mspec = load_mission(mission_name)
                # apply overlay to baseline; function returns report dict
                mission_rep = apply_mission_overlays(run_artifact=base, mission=mspec, version="v121")
                st.session_state["v121_mission_report"] = mission_rep
            else:
                mission_rep = None

            # Explainability
            expl_rep = None
            if do_expl:
                env_rep = st.session_state.get("v117_report")  # optional
                expl_rep = build_explainability_report(run_artifact=base, mission_report=mission_rep, tolerance_envelope_report=env_rep if isinstance(env_rep, dict) else None, version="v122")
                st.session_state["v122_explainability_report"] = expl_rep

            # Evidence + traceability
            graph = None
            tab = None
            tcsv = None
            if do_ev:
                env_rep = st.session_state.get("v117_report")
                graph = build_evidence_graph(run_artifact=base, mission_report=mission_rep, tolerance_envelope_report=env_rep if isinstance(env_rep, dict) else None, explainability_report=expl_rep, version="v123")
                tab = build_traceability_table(run_artifact=base, mission_report=mission_rep, tolerance_envelope_report=env_rep if isinstance(env_rep, dict) else None, explainability_report=expl_rep, version="v123")
                tcsv = traceability_csv(tab)
                st.session_state["v123_graph"] = graph
                st.session_state["v123_trace_table"] = tab

            # Atlas
            atlas_meta = None
            atlas_zip = None
            if do_atlas and atlas_cfg:
                bundle = build_feasibility_atlas_bundle(
                    baseline_run_artifact=base,
                    lever_x=atlas_cfg["lever_x"],
                    lever_y=atlas_cfg["lever_y"],
                    x_range=atlas_cfg["x_range"],
                    y_range=atlas_cfg["y_range"],
                    nx=atlas_cfg["nx"],
                    ny=atlas_cfg["ny"],
                    outdir="out_feasibility_atlas_v125",
                    version="v124",
                )
                atlas_zip = bundle.get("zip_bytes")
                atlas_meta = dict(bundle)
                atlas_meta.pop("zip_bytes", None)
                st.session_state["v124_bundle"] = bundle

            # Study kit
            kit_zip = None
            if do_kit:
                kit = build_study_kit_zip(
                    run_artifact=base,
                    mission_report=mission_rep,
                    tolerance_envelope_report=st.session_state.get("v117_report") if isinstance(st.session_state.get("v117_report"), dict) else None,
                    explainability_report=expl_rep,
                    evidence_graph=graph,
                    traceability_table=tab,
                    authority_pack_zip=(st.session_state.get("v119_pack") or {}).get("zip_bytes") if isinstance(st.session_state.get("v119_pack"), dict) else None,
                    optimizer_downstream_bundle_zip=(st.session_state.get("v118_bundle") or {}).get("zip_bytes") if isinstance(st.session_state.get("v118_bundle"), dict) else None,
                    decision_pack_zip=st.session_state.get("v118_pack_bytes") if isinstance(st.session_state.get("v118_pack_bytes"), (bytes, bytearray)) else None,
                    version="v123B",
                )
                kit_zip = kit.get("zip_bytes")
                st.session_state["v123_study_kit"] = kit

            # Final pack
            pack = build_paper_pack_zip(
                baseline_run_artifact=base,
                mission_report=mission_rep,
                explainability_report=expl_rep,
                evidence_graph=graph,
                traceability_table=tab,
                traceability_csv=tcsv,
                feasibility_atlas_meta=atlas_meta,
                atlas_bundle_zip=atlas_zip,
                study_kit_zip=kit_zip,
                version="v125",
            )
            st.session_state["v125_paper_pack"] = pack
            _v98_record_run("paper_pack", {"files": len((pack.get("manifest") or {}).get("files", {}))}, mode="paper_pack_v125")
            st.success("Paper pack built.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    pack = st.session_state.get("v125_paper_pack")
    if isinstance(pack, dict) and isinstance(pack.get("zip_bytes"), (bytes, bytearray)):
        st.download_button("Download paper_pack_v125.zip",
                           data=pack["zip_bytes"],
                           file_name="paper_pack_v125.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v125_dl_zip")
        st.download_button("Download paper_pack_manifest_v125.json",
                           data=_json.dumps(pack.get("manifest", {}), indent=2, sort_keys=True),
                           file_name="paper_pack_manifest_v125.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v125_dl_manifest")
        st.write("Pack summary:")
        st.json({"files": len((pack.get("manifest") or {}).get("files", {})),
                 "created_utc": pack.get("created_utc")})


# =====================
# v126 UI Smoke & Diagnostics - additive UI panel
# =====================
def _v126_ui_smoke_panel():
    import streamlit as st
    from pathlib import Path as _Path

    st.subheader("UI Smoke & Diagnostics")
    st.caption("Runs lightweight UI smoke checks and produces a report. This does not change physics/solvers.")

    scenarios = st.multiselect("Scenarios", options=["render_all", "paper_pack"], default=["render_all"], key="v126_scenarios")
    outdir = st.text_input("Output directory", value="out_ui_smoke_v126", key="v126_outdir")

    if st.button("Run UI smoke checks", key="v126_run"):
        try:
            cmd = [_sys.executable, "-m", "tools.cli_ui_smoke", "--outdir", outdir] + [ "--scenarios"] + list(scenarios)
            # note: argparse expects --scenarios then list; we pass that
            p = _subprocess.run(cmd, cwd=str(_Path(__file__).resolve().parents[1]), stdout=_subprocess.PIPE, stderr=_subprocess.STDOUT, text=True, timeout=300)
            st.text_area("Runner output", value=p.stdout, height=180, key="v126_out")
            rep_path = _Path(__file__).resolve().parents[1] / outdir / "ui_smoke_report.json"
            if rep_path.exists():
                rep = _json.loads(rep_path.read_text(encoding="utf-8"))
                st.session_state["v126_smoke_report"] = rep
                st.success("Smoke report generated.")
            else:
                st.warning("Report file not found after run.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    rep = st.session_state.get("v126_smoke_report")
    if isinstance(rep, dict):
        st.write("Summary:")
        st.json(rep.get("summary", {}))
        st.download_button("Download ui_smoke_report.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True),
                           file_name="ui_smoke_report_v126.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v126_dl_json")


# =====================
# v127 Study Matrix - Batch Paper Packs (single UI)
# =====================
def _v127_study_matrix_panel():
    import streamlit as st
    from tools.study_matrix import build_cases_1d_sweep, build_study_matrix_bundle
    from tools.feasibility_atlas import available_numeric_levers

    st.subheader("Study Matrix + Batch Paper Packs")
    st.caption("Build multiple cases from a baseline and export a single study zip with per-case paper packs + index. Additive; no solver behavior changes.")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("No runs in ledger yet. Run a point evaluation first.")
        return

    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Select baseline run artifact", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v127_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    base = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if base is None:
        st.error("Selected run does not contain a run artifact payload.")
        return

    base_inputs = base.get("inputs", {}) if isinstance(base.get("inputs"), dict) else {}
    levers = available_numeric_levers(base_inputs)
    if not levers:
        st.warning("No numeric levers detected in baseline inputs.")
        return

    st.write("1D sweep builder (safe defaults):")
    c1,c2,c3 = st.columns(3)
    with c1:
        lever = st.selectbox("Sweep lever", options=levers, index=0, key="v127_lever")
    with c2:
        v0 = float(base_inputs.get(lever, 0.0) or 0.0)
        vmin = st.number_input("Min", value=(v0*0.95 if abs>1e-9 else -1.0), key="v127_vmin")
        vmax = st.number_input("Max", value=(v0*1.05 if abs>1e-9 else 1.0), key="v127_vmax")
    with c3:
        n = st.slider("N cases", min_value=3, max_value=15, value=5, step=1, key="v127_n")

    missions = st.multiselect("Missions (optional)", options=["pilot","demo","powerplant"], default=["pilot"], key="v127_missions")
    include_expl = st.checkbox("Include explainability (v122)", value=True, key="v127_expl")
    include_ev = st.checkbox("Include evidence/traceability (v123)", value=True, key="v127_ev")
    include_kit = st.checkbox("Include study kit (v123B)", value=True, key="v127_kit")

    if st.button("Build Study Matrix Zip", key="v127_run"):
        try:
            if int(n) < 2:
                raise ValueError("N must be >= 2")
            # linspace
            vals = [float(vmin) + (float(vmax)-float(vmin))*i/(int(n)-1) for i in range(int(n))]
            cases = build_cases_1d_sweep(baseline_run_artifact=base, lever=str(lever), values=vals, missions=(missions or None))
            bundle = build_study_matrix_bundle(
                baseline_run_artifact=base,
                cases=cases,
                outdir="out_study_matrix_v127",
                version="v127",
                include_explainability=bool(include_expl),
                include_evidence=bool(include_ev),
                include_study_kit=bool(include_kit),
            )
            st.session_state["v127_bundle"] = bundle
            _v98_record_run("study_matrix", {"cases": bundle.get("cases")}, mode="study_matrix_v127")
            st.success(f"Study matrix built: {bundle.get('cases')} cases.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    bun = st.session_state.get("v127_bundle")
    if isinstance(bun, dict) and isinstance(bun.get("zip_bytes"), (bytes, bytearray)):
        st.download_button("Download study_matrix_v127.zip",
                           data=bun["zip_bytes"],
                           file_name="study_matrix_v127.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v127_dl_zip")
        st.download_button("Download study_matrix_manifest_v127.json",
                           data=_json.dumps(bun.get("manifest", {}), indent=2, sort_keys=True),
                           file_name="study_matrix_manifest_v127.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v127_dl_manifest")
        st.json({"cases": bun.get("cases"), "created_utc": bun.get("created_utc")})


# =====================
# v128 Study Explorer + Comparator (single UI)
# =====================
def _v128_study_explorer_panel():
    import streamlit as st
    from tools.study_explorer import load_study_zip, parse_study_index, filter_cases, load_case_run_artifact, compare_two_runs

    st.subheader("Study Explorer + Comparator")
    st.caption("Load a study_matrix zip and browse/filter cases, compare two cases, and export comparison JSON. Downstream-only.")

    up = st.file_uploader("Upload study_matrix zip", type=["zip"], key="v128_upl")
    if not up:
        st.info("Upload a v127 study_matrix zip (study_matrix_v127.zip).")
        return

    try:
        # write to temp bytes map
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp.write(up.getvalue()); tmp.flush(); tmp.close()
        files = load_study_zip(tmp.name)
        idx = parse_study_index(files)
        st.session_state["v128_files"] = files
        st.session_state["v128_index"] = {"created_utc": idx.created_utc, "rows": idx.rows}
        os.unlink(tmp.name)
    except Exception as e:
        st.error(f"Failed to load: {e!r}")
        return

    idxd = st.session_state.get("v128_index") or {}
    rows = list(idxd.get("rows") or [])
    if not rows:
        st.warning("No rows found in study index.")
        return

    missions = sorted({str(r.get("mission","")) for r in rows if str(r.get("mission",""))})
    feasible_only = st.checkbox("Feasible only", value=False, key="v128_feas")
    mission = st.selectbox("Mission filter", options=["(any)"] + missions, index=0, key="v128_msel")

    # simple KPI filters
    kf = {}
    with st.expander("KPI filters (optional)"):
        c1,c2,c3 = st.columns(3)
        with c1:
            qlo = st.number_input("Q min", value=0.0, key="v128_qlo")
            kf["Q"] = (float(qlo), None)
        with c2:
            pnlo = st.number_input("Pnet_MW min", value=-1e9, key="v128_pnlo")
            kf["Pnet_MW"] = (float(pnlo), None)
        with c3:
            pflo = st.number_input("Pfus_MW min", value=0.0, key="v128_pflo")
            kf["Pfus_MW"] = (float(pflo), None)

    idx_obj = parse_study_index(st.session_state["v128_files"])
    fr = filter_cases(idx_obj, feasible_only=feasible_only, mission=None if mission=="(any)"else mission, kpi_filters=kf)

    st.write(f"Filtered cases: {len(fr)} / {len(rows)}")
    show = fr[:200]  # avoid UI overload
    st.dataframe(show, use_container_width=True)

    case_ids = [str(r.get("case_id")) for r in fr if r.get("case_id") is not None]
    if len(case_ids) < 2:
        st.info("Need at least 2 filtered cases to compare.")
        return

    a_id = st.selectbox("Case A", options=case_ids, index=0, key="v128_a")
    b_id = st.selectbox("Case B", options=case_ids, index=1 if len(case_ids)>1 else 0, key="v128_b")

    if st.button("Compare", key="v128_compare"):
        try:
            files = st.session_state["v128_files"]
            a_row = next(r for r in fr if str(r.get("case_id"))==a_id)
            b_row = next(r for r in fr if str(r.get("case_id"))==b_id)
            a_art = load_case_run_artifact(files, a_row)
            b_art = load_case_run_artifact(files, b_row)
            comp = compare_two_runs(a_art, b_art)
            st.session_state["v128_comp"] = comp
            st.success("Comparison built.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    comp = st.session_state.get("v128_comp")
    if isinstance(comp, dict):
        st.write("Comparison summary:")
        st.json(comp)
        st.download_button("Download comparison_v128.json",
                           data=_json.dumps(comp, indent=2, sort_keys=True),
                           file_name="comparison_v128.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v128_dl_comp")


# =====================
# v129 Pareto from Study (single UI)
# =====================
def _v129_pareto_panel():
    import streamlit as st
    from tools.pareto_from_study import build_pareto, pareto_bundle_zip

    st.subheader("Pareto from Study")
    st.caption("Compute Pareto fronts from a study_matrix zip. No optimizer. Downstream-only, publishable.")

    up = st.file_uploader("Upload study_matrix zip", type=["zip"], key="v129_upl")
    if not up:
        st.info("Upload a v127 study_matrix zip (study_matrix_v127.zip).")
        return

    # Save upload to temp file for existing loaders
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.write(up.getvalue()); tmp.flush(); tmp.close()
    study_path = tmp.name

    st.write("Objectives (choose senses):")
    c1,c2,c3 = st.columns(3)
    with c1:
        obj1 = st.text_input("Objective 1 column", value="Q", key="v129_o1")
        s1 = st.selectbox("Sense 1", options=["max","min"], index=0, key="v129_s1")
    with c2:
        obj2 = st.text_input("Objective 2 column", value="Pnet_MW", key="v129_o2")
        s2 = st.selectbox("Sense 2", options=["max","min"], index=0, key="v129_s2")
    with c3:
        obj3 = st.text_input("Objective 3 column (optional)", value="R0_m", key="v129_o3")
        s3 = st.selectbox("Sense 3", options=["min","max"], index=0, key="v129_s3")

    feasible_only = st.checkbox("Feasible only", value=True, key="v129_feas")
    mission = st.selectbox("Mission filter", options=["(any)","pilot","demo","powerplant"], index=0, key="v129_mis")

    objs=[{"k": obj1.strip(), "sense": s1}]
    if obj2.strip():
        objs.append({"k": obj2.strip(), "sense": s2})
    if obj3.strip():
        objs.append({"k": obj3.strip(), "sense": s3})

    if st.button("Compute Pareto", key="v129_run"):
        try:
            rep = build_pareto(study_path=study_path, objectives=objs, feasible_only=bool(feasible_only), mission=None if mission=="(any)"else mission, version="v129")
            bun = pareto_bundle_zip(rep)
            st.session_state["v129_rep"]=rep
            st.session_state["v129_bun"]=bun
            st.success(f"Computed Pareto: {rep.get('n_filtered')} rows, layers: {len(rep.get('layer_counts') or {})}")
        except Exception as e:
            st.error(f"Failed: {e!r}")
        finally:
            try: os.unlink(study_path)
            except Exception: pass

    rep = st.session_state.get("v129_rep")
    bun = st.session_state.get("v129_bun")
    if isinstance(rep, dict):
        st.write("Summary:")
        st.json({"n_filtered": rep.get("n_filtered"), "layer_counts": rep.get("layer_counts"), "objectives": rep.get("objectives")})
        st.dataframe((rep.get("rows") or [])[:200], use_container_width=True)
        st.download_button("Download pareto_report_v129.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True),
                           file_name="pareto_report_v129.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v129_dl_rep")
    if isinstance(bun, dict) and isinstance(bun.get("zip_bytes"), (bytes,bytearray)):
        st.download_button("Download pareto_bundle_v129.zip",
                           data=bun["zip_bytes"],
                           file_name="pareto_bundle_v129.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v129_dl_zip")


# =====================
# v130 Persistent Run Vault (single UI)
# =====================
def _v130_run_vault_panel():
    import streamlit as st
    from pathlib import Path
    from tools.run_vault import list_entries

    st.subheader("Persistent Run Vault")
    st.caption("Append-only, local vault of run artifacts and bundles. Prevents loss due to reruns/downloads. Storage-only; never changes physics/solvers.")

    c1,c2 = st.columns(2)
    with c1:
        enabled = st.toggle("Enable vault persistence", value=bool(st.session_state.get("vault_enabled", True)), key="vault_enabled")
    with c2:
        limit = st.slider("Show last N entries", min_value=10, max_value=200, value=int(st.session_state.get("vault_limit", 50)), step=10, key="vault_limit")

    root = Path(__file__).resolve().parents[1]
    entries = list_entries(root, limit=int(limit))
    st.write(f"Vault entries: showing last {len(entries)}")
    if entries:
        st.dataframe(entries, use_container_width=True)

        # allow downloading index file
        idx_path = root / "out_run_vault"/ "INDEX.jsonl"
        if idx_path.exists():
            st.download_button("Download vault INDEX.jsonl",
                               data=idx_path.read_bytes(),
                               file_name="INDEX.jsonl",
                               mime="text/plain",
                               use_container_width=True,
                               key="v130_dl_index")
    else:
        st.info("No entries yet. Run a point evaluation or generate a bundle; entries will appear here.")


# =====================
# v131 Vault Restore + Session Replay (single UI)
# =====================
def _v131_vault_restore_panel():
    import streamlit as st
    from pathlib import Path
    from tools.vault_restore import list_entries, load_entry_payload, list_entry_files, read_entry_file

    st.subheader("Vault Restore + Session Replay")
    st.caption("Restore runs and bundles from the persistent vault back into the UI ledger. Downstream-only; no evaluation is performed.")

    root = Path(__file__).resolve().parents[1]
    entries = list_entries(root, limit=int(st.session_state.get("vault_limit", 50)))
    if not entries:
        st.info("No vault entries found yet. Enable the vault and run evaluations/bundles first.")
        return

    # select entry
    labels = []
    for e in entries:
        labels.append(f"{e.get('created_utc','')} | {e.get('record_kind','')} | {e.get('mode','')} | {str(e.get('sha256',''))[:10]}")
    idx = st.selectbox("Select vault entry", options=list(range(len(entries))), format_func=lambda i: labels[i], key="v131_pick")
    meta = entries[int(idx)]

    st.write("Entry meta:")
    st.json(meta)

    c1,c2,c3 = st.columns(3)
    with c1:
        if st.button("Restore payload to Run Ledger", key="v131_restore"):
            try:
                payload = load_entry_payload(root, meta)
                kind = str(meta.get("record_kind") or "vault_restore")
                mode = str(meta.get("mode") or "vault_restore_v131")
                _v98_record_run(kind, payload, mode=mode)
                st.success("Restored into run ledger.")
            except Exception as e:
                st.error(f"Restore failed: {e!r}")

    with c2:
        if st.button("Load payload into viewer (no restore)", key="v131_load"):
            try:
                payload = load_entry_payload(root, meta)
                st.session_state["v131_loaded_payload"] = payload
                st.success("Loaded.")
            except Exception as e:
                st.error(f"Load failed: {e!r}")

    with c3:
        show_files = st.toggle("Show attached files", value=False, key="v131_show_files")

    payload = st.session_state.get("v131_loaded_payload")
    if payload is not None:
        st.write("Loaded payload preview:")
        if isinstance(payload, (bytes, bytearray)):
            st.write(f"Binary payload: {len(payload)} bytes")
        else:
            try:
                st.json(payload)
            except Exception:
                st.write(repr(payload)[:2000])

    if show_files:
        fnames = list_entry_files(root, meta)
        if not fnames:
            st.info("No attached files for this entry.")
        else:
            st.write("Attached files:")
            for fn in fnames:
                b = read_entry_file(root, meta, fn)
                st.download_button(f"Download {fn}", data=b, file_name=fn, use_container_width=True, key=f"v131_dl_{fn}")


# =====================
# v132 Study Matrix Builder v2 (multi-lever sweep) (single UI)
# =====================
def _v132_study_matrix_v2_panel():
    import streamlit as st
    from tools.study_matrix_v2 import build_cases_multi_sweep, build_study_matrix_bundle_v2
    from tools.feasibility_atlas import available_numeric_levers

    st.subheader("Study Matrix Builder v2")
    st.caption("Multi-lever sweeps (2D/3D) with derived columns. Produces a study zip compatible with Study Explorer and Pareto.")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("No runs in ledger yet. Run a point evaluation first.")
        return

    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Select baseline run artifact", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v132_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    base = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if base is None:
        st.error("Selected run does not contain a run artifact payload.")
        return

    base_inputs = base.get("inputs", {}) if isinstance(base.get("inputs"), dict) else {}
    levers = available_numeric_levers(base_inputs)
    if not levers:
        st.warning("No numeric levers detected in baseline inputs.")
        return

    st.write("Define up to 3 sweeps (leave lever blank to disable a sweep):")
    sweeps=[]
    cols = st.columns(3)
    for i in range(3):
        with cols[i]:
            lever = st.selectbox(f"Sweep {i+1} lever", options=["(none)"]+levers, index=0, key=f"v132_lev_{i}")
            if lever != "(none)":
                v0 = float(base_inputs.get(lever, 0.0) or 0.0)
                vmin = st.number_input(f"Min {i+1}", value=(v0*0.95 if abs>1e-9 else -1.0), key=f"v132_min_{i}")
                vmax = st.number_input(f"Max {i+1}", value=(v0*1.05 if abs>1e-9 else 1.0), key=f"v132_max_{i}")
                n = st.slider(f"N {i+1}", min_value=2, max_value=10, value=4, step=1, key=f"v132_n_{i}")
                sweeps.append({"lever": str(lever), "min": float(vmin), "max": float(vmax), "n": int(n)})

    if not sweeps:
        st.info("Choose at least one sweep lever.")
        return

    missions = st.multiselect("Missions (optional)", options=["pilot","demo","powerplant"], default=["pilot"], key="v132_missions")
    derived = st.multiselect("Derived columns", options=["Pnet_per_R0","Q_per_Bt","margin_penalty"], default=["Pnet_per_R0","Q_per_Bt","margin_penalty"], key="v132_derived")

    include_expl = st.checkbox("Include explainability", value=True, key="v132_expl")
    include_ev = st.checkbox("Include evidence/traceability (v123)", value=True, key="v132_ev")
    include_kit = st.checkbox("Include study kit (v123B)", value=True, key="v132_kit")

    est = 1
    for sw in sweeps:
        est *= int(sw.get("n",1))
    est *= max(1, len(missions) if missions else 1)
    st.warning(f"Estimated cases: {est}. Keep it small for local runs.")

    if st.button("Build Study Matrix v132 Zip", key="v132_run"):
        try:
            cases = build_cases_multi_sweep(baseline_run_artifact=base, sweeps=sweeps, missions=(missions or None))
            bundle = build_study_matrix_bundle_v2(
                baseline_run_artifact=base,
                cases=cases,
                outdir="out_study_matrix_v132",
                version="v132",
                include_explainability=bool(include_expl),
                include_evidence=bool(include_ev),
                include_study_kit=bool(include_kit),
                derived=list(derived or []),
            )
            st.session_state["v132_bundle"] = bundle
            _v98_record_run("study_matrix_v2", {"cases": bundle.get("cases")}, mode="study_matrix_v132")
            st.success(f"Study matrix built: {bundle.get('cases')} cases.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    bun = st.session_state.get("v132_bundle")
    if isinstance(bun, dict) and isinstance(bun.get("zip_bytes"), (bytes, bytearray)):
        st.download_button("Download study_matrix_v132.zip",
                           data=bun["zip_bytes"],
                           file_name="study_matrix_v132.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v132_dl_zip")
        st.download_button("Download study_matrix_manifest_v132.json",
                           data=_json.dumps(bun.get("manifest", {}), indent=2, sort_keys=True),
                           file_name="study_matrix_manifest_v132.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v132_dl_manifest")
        st.json({"cases": bun.get("cases"), "created_utc": bun.get("created_utc"), "version": bun.get("version")})


# =====================
# v133 Feasibility Completion (Partial Design Inference) (single UI)
# =====================
def _v133_fc_panel():
    import streamlit as st
    from tools.feasibility_completion import FCConfig, run_feasibility_completion, build_fc_bundle_zip
    from tools.feasibility_atlas import available_numeric_levers
    from tools import run_vault
    from pathlib import Path

    st.subheader("Feasibility Completion")
    st.caption("Partial design inference: fix a few major parameters, mark others as FREE/UNCERTAIN within bounds, and search for any feasible completions. Not an optimizer.")

    # baseline for lever discovery + default values
    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("Run a point evaluation first so SHAMS has a baseline inputs dictionary to start from.")
        return

    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Baseline run (for defaults)", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v133_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    base = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if base is None:
        st.error("Selected baseline does not contain a run artifact payload.")
        return

    base_inputs = base.get("inputs", {}) if isinstance(base.get("inputs"), dict) else {}
    levers = available_numeric_levers(base_inputs)
    if not levers:
        st.warning("No numeric levers detected.")
        return

    st.write("1) Choose FIXED parameters (set values).")
    fixed_choices = st.multiselect("Fixed parameters", options=levers, default=[x for x in ["R0_m","Bt_T","Ip_MA"] if x in levers], key="v133_fixed_list")
    fixed = {}
    if fixed_choices:
        cols = st.columns(min(3, len(fixed_choices)))
        for i,k in enumerate(fixed_choices):
            with cols[i % len(cols)]:
                v0 = float(base_inputs.get(k, 0.0) or 0.0)
                fixed[k] = st.number_input(f"Fixed {k}", value=v0, key=f"v133_fix_{k}")

    st.write("2) Choose FREE parameters (SHAMS searches within bounds). Up to 3 recommended.")
    free_choices = st.multiselect("Free parameters", options=[x for x in levers if x not in fixed_choices], default=[x for x in ["kappa","q95"] if x in levers and x not in fixed_choices], key="v133_free_list")

    st.write("3) Choose UNCERTAIN parameters (sampled within bounds). Optional.")
    uncertain_choices = st.multiselect("Uncertain parameters", options=[x for x in levers if x not in fixed_choices and x not in free_choices], default=[], key="v133_unc_list")

    vars_all = list(dict.fromkeys(list(free_choices) + list(uncertain_choices)))
    if not vars_all:
        st.info("Select at least one FREE or UNCERTAIN parameter.")
        return

    bounds = {}
    st.write("4) Bounds for FREE/UNCERTAIN parameters:")
    for k in vars_all:
        v0 = float(base_inputs.get(k, 0.0) or 0.0)
        c1,c2,c3 = st.columns([1,1,1])
        with c1:
            lo = st.number_input(f"{k} min", value=(v0*0.95 if abs>1e-9 else -1.0), key=f"v133_lo_{k}")
        with c2:
            hi = st.number_input(f"{k} max", value=(v0*1.05 if abs>1e-9 else 1.0), key=f"v133_hi_{k}")
        with c3:
            st.caption(f"baseline={v0:g}")
        bounds[k] = (float(lo), float(hi))

    st.write("5) Search method and budget:")
    method = st.selectbox("Method", options=["grid","random"], index=0, key="v133_method")
    if method == "grid":
        n_per_dim = st.slider("Grid points per dimension", min_value=2, max_value=10, value=4, step=1, key="v133_npd")
        est = 1
        for _ in vars_all: est *= int(n_per_dim)
        st.warning(f"Estimated evaluations: {est}")
        n_random = 0
    else:
        n_random = st.slider("Random samples", min_value=50, max_value=2000, value=300, step=50, key="v133_nr")
        n_per_dim = 0
        st.warning(f"Estimated evaluations: {n_random}")

    seed = st.number_input("Seed (determinism)", value=0, step=1, key="v133_seed")
    feasible_only_export = st.checkbox("Export only feasible evaluations", value=True, key="v133_fe_only")

    if st.button("Run Feasibility Completion", key="v133_run"):
        try:
            cfg = FCConfig(
                baseline_inputs=dict(base_inputs),
                fixed=dict(fixed),
                bounds=dict(bounds),
                free=list(free_choices),
                uncertain=list(uncertain_choices),
                method=str(method),
                n_per_dim=int(n_per_dim) if method=="grid"else 0,
                n_random=int(n_random) if method=="random"else 0,
                seed=int(seed),
                feasible_only_export=bool(feasible_only_export),
            )
            rep = run_feasibility_completion(cfg)
            bun = build_fc_bundle_zip(rep)
            st.session_state["v133_rep"] = rep
            st.session_state["v133_bun"] = bun
            _v98_record_run("feasibility_completion", {"exists_feasible": rep.get("exists_feasible"), "n_evals": rep.get("n_evals"), "n_feasible": rep.get("n_feasible")}, mode="fc_v133")
            st.success(f"Done. Feasible: {rep.get('exists_feasible')} (feasible points: {rep.get('n_feasible')}/{rep.get('n_evals')})")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    rep = st.session_state.get("v133_rep")
    bun = st.session_state.get("v133_bun")
    if isinstance(rep, dict):
        st.write("Report summary:")
        st.json({"exists_feasible": rep.get("exists_feasible"),
                 "n_evals": rep.get("n_evals"),
                 "n_feasible": rep.get("n_feasible"),
                 "envelope": rep.get("envelope"),
                 "dominant_constraint_counts": rep.get("dominant_constraint_counts")})
        st.dataframe((rep.get("evaluations") or [])[:200], use_container_width=True)
        st.download_button("Download fc_report_v133.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True),
                           file_name="fc_report_v133.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v133_dl_rep")

    if isinstance(bun, dict) and isinstance(bun.get("zip_bytes"), (bytes, bytearray)):
        st.download_button("Download fc_bundle_v133.zip",
                           data=bun["zip_bytes"],
                           file_name="fc_bundle_v133.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v133_dl_zip")

        if st.button("Save FC bundle to Vault (attach zip)", key="v133_save_vault"):
            try:
                root = Path(__file__).resolve().parents[1]
                meta = run_vault.write_entry(root=root, kind="fc_bundle", payload=rep or {}, mode="v133", files={"fc_bundle_v133.zip": bun["zip_bytes"]})
                st.success(f"Saved to vault: {meta.get('entry_dir')}")
            except Exception as e:
                st.error(f"Vault save failed: {e!r}")


# =====================
# v134–v138 FC Superpanel (single UI)
# =====================
def _v138_fc_superpanel():
    import streamlit as st
    from pathlib import Path
    from tools import run_vault
    from tools.param_guidance import suggest_free_vars, suggest_bounds, sanity_check_bounds
    from tools.feasibility_completion import FCConfig, run_feasibility_completion, build_fc_bundle_zip
    from tools.fc_advanced import build_fc_atlas_bundle, repair_to_feasibility, RepairConfig, compress_feasible_set, completion_to_run_artifact

    st.subheader("Feasibility Completion Advanced (v134–v138)")
    st.caption("Atlas + guided setup + bounded repair + compression + handoff to study tools. All downstream/orchestration only.")

    # baseline for defaults
    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("Run a point evaluation first to populate the run ledger.")
        return

    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Baseline run (defaults)", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v138_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    base = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if base is None:
        st.error("Selected baseline does not contain a run artifact.")
        return
    base_inputs = base.get("inputs", {}) if isinstance(base.get("inputs"), dict) else {}

    # Use the v133 panel state if present
    rep = st.session_state.get("v133_rep")
    bun = st.session_state.get("v133_bun")

    tabs = st.tabs(["Guided Setup", "Run FC", "Atlas", "Repair (v136)", "Compress (v137)", "Handoff (v138)"])

    # ---------------- v135 ----------------
    with tabs[0]:
        st.write("Suggested FREE variables (heuristics):")
        avail = list(available_numeric_levers(base_inputs))
        fixed_guess = [x for x in ["R0_m","Bt_T"] if x in avail]
        suggested = suggest_free_vars(avail, fixed=fixed_guess, max_k=3)
        st.json({"suggested_free": suggested})
        st.write("Suggested bounds (editable):")
        b = {}
        for v in suggested:
            lo,hi = suggest_bounds(base_inputs, v)
            b[v] = [lo,hi]
            msgs = sanity_check_bounds(v, lo, hi)
            st.write(f"- {v}: [{lo:g}, {hi:g}]"+ (f"{', '.join(msgs)}"if msgs else ""))
        st.caption("You can copy these into the FC run tab.")

    # ---------------- v133 run ----------------
    with tabs[1]:
        st.write("Run Feasibility Completion using baseline defaults + your fixed/free/uncertain selections.")
        levers = list(available_numeric_levers(base_inputs))
        fixed_choices = st.multiselect("Fixed parameters", options=levers, default=[x for x in ["R0_m","Bt_T"] if x in levers], key="v138_fixed_list")
        fixed = {}
        for k in fixed_choices:
            v0 = float(base_inputs.get(k, 0.0) or 0.0)
            fixed[k] = st.number_input(f"Fixed {k}", value=v0, key=f"v138_fix_{k}")

        free_choices = st.multiselect("Free parameters", options=[x for x in levers if x not in fixed_choices], default=[x for x in ["Ip_MA","kappa","q95"] if x in levers and x not in fixed_choices], key="v138_free_list")
        uncertain_choices = st.multiselect("Uncertain parameters", options=[x for x in levers if x not in fixed_choices and x not in free_choices], default=[], key="v138_unc_list")
        vars_all = list(dict.fromkeys(list(free_choices)+list(uncertain_choices)))
        if vars_all:
            st.write("Bounds:")
        bounds={}
        for k in vars_all:
            lo0,hi0 = suggest_bounds(base_inputs, k)
            c1,c2 = st.columns(2)
            with c1:
                lo = st.number_input(f"{k} min", value=float(lo0), key=f"v138_lo_{k}")
            with c2:
                hi = st.number_input(f"{k} max", value=float(hi0), key=f"v138_hi_{k}")
            bounds[k]=(float(lo), float(hi))
            msgs = sanity_check_bounds(k, float(lo), float(hi))
            if msgs:
                st.warning(f"{k}: {', '.join(msgs)}")

        method = st.selectbox("Method", options=["grid","random"], index=0, key="v138_method")
        if method=="grid":
            n_per_dim = st.slider("Grid points per dimension", 2, 10, 4, 1, key="v138_npd")
            n_random = 0
        else:
            n_random = st.slider("Random samples", 50, 2000, 300, 50, key="v138_nr")
            n_per_dim = 0
        seed = st.number_input("Seed", value=0, step=1, key="v138_seed")
        feasible_only = st.checkbox("Export only feasible points", value=True, key="v138_fe_only")

        if st.button("Run FC", key="v138_run_fc"):
            cfg = FCConfig(
                baseline_inputs=dict(base_inputs),
                fixed=dict(fixed),
                bounds=dict(bounds),
                free=list(free_choices),
                uncertain=list(uncertain_choices),
                method=str(method),
                n_per_dim=int(n_per_dim) if method=="grid"else 0,
                n_random=int(n_random) if method=="random"else 0,
                seed=int(seed),
                feasible_only_export=bool(feasible_only),
            )
            rep = run_feasibility_completion(cfg)
            bun = build_fc_bundle_zip(rep)
            st.session_state["v133_rep"] = rep
            st.session_state["v133_bun"] = bun
            _v98_record_run("feasibility_completion", {"exists_feasible": rep.get("exists_feasible"), "n_evals": rep.get("n_evals"), "n_feasible": rep.get("n_feasible")}, mode="fc_v133")
            st.success(f"Feasible: {rep.get('exists_feasible')} (feasible points: {rep.get('n_feasible')}/{rep.get('n_evals')})")

        rep = st.session_state.get("v133_rep")
        bun = st.session_state.get("v133_bun")
        if isinstance(rep, dict):
            st.json({"exists_feasible": rep.get("exists_feasible"), "n_evals": rep.get("n_evals"), "n_feasible": rep.get("n_feasible"), "envelope": rep.get("envelope")})
            st.download_button("Download fc_report_v133.json", data=_json.dumps(rep, indent=2, sort_keys=True), file_name="fc_report_v133.json", mime="application/json", use_container_width=True)
        if isinstance(bun, dict) and isinstance(bun.get("zip_bytes"), (bytes, bytearray)):
            st.download_button("Download fc_bundle_v133.zip", data=bun["zip_bytes"], file_name="fc_bundle_v133.zip", mime="application/zip", use_container_width=True)
            if st.button("Save FC bundle to Vault", key="v138_save_fc_vault"):
                root = Path(__file__).resolve().parents[1]
                run_vault.write_entry(root=root, kind="fc_bundle", payload=rep or {}, mode="v138", files={"fc_bundle_v133.zip": bun["zip_bytes"]})
                st.success("Saved.")

    # ---------------- v134 atlas ----------------
    with tabs[2]:
        rep = st.session_state.get("v133_rep")
        if not isinstance(rep, dict):
            st.info("Run FC first (Run FC tab).")
        else:
            bounds = rep.get("config", {}).get("bounds", {}) if isinstance(rep.get("config"), dict) else {}
            vars_ = list(bounds.keys())
            if len(vars_) < 2:
                st.info("Need at least two bounded variables in FC config to build an atlas.")
            else:
                x = st.selectbox("X axis", options=vars_, index=0, key="v138_atlas_x")
                y = st.selectbox("Y axis", options=[v for v in vars_ if v != x], index=0, key="v138_atlas_y")
                if st.button("Build FC Atlas", key="v138_build_atlas"):
                    try:
                        bun_at = build_fc_atlas_bundle(rep, x_var=str(x), y_var=str(y))
                        st.session_state["v134_atlas"] = bun_at
                        _v98_record_run("fc_atlas", {"x": x, "y": y, "n": bun_at.get("manifest", {}).get("files", {}).get("atlas_points.csv", {}).get("bytes")}, mode="v134")
                        st.success("Atlas built.")
                    except Exception as e:
                        st.error(f"Atlas failed: {e!r}")

                bun_at = st.session_state.get("v134_atlas")
                if isinstance(bun_at, dict) and isinstance(bun_at.get("zip_bytes"), (bytes, bytearray)):
                    st.download_button("Download fc_atlas_v134.zip", data=bun_at["zip_bytes"], file_name="fc_atlas_v134.zip", mime="application/zip", use_container_width=True, key="v138_dl_atlas")
                    st.json(bun_at.get("manifest", {}))

    # ---------------- v136 repair ----------------
    with tabs[3]:
        rep = st.session_state.get("v133_rep")
        if not isinstance(rep, dict):
            st.info("Run FC first (Run FC tab).")
        else:
            evals = list(rep.get("evaluations") or [])
            infeas = [r for r in evals if r.get("feasible") is not True]
            cfg0 = rep.get("config", {}) if isinstance(rep.get("config"), dict) else {}
            bounds = cfg0.get("bounds", {}) if isinstance(cfg0.get("bounds"), dict) else {}
            free = list(cfg0.get("free") or [])
            if not free or not bounds:
                st.info("Repair requires FREE variables with bounds.")
            elif not infeas:
                st.success("No infeasible points in current export. Disable 'feasible-only export' if you want to repair infeasible samples.")
            else:
                st.write(f"Infeasible points available: {len(infeas)}")
                idx = st.slider("Pick infeasible sample index", 0, len(infeas)-1, 0, 1, key="v138_rep_idx")
                start = infeas[int(idx)].get("inputs", {}) if isinstance(infeas[int(idx)].get("inputs"), dict) else {}
                max_steps = st.slider("Max steps", 5, 30, 12, 1, key="v138_rep_steps")
                step_frac = st.slider("Step fraction", 0.05, 0.50, 0.15, 0.05, key="v138_rep_frac")
                seed = st.number_input("Repair seed", value=0, step=1, key="v138_rep_seed")
                if st.button("Run bounded repair", key="v138_run_repair"):
                    try:
                        bnd = {k: (float(v[0]), float(v[1])) for k,v in bounds.items()}
                        cfg = RepairConfig(bounds=bnd, free=list(free), max_steps=int(max_steps), step_frac=float(step_frac), seed=int(seed))
                        tr = repair_to_feasibility(baseline_inputs=dict(base_inputs), start_inputs=dict(start), cfg=cfg)
                        st.session_state["v136_trace"] = tr
                        st.success(f"Repair done. Feasible={tr.get('final',{}).get('feasible')}")
                    except Exception as e:
                        st.error(f"Repair failed: {e!r}")
                tr = st.session_state.get("v136_trace")
                if isinstance(tr, dict):
                    st.json({"final": tr.get("final"), "final_inputs": tr.get("final_inputs")})
                    st.dataframe(tr.get("trace", [])[:200], use_container_width=True)
                    st.download_button("Download repair_trace_v136.json", data=_json.dumps(tr, indent=2, sort_keys=True), file_name="repair_trace_v136.json", mime="application/json", use_container_width=True)

    # ---------------- v137 compress ----------------
    with tabs[4]:
        rep = st.session_state.get("v133_rep")
        if not isinstance(rep, dict):
            st.info("Run FC first.")
        else:
            k = st.slider("Representatives K", 5, 200, 25, 5, key="v138_k")
            if st.button("Compress feasible set", key="v138_compress"):
                comp = compress_feasible_set(rep, k=int(k))
                st.session_state["v137_comp"] = comp
                st.success("Compressed.")
            comp = st.session_state.get("v137_comp")
            if isinstance(comp, dict):
                st.json({"k": comp.get("k"), "n_feasible": comp.get("n_feasible")})
                st.dataframe(comp.get("representatives", [])[:200], use_container_width=True)
                st.download_button("Download fc_compressed_v137.json", data=_json.dumps(comp, indent=2, sort_keys=True), file_name="fc_compressed_v137.json", mime="application/json", use_container_width=True)

    # ---------------- v138 handoff ----------------
    with tabs[5]:
        comp = st.session_state.get("v137_comp")
        rep = st.session_state.get("v133_rep")
        if not isinstance(rep, dict):
            st.info("Run FC first.")
        else:
            # pick best feasible from compressed or report
            best_inputs = None
            if isinstance(comp, dict) and (comp.get("representatives")):
                best_inputs = (comp["representatives"][0].get("inputs") if isinstance(comp["representatives"][0], dict) else None)
            if best_inputs is None:
                feas = [r for r in (rep.get("evaluations") or []) if isinstance(r, dict) and r.get("feasible") is True]
                if feas:
                    best_inputs = feas[0].get("inputs")
            if not isinstance(best_inputs, dict):
                st.info("No feasible point available to hand off. Try expanding bounds or budget.")
            else:
                st.write("Best feasible completion inputs (preview):")
                st.json({k: best_inputs.get(k) for k in list(best_inputs.keys())[:40]})
                if st.button("Evaluate completion as new run + pin", key="v138_handoff_eval"):
                    try:
                        art = completion_to_run_artifact(baseline_inputs=dict(base_inputs), completion_inputs=dict(best_inputs))
                        rid2 = _v98_record_run("handoff_run_artifact", art, mode="fc_handoff_v138")
                        s.pinned_run_ids.append(rid2)
                        st.success(f"Created new run artifact in ledger: {rid2} (pinned)")
                    except Exception as e:
                        st.error(f"Handoff failed: {e!r}")
                st.caption("After creating the pinned run, go to Study Matrix Builder v2 and select the pinned baseline.")


# =====================
# v139 Feasibility Certificate
# =====================
def _v139_feasibility_certificate_panel():
    import streamlit as st
    import json as _json
    from pathlib import Path
    from tools import run_vault
    from tools.feasibility_certificate import generate_feasibility_certificate

    st.subheader("Feasibility Certificate")
    st.caption("Generate an immutable, audit-ready certificate for a specific run artifact.")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("Run a point evaluation first to populate the run ledger.")
        return

    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids) > 0) else ids[-1])
    rid = st.selectbox("Select run", options=ids, index=ids.index(default_id) if default_id in ids else len(ids) - 1, key="v139_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    art = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if art is None:
        st.error("Selected entry does not contain a run artifact.")
        return

    origin = st.selectbox("Origin label", options=["point","fc_handoff","study_matrix",""], index=0, key="v139_origin")

    if st.button("Generate certificate", key="v139_gen"):
        root = Path(__file__).resolve().parents[1]
        cert = generate_feasibility_certificate(run_artifact=art, repo_root=root, run_id=str(rid), origin=str(origin))
        st.session_state["v139_cert"] = cert
        _v98_record_run("feasibility_certificate", {"certificate_id": cert.get("certificate_id"), "worst": cert.get("dominance",{}).get("worst_constraint"), "worst_margin_frac": cert.get("dominance",{}).get("worst_margin_frac")}, mode="v139")
        st.success("Certificate generated.")

    cert = st.session_state.get("v139_cert")
    if isinstance(cert, dict):
        st.json({
            "certificate_id": cert.get("certificate_id"),
            "issued_utc": cert.get("issued_utc"),
            "worst_constraint": (cert.get("dominance") or {}).get("worst_constraint"),
            "worst_margin_frac": (cert.get("dominance") or {}).get("worst_margin_frac"),
            "n_hard": len((cert.get("constraints") or {}).get("hard") or {}),
        })
        st.download_button(
            "Download feasibility_certificate_v139.json",
            data=_json.dumps(cert, indent=2, sort_keys=True),
            file_name="feasibility_certificate_v139.json",
            mime="application/json",
            use_container_width=True,
        )
        if st.button("Save certificate to Vault", key="v139_save_vault"):
            root = Path(__file__).resolve().parents[1]
            run_vault.write_entry(root=root, kind="feasibility_certificate", payload=cert, mode="v139", files={"feasibility_certificate_v139.json": _json.dumps(cert, indent=2, sort_keys=True).encode("utf-8")})
            st.success("Saved.")


# =====================
# v140 Sensitivity Maps (certificate -> fragility envelopes)
# =====================
def _v140_sensitivity_panel():
    import streamlit as st
    from pathlib import Path
    from tools.sensitivity_maps import SensitivityConfig, run_sensitivity, build_sensitivity_bundle
    from tools.feasibility_atlas import available_numeric_levers
    from tools import run_vault

    st.subheader("Constraint Sensitivity Maps")
    st.caption("Finite perturbation sensitivity: how much each variable can vary (+/-) before feasibility breaks. Auditable, no gradients/optimizers.")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("Run a point evaluation first.")
        return
    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Baseline run", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v140_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    base = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if base is None:
        st.error("Selected baseline does not contain a run artifact.")
        return
    base_inputs = base.get("inputs", {}) if isinstance(base.get("inputs"), dict) else {}

    levers = list(available_numeric_levers(base_inputs))
    default_vars = [v for v in ["Ip_MA","kappa","q95","a_m","beta_N","f_GW"] if v in levers]
    vars_sel = st.multiselect("Variables to probe", options=levers, default=(default_vars or levers[:4]), key="v140_vars")
    max_rel = st.slider("Max relative change (+/-)", 0.05, 1.0, 0.40, 0.05, key="v140_max_rel")
    n_expand = st.slider("Expansion steps", 3, 20, 8, 1, key="v140_nexp")
    n_bisect = st.slider("Bisection steps", 3, 20, 10, 1, key="v140_nbis")
    require_feas = st.checkbox("Require baseline feasible", value=True, key="v140_req_feas")

    if st.button("Run sensitivity", key="v140_run"):
        try:
            cfg = SensitivityConfig(
                baseline_inputs=dict(base_inputs),
                fixed_overrides={},
                vars=list(vars_sel),
                bounds={},  # intentionally empty by default; user can constrain later if needed
                max_rel=float(max_rel),
                max_abs=0.0,
                n_expand=int(n_expand),
                n_bisect=int(n_bisect),
                require_baseline_feasible=bool(require_feas),
            )
            rep = run_sensitivity(cfg)
            bun = build_sensitivity_bundle(rep)
            st.session_state["v140_rep"] = rep
            st.session_state["v140_bun"] = bun
            _v98_record_run("sensitivity_maps", {"n_vars": len(vars_sel), "max_rel": max_rel}, mode="v140")
            st.success("Sensitivity run complete.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    rep = st.session_state.get("v140_rep")
    bun = st.session_state.get("v140_bun")
    if isinstance(rep, dict):
        st.json({"baseline": rep.get("baseline"), "n_vars": len(rep.get("results") or [])})
        st.dataframe(rep.get("results", [])[:200], use_container_width=True)
        st.download_button("Download sensitivity_report_v140.json", data=_json.dumps(rep, indent=2, sort_keys=True, default=str),
                           file_name="sensitivity_report_v140.json", mime="application/json", use_container_width=True, key="v140_dl_rep")

    if isinstance(bun, dict) and isinstance(bun.get("zip_bytes"), (bytes, bytearray)):
        st.download_button("Download sensitivity_bundle_v140.zip", data=bun["zip_bytes"], file_name="sensitivity_bundle_v140.zip",
                           mime="application/zip", use_container_width=True, key="v140_dl_zip")
        if st.button("Save sensitivity bundle to Vault", key="v140_save_vault"):
            try:
                root = Path(__file__).resolve().parents[1]
                run_vault.write_entry(root=root, kind="sensitivity_bundle", payload=rep or {}, mode="v140",
                                      files={"sensitivity_bundle_v140.zip": bun["zip_bytes"]})
                st.success("Saved to vault.")
            except Exception as e:
                st.error(f"Vault save failed: {e!r}")


# =====================
# v141 Robustness Certificate
# =====================
def _v141_robustness_panel():
    import streamlit as st
    from pathlib import Path
    from tools.feasibility_certificate import generate_feasibility_certificate
    from tools.sensitivity_maps import SensitivityConfig, run_sensitivity
    from tools.robustness_certificate import generate_robustness_certificate
    from tools.feasibility_atlas import available_numeric_levers
    from tools import run_vault

    st.subheader("Robustness Certificate")
    st.caption("Derives a robustness certificate from v139 Feasibility Certificate + v140 Sensitivity Report. No optimizers/gradients.")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("Run a point evaluation first.")
        return

    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Baseline run (for certificate + sensitivity)", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v141_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    base = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if base is None:
        st.error("Selected baseline does not contain a run artifact.")
        return
    base_inputs = base.get("inputs", {}) if isinstance(base.get("inputs"), dict) else {}

    # v140 settings (re-run sensitivity here for coherence)
    levers = list(available_numeric_levers(base_inputs))
    default_vars = [v for v in ["Ip_MA","kappa","q95","a_m","beta_N","f_GW"] if v in levers]
    vars_sel = st.multiselect("Variables for robustness probing", options=levers, default=(default_vars or levers[:4]), key="v141_vars")
    max_rel = st.slider("Max relative change (+/-) for sensitivity", 0.05, 1.0, 0.40, 0.05, key="v141_max_rel")
    n_expand = st.slider("Expansion steps", 3, 20, 8, 1, key="v141_nexp")
    n_bisect = st.slider("Bisection steps", 3, 20, 10, 1, key="v141_nbis")
    require_feas = st.checkbox("Require baseline feasible", value=True, key="v141_req_feas")

    policy_json = st.text_area("Policy JSON (optional)", value="{}", height=120, key="v141_policy")

    if st.button("Generate Robustness Certificate", key="v141_run"):
        try:
            # v139 cert from current artifact (source of truth)
            fc = generate_feasibility_certificate(base)

            # v140 report (computed here for coherence; also available via v140 panel)
            cfg = SensitivityConfig(
                baseline_inputs=dict(base_inputs),
                fixed_overrides={},
                vars=list(vars_sel),
                bounds={},
                max_rel=float(max_rel),
                max_abs=0.0,
                n_expand=int(n_expand),
                n_bisect=int(n_bisect),
                require_baseline_feasible=bool(require_feas),
            )
            sr = run_sensitivity(cfg)

            policy = _json.loads(policy_json) if policy_json.strip() else {}
            rc = generate_robustness_certificate(fc, sr, policy=policy)

            st.session_state["v141_fc"] = fc
            st.session_state["v141_sr"] = sr
            st.session_state["v141_rc"] = rc
            _v98_record_run("robustness_certificate", {"n_vars": len(vars_sel), "max_rel": max_rel, "index": rc.get("robustness", {}).get("index_min_bounded_rel")}, mode="v141")
            st.success("Robustness certificate generated.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    rc = st.session_state.get("v141_rc")
    fc = st.session_state.get("v141_fc")
    sr = st.session_state.get("v141_sr")

    if isinstance(rc, dict):
        st.json({
            "robustness_index_min_bounded_rel": (rc.get("robustness", {}) or {}).get("index_min_bounded_rel"),
            "fragility_top": ((rc.get("robustness", {}) or {}).get("fragility_ranking") or [])[:5],
        })
        st.download_button("Download robustness_certificate_v141.json",
                           data=_json.dumps(rc, indent=2, sort_keys=True, default=str),
                           file_name="robustness_certificate_v141.json", mime="application/json", use_container_width=True, key="v141_dl_rc")
        with st.expander("See underlying v139 feasibility certificate"):
            st.download_button("Download feasibility_certificate_v139.json",
                               data=_json.dumps(fc or {}, indent=2, sort_keys=True, default=str),
                               file_name="feasibility_certificate_v139.json", mime="application/json", use_container_width=True, key="v141_dl_fc")
        with st.expander("See underlying v140 sensitivity report"):
            st.download_button("Download sensitivity_report_v140.json",
                               data=_json.dumps(sr or {}, indent=2, sort_keys=True, default=str),
                               file_name="sensitivity_report_v140.json", mime="application/json", use_container_width=True, key="v141_dl_sr")

        if st.button("Save robustness certificate to Vault", key="v141_save_vault"):
            try:
                root = Path(__file__).resolve().parents[1]
                run_vault.write_entry(root=root, kind="robustness_certificate", payload=rc, mode="v141",
                                      files={"robustness_certificate_v141.json": _json.dumps(rc, indent=2, sort_keys=True, default=str).encode("utf-8")})
                st.success("Saved to vault.")
            except Exception as e:
                st.error(f"Vault save failed: {e!r}")


# =====================
# v142–v144 Feasibility Deep Dive
# =====================
def _v144_deepdive_panel():
    import streamlit as st
    from pathlib import Path
    from tools.feasibility_atlas import available_numeric_levers
    from tools.feasibility_deepdive import (
        SampleConfig, sample_and_evaluate, topology_from_dataset, bundle_topology,
        interactions_from_dataset, bundle_interactions,
        IntervalConfig, interval_certificate, bundle_interval_certificate,
    )
    from tools import run_vault

    st.subheader("Feasibility Deep Dive (v142–v144)")
    st.caption("Topology maps + constraint interaction structure + interval feasibility certificates. Downstream analysis only.")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("Run a point evaluation first.")
        return
    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Baseline run", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v144_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    base = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if base is None:
        st.error("Selected baseline does not contain a run artifact.")
        return
    base_inputs = base.get("inputs", {}) if isinstance(base.get("inputs"), dict) else {}

    levers = list(available_numeric_levers(base_inputs))
    tabs = st.tabs(["Topology Maps", "Constraint Interactions", "Interval Certificates"])

    # -------- v142
    with tabs[0]:
        st.write("Build feasible topology (islands) by sampling within bounds for selected variables.")
        vars_sel = st.multiselect("Variables (2–6 recommended)", options=levers, default=[v for v in ["Ip_MA","kappa"] if v in levers] or levers[:2], key="v142_vars")
        n_samples = st.slider("Samples", 100, 2000, 300, 50, key="v142_ns")
        seed = st.number_input("Seed", value=0, step=1, key="v142_seed")
        k = st.slider("kNN neighbors", 2, 20, 6, 1, key="v142_k")
        eps = st.number_input("Distance cutoff eps (0 = no cutoff)", value=0.0, key="v142_eps")

        bounds = {}
        for v in vars_sel:
            v0 = float(base_inputs.get(v, 0.0) or 0.0)
            lo = st.number_input(f"{v} min", value=(v0*0.9 if v0 else 0.0), key=f"v142_lo_{v}")
            hi = st.number_input(f"{v} max", value=(v0*1.1 if v0 else 1.0), key=f"v142_hi_{v}")
            bounds[v] = (float(lo), float(hi))

        if st.button("Run topology", key="v142_run"):
            try:
                cfg = SampleConfig(baseline_inputs=dict(base_inputs), vars=list(vars_sel), bounds=dict(bounds), n_samples=int(n_samples), seed=int(seed))
                ds = sample_and_evaluate(cfg)
                topo = topology_from_dataset(ds, k=int(k), eps=float(eps))
                bun = bundle_topology(ds, topo)
                st.session_state["v142_ds"] = ds
                st.session_state["v142_topo"] = topo
                st.session_state["v142_bun"] = bun
                _v98_record_run("feasible_topology", {"n_samples": n_samples, "n_feasible": topo.get("n_feasible_points"), "n_islands": len(topo.get("islands") or [])}, mode="v142")
                st.success(f"Topology built: feasible={topo.get('n_feasible_points')} islands={len(topo.get('islands') or [])}")
            except Exception as e:
                st.error(f"Topology failed: {e!r}")

        topo = st.session_state.get("v142_topo")
        bun = st.session_state.get("v142_bun")
        if isinstance(topo, dict):
            st.json({"n_feasible_points": topo.get("n_feasible_points"), "islands": topo.get("islands")[:10]})
        if isinstance(bun, dict) and isinstance(bun.get("zip_bytes"), (bytes, bytearray)):
            st.download_button("Download topology_bundle_v142.zip", data=bun["zip_bytes"], file_name="topology_bundle_v142.zip", mime="application/zip", use_container_width=True, key="v142_dl")
            if st.button("Save topology bundle to Vault", key="v142_save_vault"):
                root = Path(__file__).resolve().parents[1]
                run_vault.write_entry(root=root, kind="topology_bundle", payload=topo or {}, mode="v142", files={"topology_bundle_v142.zip": bun["zip_bytes"]})
                st.success("Saved.")

    # -------- v143
    with tabs[1]:
        st.write("Compute constraint co-failure and dominance statistics from the last deep-dive dataset.")
        ds = st.session_state.get("v142_ds")
        if not isinstance(ds, dict):
            st.info("Run topology sampling first (v142 tab) to generate a dataset.")
        else:
            if st.button("Compute interactions", key="v143_run"):
                try:
                    inter = interactions_from_dataset(ds, top_n=20)
                    bun2 = bundle_interactions(inter)
                    st.session_state["v143_inter"] = inter
                    st.session_state["v143_bun"] = bun2
                    _v98_record_run("constraint_interactions", {"top_constraints": len(inter.get("top_constraints") or [])}, mode="v143")
                    st.success("Interactions computed.")
                except Exception as e:
                    st.error(f"Interactions failed: {e!r}")
            inter = st.session_state.get("v143_inter")
            bun2 = st.session_state.get("v143_bun")
            if isinstance(inter, dict):
                st.json({"top_constraints": inter.get("top_constraints")[:12], "dominance_top": sorted((inter.get("dominance_counts") or {}).items(), key=lambda kv: kv[1], reverse=True)[:10]})
            if isinstance(bun2, dict) and isinstance(bun2.get("zip_bytes"), (bytes, bytearray)):
                st.download_button("Download interactions_bundle_v143.zip", data=bun2["zip_bytes"], file_name="interactions_bundle_v143.zip", mime="application/zip", use_container_width=True, key="v143_dl")
                if st.button("Save interactions bundle to Vault", key="v143_save_vault"):
                    root = Path(__file__).resolve().parents[1]
                    run_vault.write_entry(root=root, kind="interactions_bundle", payload=inter or {}, mode="v143", files={"interactions_bundle_v143.zip": bun2["zip_bytes"]})
                    st.success("Saved.")

    # -------- v144
    with tabs[2]:
        st.write("Certify a hyper-rectangle interval (conservative): checks all corners + random interior probes.")
        vars_sel = st.multiselect("Interval variables", options=levers, default=[v for v in ["Ip_MA","kappa"] if v in levers] or levers[:2], key="v144_ivars")
        bounds = {}
        for v in vars_sel:
            v0 = float(base_inputs.get(v, 0.0) or 0.0)
            lo = st.number_input(f"{v} min", value=(v0*0.95 if v0 else 0.0), key=f"v144_lo_{v}")
            hi = st.number_input(f"{v} max", value=(v0*1.05 if v0 else 1.0), key=f"v144_hi_{v}")
            bounds[v] = (float(lo), float(hi))
        n_random = st.slider("Random interior probes", 0, 500, 60, 10, key="v144_nr")
        seed = st.number_input("Seed", value=0, step=1, key="v144_seed")
        if st.button("Generate interval certificate (v144)", key="v144_run"):
            try:
                cert = interval_certificate(IntervalConfig(baseline_inputs=dict(base_inputs), bounds=dict(bounds), n_random=int(n_random), seed=int(seed)))
                bun = bundle_interval_certificate(cert)
                st.session_state["v144_cert"] = cert
                st.session_state["v144_bun"] = bun
                _v98_record_run("interval_certificate", {"interval_certified": cert.get("verdict",{}).get("interval_certified"), "n_vars": len(bounds)}, mode="v144")
                st.success(f"Interval certified = {cert.get('verdict',{}).get('interval_certified')}")
            except Exception as e:
                st.error(f"Interval certificate failed: {e!r}")

        cert = st.session_state.get("v144_cert")
        bun = st.session_state.get("v144_bun")
        if isinstance(cert, dict):
            st.json(cert.get("verdict", {}))
            st.download_button("Download interval_certificate_v144.json", data=_json.dumps(cert, indent=2, sort_keys=True, default=str),
                               file_name="interval_certificate_v144.json", mime="application/json", use_container_width=True, key="v144_dl_json")
        if isinstance(bun, dict) and isinstance(bun.get("zip_bytes"), (bytes, bytearray)):
            st.download_button("Download interval_bundle_v144.zip", data=bun["zip_bytes"], file_name="interval_bundle_v144.zip", mime="application/zip", use_container_width=True, key="v144_dl_zip")
            if st.button("Save interval bundle to Vault", key="v144_save_vault"):
                root = Path(__file__).resolve().parents[1]
                run_vault.write_entry(root=root, kind="interval_bundle", payload=cert or {}, mode="v144", files={"interval_bundle_v144.zip": bun["zip_bytes"]})
                st.success("Saved.")


# =====================
# v145 Topology Certificate
# =====================
def _v145_topology_certificate_panel():
    import streamlit as st
    from pathlib import Path
    from tools.topology_certificate import generate_topology_certificate
    from tools import run_vault

    st.subheader("Topology Certificate")
    st.caption("Citable certificate summarizing feasible-set topology (islands) for a declared domain and sampling protocol.")

    s = _v98_state_init_runlists()
    ids = [r.get("id") for r in (s.run_history or []) if r.get("id")]
    if not ids:
        st.info("Run a point evaluation first.")
        return
    default_id = (s.pinned_run_ids[-1] if (s.pinned_run_ids and len(s.pinned_run_ids)>0) else ids[-1])
    rid = st.selectbox("Baseline run", options=ids, index=ids.index(default_id) if default_id in ids else len(ids)-1, key="v145_pick_run")
    run_map = {r.get("id"): r for r in (s.run_history or []) if r.get("id")}
    payload = (run_map.get(rid) or {}).get("payload")
    base = payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None
    if base is None:
        st.error("Selected baseline does not contain a run artifact.")
        return

    topo = st.session_state.get("v142_topo")
    ds = st.session_state.get("v142_ds")
    if not isinstance(topo, dict):
        st.info("Run v142 Topology Maps first (Feasibility Deep Dive panel) to generate feasible topology.")
        return

    policy_json = st.text_area("Policy JSON (optional)", value="{}", height=120, key="v145_policy")

    if st.button("Generate Topology Certificate", key="v145_run"):
        try:
            policy = _json.loads(policy_json) if policy_json.strip() else {}
            cert = generate_topology_certificate(base, topo, deepdive_dataset=(ds if isinstance(ds, dict) else None), policy=policy)
            st.session_state["v145_cert"] = cert
            _v98_record_run("topology_certificate", {"n_islands": (cert.get("topology_summary", {}) or {}).get("n_islands")}, mode="v145")
            st.success("Topology certificate generated.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    cert = st.session_state.get("v145_cert")
    if isinstance(cert, dict):
        st.json(cert.get("topology_summary", {}))
        st.download_button("Download topology_certificate_v145.json",
                           data=_json.dumps(cert, indent=2, sort_keys=True, default=str),
                           file_name="topology_certificate_v145.json", mime="application/json",
                           use_container_width=True, key="v145_dl")
        if st.button("Save topology certificate to Vault", key="v145_save_vault"):
            try:
                root = Path(__file__).resolve().parents[1]
                run_vault.write_entry(root=root, kind="topology_certificate", payload=cert, mode="v145",
                                      files={"topology_certificate_v145.json": _json.dumps(cert, indent=2, sort_keys=True, default=str).encode("utf-8")})
                st.success("Saved to vault.")
            except Exception as e:
                st.error(f"Vault save failed: {e!r}")


# =====================
# v146–v147 Feasibility Completion
# =====================
def _v147_feasibility_completion_panel():
    import streamlit as st
    from pathlib import Path
    from tools.feasibility_atlas import available_numeric_levers
    from tools.feasibility_bridge import BridgeConfig, run_bridge, bridge_certificate
    from tools.safe_domain_shrink import ShrinkConfig, run_safe_domain_shrink
    from tools import run_vault
    import hashlib

    st.subheader("Feasibility Completion (v146–v147)")
    st.caption("v146: topology bridge witness between two points. v147: auto-shrink to a certified safe interval box (uses v144).")

    s = _v98_state_init_runlists()
    runs = [r for r in (s.run_history or []) if r.get("id")]
    ids = [r.get("id") for r in runs]
    if len(ids) < 1:
        st.info("Run at least one point evaluation first.")
        return

    run_map = {r.get("id"): r for r in runs}
    def _get_art(rid):
        payload = (run_map.get(rid) or {}).get("payload")
        return payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None

    tabs = st.tabs(["Bridge Certificate", "Safe Domain Shrink"])

    # ---------- v146
    with tabs[0]:
        if len(ids) < 2:
            st.info("Need at least two runs in history to bridge (A and B).")
        else:
            ridA = st.selectbox("Point A (baseline)", options=ids, index=max(0, len(ids)-2), key="v146_A")
            ridB = st.selectbox("Point B (target)", options=ids, index=len(ids)-1, key="v146_B")
            artA = _get_art(ridA); artB = _get_art(ridB)
            if artA is None or artB is None:
                st.error("Selected runs must be run artifacts.")
            else:
                Ain = artA.get("inputs", {}) if isinstance(artA.get("inputs"), dict) else {}
                Bin = artB.get("inputs", {}) if isinstance(artB.get("inputs"), dict) else {}
                levers = sorted(set(available_numeric_levers(Ain)).intersection(set(available_numeric_levers(Bin))))
                default_vars = [v for v in ["Ip_MA","kappa"] if v in levers] or levers[:2]
                vars_sel = st.multiselect("Bridge variables", options=levers, default=default_vars, key="v146_vars")
                n_steps = st.slider("Coarse steps", 5, 101, 21, 2, key="v146_steps")
                bis = st.slider("Max bisection depth", 0, 10, 6, 1, key="v146_bis")
                req_end = st.checkbox("Require endpoints feasible", value=True, key="v146_req")
                if st.button("Run bridge", key="v146_run"):
                    try:
                        cfg = BridgeConfig(inputs_A=dict(Ain), inputs_B=dict(Bin), vars=list(vars_sel), n_steps=int(n_steps), max_bisect_depth=int(bis), require_endpoints_feasible=bool(req_end))
                        rep = run_bridge(cfg)
                        # baseline hash from A inputs
                        h = hashlib.sha256(_json.dumps(Ain, sort_keys=True, default=str).encode("utf-8")).hexdigest()
                        cert = bridge_certificate(rep, baseline_inputs_sha256=h)
                        st.session_state["v146_rep"] = rep
                        st.session_state["v146_cert"] = cert
                        _v98_record_run("bridge_certificate", {"bridge_exists": rep.get("bridge_exists"), "n_points": len(rep.get("path") or [])}, mode="v146")
                        st.success(f"Bridge exists = {rep.get('bridge_exists')}")
                    except Exception as e:
                        st.error(f"Bridge failed: {e!r}")

                cert = st.session_state.get("v146_cert")
                rep = st.session_state.get("v146_rep")
                if isinstance(cert, dict):
                    st.json(cert.get("summary", {}))
                    st.download_button("Download bridge_certificate_v146.json", data=_json.dumps(cert, indent=2, sort_keys=True, default=str),
                                       file_name="bridge_certificate_v146.json", mime="application/json", use_container_width=True, key="v146_dl_cert")
                    st.download_button("Download bridge_report_v146.json", data=_json.dumps(rep or {}, indent=2, sort_keys=True, default=str),
                                       file_name="bridge_report_v146.json", mime="application/json", use_container_width=True, key="v146_dl_rep")
                    if st.button("Save v146 to Vault", key="v146_save_vault"):
                        root = Path(__file__).resolve().parents[1]
                        run_vault.write_entry(root=root, kind="bridge_certificate", payload={"certificate": cert, "report": rep}, mode="v146",
                                              files={
                                                  "bridge_certificate_v146.json": _json.dumps(cert, indent=2, sort_keys=True, default=str).encode("utf-8"),
                                                  "bridge_report_v146.json": _json.dumps(rep or {}, indent=2, sort_keys=True, default=str).encode("utf-8"),
                                              })
                        st.success("Saved.")

    # ---------- v147
    with tabs[1]:
        rid = st.selectbox("Baseline run for safe box", options=ids, index=len(ids)-1, key="v147_base")
        art = _get_art(rid)
        if art is None:
            st.error("Selected run must be a run artifact.")
        else:
            base_inputs = art.get("inputs", {}) if isinstance(art.get("inputs"), dict) else {}
            levers = list(available_numeric_levers(base_inputs))
            vars_sel = st.multiselect("Interval variables", options=levers, default=[v for v in ["Ip_MA","kappa"] if v in levers] or levers[:2], key="v147_vars")
            bounds={}
            for v in vars_sel:
                v0=float(base_inputs.get(v, 0.0) or 0.0)
                lo = st.number_input(f"{v} min", value=(v0*0.9 if v0 else 0.0), key=f"v147_lo_{v}")
                hi = st.number_input(f"{v} max", value=(v0*1.1 if v0 else 1.0), key=f"v147_hi_{v}")
                bounds[v]=(float(lo), float(hi))
            shrink_factor = st.slider("Shrink factor per iteration", 0.50, 0.98, 0.85, 0.01, key="v147_sf")
            max_iter = st.slider("Max iterations", 1, 30, 10, 1, key="v147_mi")
            n_random = st.slider("Random probes per iteration", 0, 300, 40, 10, key="v147_nr")
            seed = st.number_input("Seed", value=0, step=1, key="v147_seed")

            if st.button("Run safe-domain shrink", key="v147_run"):
                try:
                    cfg = ShrinkConfig(baseline_inputs=dict(base_inputs), bounds=dict(bounds), shrink_factor=float(shrink_factor),
                                       max_iter=int(max_iter), n_random=int(n_random), seed=int(seed))
                    rep = run_safe_domain_shrink(cfg)
                    st.session_state["v147_rep"] = rep
                    _v98_record_run("safe_domain_shrink", {"final_certified": rep.get("final_certified"), "iters": len(rep.get("history") or [])}, mode="v147")
                    st.success(f"Final certified = {rep.get('final_certified')} (iters={len(rep.get('history') or [])})")
                except Exception as e:
                    st.error(f"Shrink failed: {e!r}")

            rep = st.session_state.get("v147_rep")
            if isinstance(rep, dict):
                st.json({"final_certified": rep.get("final_certified"), "final_bounds": rep.get("final_bounds"), "last": (rep.get("history") or [])[-1] if (rep.get("history") or []) else None})
                st.download_button("Download safe_domain_shrink_report_v147.json",
                                   data=_json.dumps(rep, indent=2, sort_keys=True, default=str),
                                   file_name="safe_domain_shrink_report_v147.json", mime="application/json",
                                   use_container_width=True, key="v147_dl_rep")
                cert = rep.get("interval_certificate_v144")
                if isinstance(cert, dict):
                    st.download_button("Download interval_certificate_v144.json",
                                       data=_json.dumps(cert, indent=2, sort_keys=True, default=str),
                                       file_name="interval_certificate_v144.json", mime="application/json",
                                       use_container_width=True, key="v147_dl_cert")
                if st.button("Save v147 to Vault", key="v147_save_vault"):
                    root = Path(__file__).resolve().parents[1]
                    files={"safe_domain_shrink_report_v147.json": _json.dumps(rep, indent=2, sort_keys=True, default=str).encode("utf-8")}
                    if isinstance(cert, dict):
                        files["interval_certificate_v144.json"]=_json.dumps(cert, indent=2, sort_keys=True, default=str).encode("utf-8")
                    run_vault.write_entry(root=root, kind="safe_domain_shrink", payload=rep, mode="v147", files=files)
                    st.success("Saved.")


# =====================
# v148–v150 Publishable Study Kit
# =====================
def _v150_publishable_study_kit_panel():
    import streamlit as st
    from pathlib import Path
    from tools.design_study_kit import PaperPackConfig, build_paper_pack
    from tools import run_vault

    st.subheader("Publishable Study Kit (v148–v150)")
    st.caption("One-click paper pack (zip) with study registry + integrity manifest. Downstream-only.")

    s = _v98_state_init_runlists()
    runs = [r for r in (s.run_history or []) if r.get("id")]
    if not runs:
        st.info("Run at least one evaluation first.")
        return
    ids=[r.get("id") for r in runs]
    run_map={r.get("id"): r for r in runs}

    def _get_art(rid):
        payload = (run_map.get(rid) or {}).get("payload")
        return payload if (isinstance(payload, dict) and payload.get("kind") == "shams_run_artifact") else None

    sel = st.multiselect("Select run(s) to include", options=ids, default=[ids[-1]], key="v150_sel_runs")
    title = st.text_input("Study title", value="SHAMS design study", key="v150_title")
    authors = st.text_input("Authors (comma-separated)", value="", key="v150_authors")
    desc = st.text_area("Description", value="", height=120, key="v150_desc")

    # auto-pick latest certificates present in session_state (best effort)
    certs=[]
    for key, fn in [
        ("v139_fc", "feasibility_certificate_v139.json"),
        ("v141_rc", "robustness_certificate_v141.json"),
        ("v144_ic", "interval_certificate_v144.json"),
        ("v145_tc", "topology_certificate_v145.json"),
        ("v146_bc", "bridge_certificate_v146.json"),
        ("v147_sd", "safe_domain_shrink_report_v147.json"),
    ]:
        obj = st.session_state.get(key)
        if isinstance(obj, dict):
            certs.append((fn, obj))

    st.checkbox("Include best-effort certificates from current session", value=True, key="v150_include_session_certs")
    st.checkbox("Include figures/tables from session bundles", value=True, key="v151_include_session_bundles")
    methods_json = st.text_area("Methods JSON (optional)", value="{}", height=120, key="v150_methods")
    policy_json = st.text_area("Policy JSON (optional)", value='{"mode":"paper_pack"}', height=120, key="v150_policy")

    if st.button("Build Paper Pack", key="v150_run"):
        try:
            run_arts=[]
            for rid in sel:
                art=_get_art(rid)
                if art is not None:
                    run_arts.append(art)
            if not run_arts:
                st.error("No valid run artifacts selected.")
                return

            methods=_json.loads(methods_json) if methods_json.strip() else {}
            policy=_json.loads(policy_json) if policy_json.strip() else {}
            # v154 captions override
            caps = st.session_state.get("v154_captions")
            if isinstance(caps, dict) and caps:
                policy = dict(policy)
                policy["captions_override"] = caps

            cfg=PaperPackConfig(
                shams_version=str((_json.loads((Path(__file__).resolve().parents[1]/"VERSION").read_text(encoding="utf-8").strip().splitlines()[0]) if True else "unknown")),
                title=title,
                authors=[a.strip() for a in authors.split(",") if a.strip()],
                description=desc,
                run_artifacts=run_arts,
                certificates=certs if st.session_state.get("v150_include_session_certs") else [],
                figures=figs,
                tables=tabs,
                methods=methods,
                policy=policy,
            )
            bun=build_paper_pack(cfg)
            st.session_state["v150_pack"]=bun
            _v98_record_run("paper_pack", {"n_runs": len(run_arts), "n_certs": len(cfg.certificates)}, mode="v150")
            st.success("Paper pack built.")
        except Exception as e:
            st.error(f"Failed: {e!r}")

    bun=st.session_state.get("v150_pack")
    if isinstance(bun, dict) and isinstance(bun.get("zip_bytes"), (bytes, bytearray)):
        st.download_button("Download paper_pack_v150.zip", data=bun["zip_bytes"], file_name="paper_pack_v150.zip",
                           mime="application/zip", use_container_width=True, key="v150_dl_zip")
        st.download_button("Download study_registry_v149.json", data=_json.dumps(bun.get("study_registry") or {}, indent=2, sort_keys=True, default=str),
                           file_name="study_registry_v149.json", mime="application/json", use_container_width=True, key="v150_dl_reg")
        st.download_button("Download captions.json", data=_json.dumps({"note":"captions.json is included inside paper_pack_v150.zip"}, indent=2), file_name="captions_note.json", mime="application/json", use_container_width=True, key="v151_dl_caps_note")
        
        st.download_button("Download integrity_manifest_v150.json", data=_json.dumps((bun.get("manifest") or {}), indent=2, sort_keys=True, default=str),
                           file_name="integrity_manifest_v150.json", mime="application/json", use_container_width=True, key="v150_dl_mf")

        if st.button("Save paper pack to Vault", key="v150_save_vault"):
            root = Path(__file__).resolve().parents[1]
            run_vault.write_entry(root=root, kind="paper_pack", payload={"study_registry": bun.get("study_registry"), "manifest": bun.get("manifest")}, mode="v150",
                                  files={
                                      "paper_pack_v150.zip": bun["zip_bytes"],
                                      "study_registry_v149.json": _json.dumps(bun.get("study_registry") or {}, indent=2, sort_keys=True, default=str).encode("utf-8"),
                                      "integrity_manifest_v150.json": _json.dumps(bun.get("manifest") or {}, indent=2, sort_keys=True, default=str).encode("utf-8"),
                                  })
            st.success("Saved.")


# =====================
# v152 Integrity Lock helpers
# =====================
def _v152_artifact_sha(payload):
    import json, hashlib
    b = json.dumps(payload, indent=2, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(b).hexdigest()

def _v152_get_lock_for_run(run_id: str):
    import streamlit as st
    locks = st.session_state.get("v152_locks") or {}
    return locks.get(run_id) if isinstance(locks, dict) else None

def _v152_set_lock_for_run(run_id: str, lock_obj: dict):
    import streamlit as st
    locks = st.session_state.get("v152_locks")
    if not isinstance(locks, dict):
        locks = {}
    locks[str(run_id)] = lock_obj
    st.session_state["v152_locks"] = locks

def _v152_integrity_status(run_id: str, payload: dict):
    lock = _v152_get_lock_for_run(run_id)
    if not isinstance(lock, dict):
        return ("UNLOCKED", None)
    # compare current artifact sha with stored
    expected = ((lock.get("files") or {}).get("run_artifact.json") or {}).get("sha256")
    cur = _v152_artifact_sha(payload)
    if expected and cur == expected:
        return ("VERIFIED", cur)
    return ("MODIFIED", cur)

def _v152_integrity_panel():
    import streamlit as st
    from pathlib import Path
    from tools.run_integrity_lock import lock_run, verify_run
    from tools import run_vault

    st.subheader("Run Integrity Lock")
    st.caption("Lock a run artifact hash and later verify whether it changed. Downstream-only.")

    s = _v98_state_init_runlists()
    runs = [r for r in (s.run_history or []) if r.get("id")]
    if not runs:
        st.info("Run at least one evaluation first.")
        return
    ids=[r.get("id") for r in runs]
    run_map={r.get("id"): r for r in runs}
    rid = st.selectbox("Select run to lock/verify", options=ids, index=len(ids)-1, key="v152_pick_run")
    payload = (run_map.get(rid) or {}).get("payload")
    if not (isinstance(payload, dict) and payload.get("kind")=="shams_run_artifact"):
        st.error("Selected run payload missing.")
        return

    status, cur_sha = _v152_integrity_status(rid, payload)
    st.write(f"Status: **{status}**")
    if cur_sha:
        st.code(cur_sha)

    if st.button("Lock integrity for this run", key="v152_lock"):
        out = lock_run(run_id=str(rid), run_artifact=payload, extras=None, policy={"mode":"ui"})
        lock_obj = out["lock"]
        _v152_set_lock_for_run(rid, lock_obj)
        st.session_state["v152_last_lock"] = lock_obj
        st.success("Locked.")
        _v98_record_run("integrity_lock", {"status":"locked"}, mode="v152")

    lock_obj = _v152_get_lock_for_run(rid) or st.session_state.get("v152_last_lock")
    if isinstance(lock_obj, dict):
        rep = verify_run(lock_obj, payload, extras=None)
        st.json(rep)
        st.download_button("Download run_integrity_lock_v152.json", data=_json.dumps(lock_obj, indent=2, sort_keys=True, default=str),
                           file_name="run_integrity_lock_v152.json", mime="application/json", use_container_width=True, key="v152_dl_lock")
        st.download_button("Download run_integrity_verify_v152.json", data=_json.dumps(rep, indent=2, sort_keys=True, default=str),
                           file_name="run_integrity_verify_v152.json", mime="application/json", use_container_width=True, key="v152_dl_rep")

        if st.button("Save integrity lock to Vault", key="v152_save_vault"):
            root = Path(__file__).resolve().parents[1]
            run_vault.write_entry(root=root, kind="run_integrity_lock", payload={"lock": lock_obj, "verify": rep}, mode="v152",
                                  files={
                                      "run_integrity_lock_v152.json": _json.dumps(lock_obj, indent=2, sort_keys=True, default=str).encode("utf-8"),
                                      "run_integrity_verify_v152.json": _json.dumps(rep, indent=2, sort_keys=True, default=str).encode("utf-8"),
                                  })
            st.success("Saved.")


# =====================
# v153–v155 Study Kit Extensions
# =====================
def _v153_doi_export_panel():
    import streamlit as st
    from tools.doi_export import zenodo_metadata_from_registry, crossref_minimal_from_registry

    st.subheader("DOI Export Helper")
    st.caption("Export Zenodo/Crossref-style metadata from the latest study registry built in this session.")

    bun = st.session_state.get("v150_pack")
    reg = (bun or {}).get("study_registry") if isinstance(bun, dict) else None
    if not isinstance(reg, dict):
        st.info("Build a Paper Pack first (Publishable Study Kit panel).")
        return

    comm = st.text_input("Zenodo communities (comma-separated identifiers)", value="", key="v153_comm")
    kws = st.text_input("Keywords (comma-separated)", value="", key="v153_kws")
    doi = st.text_input("DOI (optional)", value="", key="v153_doi")
    publisher = st.text_input("Publisher (optional)", value="SHAMS", key="v153_pub")
    url = st.text_input("Resource URL (optional)", value="", key="v153_url")

    communities=[c.strip() for c in comm.split(",") if c.strip()] if comm else []
    keywords=[k.strip() for k in kws.split(",") if k.strip()] if kws else []

    zen = zenodo_metadata_from_registry(reg, communities=communities, keywords=keywords)
    cr  = crossref_minimal_from_registry(reg, doi=doi, publisher=publisher, resource_url=url)

    st.download_button("Download zenodo_metadata_v153.json", data=_json.dumps(zen, indent=2, sort_keys=True, default=str),
                       file_name="zenodo_metadata_v153.json", mime="application/json", use_container_width=True, key="v153_dl_zen")
    st.download_button("Download crossref_minimal_v153.json", data=_json.dumps(cr, indent=2, sort_keys=True, default=str),
                       file_name="crossref_minimal_v153.json", mime="application/json", use_container_width=True, key="v153_dl_cr")

def _v154_caption_editor_panel():
    import streamlit as st
    st.subheader("Caption Editor")
    st.caption("Edit captions for figures/tables included in the paper pack. Captions are stored in session and exported into paper packs.")

    # Captions live in session state and are applied when building the paper pack.
    caps = st.session_state.get("v154_captions")
    if not isinstance(caps, dict):
        caps = {}
        st.session_state["v154_captions"] = caps

    # Show detected figure/table filenames from latest built pack, if any
    bun = st.session_state.get("v150_pack")
    reg = (bun or {}).get("study_registry") if isinstance(bun, dict) else None
    names=[]
    if isinstance(reg, dict):
        for ref in (reg.get("figures") or []):
            if isinstance(ref, dict) and ref.get("name"):
                names.append(ref["name"])
        for ref in (reg.get("tables") or []):
            if isinstance(ref, dict) and ref.get("name"):
                names.append(ref["name"])
    names = sorted(set(names))

    if not names:
        st.info("No figures/tables detected yet. Build a Paper Pack with v151 session-bundle harvesting enabled.")
    else:
        pick = st.selectbox("Select figure/table", options=names, key="v154_pick")
        cur = caps.get(pick, f"Figure/Table: {pick}.")
        new = st.text_area("Caption text", value=cur, height=120, key="v154_text")
        if st.button("Save caption", key="v154_save"):
            caps[pick] = new
            st.session_state["v154_captions"] = caps
            st.success("Saved.")
        st.download_button("Download captions_override_v154.json", data=_json.dumps({"captions": caps}, indent=2, sort_keys=True, default=str),
                           file_name="captions_override_v154.json", mime="application/json", use_container_width=True, key="v154_dl")

def _v155_multi_study_pack_panel():
    import streamlit as st
    from tools.multi_study_pack import build_multi_study_pack

    st.subheader("Multi-Study Comparison Pack")
    st.caption("Upload multiple paper packs and export a comparison bundle with a multi-pack integrity manifest.")

    files = st.file_uploader("Upload paper_pack_v150.zip files", type=["zip"], accept_multiple_files=True, key="v155_upload")
    if not files:
        st.info("Upload 2+ paper packs to compare.")
        return
    packs=[]
    for f in files:
        packs.append((f.name, f.getvalue()))

    bun = build_multi_study_pack(packs, policy={"source":"ui"})
    st.json({"n_packs": len(packs), "manifest_sha256": (bun.get("manifest") or {}).get("hashes",{}).get("manifest_sha256")})
    st.download_button("Download multi_study_pack_v155.zip", data=bun["zip_bytes"], file_name="multi_study_pack_v155.zip",
                       mime="application/zip", use_container_width=True, key="v155_dl_zip")
    st.download_button("Download comparison_report_v155.json", data=_json.dumps(bun.get("bundle") or {}, indent=2, sort_keys=True, default=str),
                       file_name="comparison_report_v155.json", mime="application/json", use_container_width=True, key="v155_dl_rep")


# =====================
# v156 / v160 Design Space Authority (Atlas + Certificates)
# =====================
def _v156_feasibility_atlas_panel():
    import streamlit as st
    from tools.feasibility_field import build_feasibility_field

    st.subheader("Feasibility Atlas")
    st.caption("Sample a 2D design space slice and export a feasibility field + atlas bundle.")

    s = _v98_state_init_runlists()
    runs = [r for r in (s.run_history or []) if r.get("id")]
    if not runs:
        st.info("Run at least one evaluation first (Point Designer / Systems Mode).")
        return
    ids=[r.get("id") for r in runs]
    run_map={r.get("id"): r for r in runs}
    rid = st.selectbox("Baseline run", options=ids, index=len(ids)-1, key="v156_base_run")
    payload = (run_map.get(rid) or {}).get("payload")
    if not (isinstance(payload, dict) and payload.get("kind")=="shams_run_artifact"):
        st.error("Selected baseline run payload missing.")
        return
    baseline_inputs = payload.get("inputs") or payload.get("_inputs") or {}
    if not isinstance(baseline_inputs, dict) or not baseline_inputs:
        st.error("Baseline inputs missing.")
        return

    keys=sorted([k for k in baseline_inputs.keys() if isinstance(k,str)])
    col1,col2=st.columns(2)
    with col1:
        a1 = st.selectbox("Axis 1 parameter", options=keys, index=0 if keys else 0, key="v156_a1")
        a1_start = st.number_input("Axis 1 start", value=float(baseline_inputs.get(a1, 0.0) or 0.0), key="v156_a1s")
        a1_stop  = st.number_input("Axis 1 stop", value=float(baseline_inputs.get(a1, 1.0) or 1.0)+1.0, key="v156_a1e")
        a1_n     = st.number_input("Axis 1 N", value=25, min_value=2, max_value=250, step=1, key="v156_a1n")
    with col2:
        a2 = st.selectbox("Axis 2 parameter", options=keys, index=1 if len(keys)>1 else 0, key="v156_a2")
        a2_start = st.number_input("Axis 2 start", value=float(baseline_inputs.get(a2, 0.0) or 0.0), key="v156_a2s")
        a2_stop  = st.number_input("Axis 2 stop", value=float(baseline_inputs.get(a2, 1.0) or 1.0)+1.0, key="v156_a2e")
        a2_n     = st.number_input("Axis 2 N", value=25, min_value=2, max_value=250, step=1, key="v156_a2n")

    fixed_json = st.text_area("Fixed overrides (JSON list of {name,value})", value="[]", height=90, key="v156_fixed")
    assumptions_json = st.text_area("Assumption set (JSON object)", value="{}", height=90, key="v156_assumptions")
    margin_eps = st.number_input("Margin epsilon for feasible", value=1e-6, format="%.1e", key="v156_eps")
    run_btn = st.button("Build Feasibility Field", use_container_width=True, key="v156_run")

    if run_btn:
        try:
            fixed = _json.loads(fixed_json) if fixed_json.strip() else []
            assumptions = _json.loads(assumptions_json) if assumptions_json.strip() else {}
        except Exception as e:
            st.error(f"JSON parse error: {e}")
            return

        axis1={"name": a1, "role":"axis", "grid":{"type":"linspace","start": float(a1_start), "stop": float(a1_stop), "n": int(a1_n)}}
        axis2={"name": a2, "role":"axis", "grid":{"type":"linspace","start": float(a2_start), "stop": float(a2_stop), "n": int(a2_n)}}
        with st.spinner("Sampling feasibility field..."):
            out = build_feasibility_field(
                baseline_inputs=baseline_inputs,
                axis1=axis1,
                axis2=axis2,
                fixed=fixed if isinstance(fixed, list) else [],
                assumption_set=assumptions if isinstance(assumptions, dict) else {},
                sampling={"generator":"ui","strategy":"grid"},
                solver_meta={"label":"feasibility_field_v156"},
                margin_eps=float(margin_eps),
            )
        st.session_state["v156_field"] = out["field"]
        st.session_state["v156_atlas_zip"] = out["zip_bytes"]
        summ = (((out["field"].get("payload") or {}).get("field") or {}).get("summaries") or {})
        st.success("Built.")
        st.json(summ)
        st.download_button("Download feasibility_atlas_bundle_v156.zip", data=out["zip_bytes"], file_name="feasibility_atlas_bundle_v156.zip",
                           mime="application/zip", use_container_width=True, key="v156_dl_zip")
        st.download_button("Download feasibility_field_v156.json", data=_json.dumps(out["field"], indent=2, sort_keys=True, default=str),
                           file_name="feasibility_field_v156.json", mime="application/json", use_container_width=True, key="v156_dl_json")

def _v160_authority_certificate_panel():
    import streamlit as st
    from tools.feasibility_authority_certificate import issue_certificate_from_field

    st.subheader("Feasibility Authority Certificate")
    st.caption("Issue an authority certificate from a feasibility field (dense sampling basis).")

    field = st.session_state.get("v156_field")
    up = st.file_uploader("Optional: upload feasibility_field_v156.json", type=["json"], key="v160_upload")
    if up is not None:
        try:
            field = _json.loads(up.getvalue().decode("utf-8"))
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
            return

    if not isinstance(field, dict):
        st.info("Build a Feasibility Field first or upload one here.")
        return

    claim = st.selectbox("Claim type", options=["feasible_region","excluded_region","boundary_surface","completion_existence"], index=1, key="v160_claim")
    default_stmt = "Under assumption_set SHA256=..., region sampled is excluded/feasible under dense sampling evidence."
    stmt = st.text_area("Claim statement (human-readable, publishable)", value=default_stmt, height=110, key="v160_stmt")
    conf = st.number_input("Confidence level", value=0.95, min_value=0.5, max_value=0.999, step=0.01, key="v160_conf")
    grade = st.selectbox("Grade", options=["A","B","C"], index=1, key="v160_grade")

    if st.button("Issue Certificate", use_container_width=True, key="v160_issue"):
        cert = issue_certificate_from_field(field=field, claim_type=claim, statement=stmt, confidence_level=float(conf), confidence_grade=str(grade), policy={"mode":"ui"})
        st.session_state["v160_cert"] = cert
        st.success("Issued.")
        st.json(cert.get("payload") or {})
        st.download_button("Download feasibility_authority_certificate_v160.json",
                           data=_json.dumps(cert, indent=2, sort_keys=True, default=str),
                           file_name="feasibility_authority_certificate_v160.json",
                           mime="application/json", use_container_width=True, key="v160_dl")


# =====================
# v157 Feasibility Boundary Extractor
# =====================
def _v157_feasibility_boundary_panel():
    import streamlit as st
    from tools.feasibility_boundary import build_feasibility_boundary

    st.subheader("Feasibility Boundary")
    st.caption("Extract a feasibility boundary curve from a v156 feasibility field (grid interpolation).")

    field = st.session_state.get("v156_field")
    up = st.file_uploader("Optional: upload feasibility_field_v156.json", type=["json"], key="v157_upload")
    if up is not None:
        try:
            field = _json.loads(up.getvalue().decode("utf-8"))
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
            return
    if not isinstance(field, dict):
        st.info("Build a Feasibility Field first or upload one here.")
        return

    prefer_lowest = st.checkbox("Prefer lowest Axis2 crossing (typical min required)", value=True, key="v157_low")
    if st.button("Extract Boundary", use_container_width=True, key="v157_run"):
        b = build_feasibility_boundary(field=field, prefer_lowest_axis2=bool(prefer_lowest))
        st.session_state["v157_boundary"] = b
        st.success(f"Extracted {len(((b.get('payload') or {}).get('boundary') or {}).get('samples') or [])} samples.")
        st.json((b.get("payload") or {}).get("boundary_definition") or {})
        st.download_button("Download feasibility_boundary_v157.json",
                           data=_json.dumps(b, indent=2, sort_keys=True, default=str),
                           file_name="feasibility_boundary_v157.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v157_dl")


# =====================
# v158 Constraint Dominance Topology
# =====================
def _v158_constraint_dominance_panel():
    import streamlit as st
    from tools.constraint_dominance import build_constraint_dominance

    st.subheader("Constraint Dominance Topology")
    st.caption("Explain why regions fail: dominant violated constraint maps + connected components (grid topology).")

    field = st.session_state.get("v156_field")
    up = st.file_uploader("Optional: upload feasibility_field_v156.json", type=["json"], key="v158_upload")
    if up is not None:
        try:
            field = _json.loads(up.getvalue().decode("utf-8"))
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
            return
    if not isinstance(field, dict):
        st.info("Build a Feasibility Field first or upload one here.")
        return

    include_all = st.checkbox("Include feasible points in dominance map (larger JSON)", value=False, key="v158_all")
    if st.button("Compute Dominance Topology", use_container_width=True, key="v158_run"):
        dom = build_constraint_dominance(field=field, only_infeasible=(not include_all))
        st.session_state["v158_dom"] = dom
        summ = (((dom.get("payload") or {}).get("dominance") or {}).get("summary") or {})
        st.success("Computed.")
        st.json(summ)
        st.download_button("Download constraint_dominance_v158.json",
                           data=_json.dumps(dom, indent=2, sort_keys=True, default=str),
                           file_name="constraint_dominance_v158.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v158_dl")


# =====================
# v159 Feasibility Completion Evidence
# =====================
def _v159_feasibility_completion_panel():
    import streamlit as st
    from tools.feasibility_completion_evidence import build_feasibility_completion_evidence

    st.subheader("Feasibility Completion Evidence")
    st.caption("Given partial inputs + bounds on unknowns, search for a feasible completion witness and report bottlenecks.")

    s = _v98_state_init_runlists()
    runs = [r for r in (s.run_history or []) if r.get("id")]
    if not runs:
        st.info("Run at least one evaluation first (Point Designer / Systems Mode).")
        return
    ids=[r.get("id") for r in runs]
    run_map={r.get("id"): r for r in runs}
    rid = st.selectbox("Baseline run (provides default known inputs)", options=ids, index=len(ids)-1, key="v159_base_run")
    payload = (run_map.get(rid) or {}).get("payload")
    if not (isinstance(payload, dict) and payload.get("kind")=="shams_run_artifact"):
        st.error("Selected baseline run payload missing.")
        return
    baseline_inputs = payload.get("inputs") or payload.get("_inputs") or {}
    if not isinstance(baseline_inputs, dict) or not baseline_inputs:
        st.error("Baseline inputs missing.")
        return

    st.markdown("### Unknowns to search")
    keys=sorted([k for k in baseline_inputs.keys() if isinstance(k,str)])
    unk = st.multiselect("Select unknown parameters (will be randomized within bounds)", options=keys, default=[k for k in keys if k in ("R0_m","B0_T")], key="v159_unk_keys")
    st.caption('Provide bounds as JSON list: [{"name":"R0_m","bounds":[2.5,3.5]}, ...]')
    default_bounds=_json.dumps([{"name":k, "bounds":[float(baseline_inputs.get(k,0.0) or 0.0)*0.9, float(baseline_inputs.get(k,0.0) or 0.0)*1.1+1e-9]} for k in (unk or [])][:6], indent=2)
    bounds_json = st.text_area("Unknown bounds (JSON)", value=default_bounds, height=140, key="v159_bounds")
    fixed_json = st.text_area("Fixed overrides (JSON list of {name,value})", value="[]", height=80, key="v159_fixed")
    assumptions_json = st.text_area("Assumption set (JSON object)", value="{}", height=80, key="v159_assumptions")

    col1,col2,col3=st.columns(3)
    with col1:
        n_samples = st.number_input("Samples", value=400, min_value=20, max_value=20000, step=20, key="v159_n")
    with col2:
        seed = st.number_input("Seed", value=0, min_value=0, max_value=10_000_000, step=1, key="v159_seed")
    with col3:
        strategy = st.selectbox("Strategy", options=["random","lhs"], index=0, key="v159_strategy")

    if st.button("Search Completion Witness", use_container_width=True, key="v159_run"):
        try:
            unknowns = _json.loads(bounds_json) if bounds_json.strip() else []
            fixed = _json.loads(fixed_json) if fixed_json.strip() else []
            assumptions = _json.loads(assumptions_json) if assumptions_json.strip() else {}
        except Exception as e:
            st.error(f"JSON parse error: {e}")
            return

        # known = baseline minus unknown keys
        known = {k:v for k,v in baseline_inputs.items() if (k not in set(unk or []))}
        with st.spinner("Sampling for feasibility completion..."):
            ev = build_feasibility_completion_evidence(
                known=known,
                unknowns=unknowns,
                fixed=fixed if isinstance(fixed,list) else [],
                assumption_set=assumptions if isinstance(assumptions,dict) else {},
                n_samples=int(n_samples),
                seed=int(seed),
                strategy=str(strategy),
                policy={"generator":"ui"},
            )
        st.session_state["v159_completion"] = ev
        res=((ev.get("payload") or {}).get("result") or {})
        st.success(f"Verdict: {res.get('verdict')}")
        st.json(res.get("bottleneck") or {})
        st.download_button("Download feasibility_completion_evidence_v159.json",
                           data=_json.dumps(ev, indent=2, sort_keys=True, default=str),
                           file_name="feasibility_completion_evidence_v159.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v159_dl")


# =====================
# v161 Completion Frontier + Minimal Change Distance
# =====================
def _v161_completion_frontier_panel():
    import streamlit as st
    from tools.completion_frontier import build_completion_frontier

    st.subheader("Completion Frontier")
    st.caption("Quantify how far a baseline guess is from feasibility: minimal-change feasible witness + distance–margin frontier.")

    s = _v98_state_init_runlists()
    runs = [r for r in (s.run_history or []) if r.get("id")]
    if not runs:
        st.info("Run at least one evaluation first (Point Designer / Systems Mode).")
        return
    ids=[r.get("id") for r in runs]
    run_map={r.get("id"): r for r in runs}
    rid = st.selectbox("Baseline run (baseline guess x0)", options=ids, index=len(ids)-1, key="v161_base_run")
    payload = (run_map.get(rid) or {}).get("payload")
    if not (isinstance(payload, dict) and payload.get("kind")=="shams_run_artifact"):
        st.error("Selected baseline run payload missing.")
        return
    baseline_inputs = payload.get("inputs") or payload.get("_inputs") or {}
    if not isinstance(baseline_inputs, dict) or not baseline_inputs:
        st.error("Baseline inputs missing.")
        return

    st.markdown("### Decision variables (vary to reach feasibility)")
    keys=sorted([k for k in baseline_inputs.keys() if isinstance(k,str)])
    dv = st.multiselect("Select decision variables", options=keys, default=[k for k in keys if k in ("R0_m","B0_T","q95","kappa")], key="v161_dv_keys")
    default_bounds=_json.dumps([{"name":k, "bounds":[float(baseline_inputs.get(k,0.0) or 0.0)*0.9, float(baseline_inputs.get(k,0.0) or 0.0)*1.1+1e-9]} for k in (dv or [])][:8], indent=2)
    st.caption('Bounds JSON example: [{"name":"R0_m","bounds":[2.5,3.5]}, ...]')
    bounds_json = st.text_area("Decision variable bounds (JSON)", value=default_bounds, height=160, key="v161_bounds")
    fixed_json = st.text_area("Fixed overrides (JSON list of {name,value})", value="[]", height=80, key="v161_fixed")
    assumptions_json = st.text_area("Assumption set (JSON object)", value="{}", height=80, key="v161_assumptions")

    col1,col2,col3=st.columns(3)
    with col1:
        n_samples = st.number_input("Samples", value=800, min_value=40, max_value=50000, step=40, key="v161_n")
    with col2:
        seed = st.number_input("Seed", value=0, min_value=0, max_value=10_000_000, step=1, key="v161_seed")
    with col3:
        strategy = st.selectbox("Strategy", options=["random","lhs"], index=0, key="v161_strategy")

    if st.button("Compute Completion Frontier", use_container_width=True, key="v161_run"):
        try:
            vars_spec = _json.loads(bounds_json) if bounds_json.strip() else []
            fixed = _json.loads(fixed_json) if fixed_json.strip() else []
            assumptions = _json.loads(assumptions_json) if assumptions_json.strip() else {}
        except Exception as e:
            st.error(f"JSON parse error: {e}")
            return
        with st.spinner("Sampling and evaluating frontier..."):
            out = build_completion_frontier(
                baseline=baseline_inputs,
                decision_vars=vars_spec,
                fixed=fixed if isinstance(fixed,list) else [],
                assumption_set=assumptions if isinstance(assumptions,dict) else {},
                n_samples=int(n_samples),
                seed=int(seed),
                strategy=str(strategy),
                policy={"generator":"ui"},
            )
        st.session_state["v161_frontier"] = out
        res=((out.get("payload") or {}).get("result") or {})
        st.success("Computed.")
        st.markdown("**Minimal-change feasible witness**")
        st.json(res.get("minimal_change_feasible") or {})
        st.markdown("**Frontier (preview)**")
        st.json((res.get("frontier") or [])[:20])
        st.download_button("Download completion_frontier_v161.json",
                           data=_json.dumps(out, indent=2, sort_keys=True, default=str),
                           file_name="completion_frontier_v161.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v161_dl")


# =====================
# v162 Directed Local Search (safe)
# =====================
def _v162_directed_local_search_panel():
    import streamlit as st
    from tools.directed_local_search import build_directed_local_search

    st.subheader("Directed Local Search")
    st.caption("A safe, bounded local search that tries to reach feasibility with minimal evaluations (downstream-only).")

    s = _v98_state_init_runlists()
    runs = [r for r in (s.run_history or []) if r.get("id")]
    if not runs:
        st.info("Run at least one evaluation first (Point Designer / Systems Mode).")
        return
    ids=[r.get("id") for r in runs]
    run_map={r.get("id"): r for r in runs}
    rid = st.selectbox("Baseline run (starting guess)", options=ids, index=len(ids)-1, key="v162_base_run")
    payload = (run_map.get(rid) or {}).get("payload")
    if not (isinstance(payload, dict) and payload.get("kind")=="shams_run_artifact"):
        st.error("Selected baseline run payload missing.")
        return
    baseline_inputs = payload.get("inputs") or payload.get("_inputs") or {}
    if not isinstance(baseline_inputs, dict) or not baseline_inputs:
        st.error("Baseline inputs missing.")
        return

    st.markdown("### Decision variables")
    keys=sorted([k for k in baseline_inputs.keys() if isinstance(k,str)])
    dv = st.multiselect("Select decision variables to adjust", options=keys, default=[k for k in keys if k in ("R0_m","B0_T","q95","kappa")], key="v162_dv_keys")
    default_bounds=_json.dumps([{"name":k, "bounds":[float(baseline_inputs.get(k,0.0) or 0.0)*0.9, float(baseline_inputs.get(k,0.0) or 0.0)*1.1+1e-9]} for k in (dv or [])][:8], indent=2)
    st.caption('Bounds JSON example: [{"name":"R0_m","bounds":[2.5,3.5]}, ...]')
    bounds_json = st.text_area("Decision variable bounds (JSON)", value=default_bounds, height=160, key="v162_bounds")
    fixed_json = st.text_area("Fixed overrides (JSON list of {name,value})", value="[]", height=80, key="v162_fixed")
    assumptions_json = st.text_area("Assumption set (JSON object)", value="{}", height=80, key="v162_assumptions")

    col1,col2,col3,col4=st.columns(4)
    with col1:
        max_evals = st.number_input("Max evals", value=200, min_value=30, max_value=5000, step=10, key="v162_maxeval")
    with col2:
        seed = st.number_input("Seed", value=0, min_value=0, max_value=10_000_000, step=1, key="v162_seed")
    with col3:
        init_step = st.number_input("Initial step (norm)", value=0.12, min_value=0.01, max_value=0.50, step=0.01, key="v162_initstep")
    with col4:
        min_step = st.number_input("Min step (norm)", value=0.004, min_value=0.0005, max_value=0.10, step=0.0005, format="%.4f", key="v162_minstep")

    shrink = st.slider("Step shrink factor", min_value=0.2, max_value=0.9, value=0.5, step=0.05, key="v162_shrink")

    if st.button("Run Directed Search", use_container_width=True, key="v162_run"):
        try:
            vars_spec = _json.loads(bounds_json) if bounds_json.strip() else []
            fixed = _json.loads(fixed_json) if fixed_json.strip() else []
            assumptions = _json.loads(assumptions_json) if assumptions_json.strip() else {}
        except Exception as e:
            st.error(f"JSON parse error: {e}")
            return
        with st.spinner("Searching..."):
            out = build_directed_local_search(
                baseline=baseline_inputs,
                decision_vars=vars_spec,
                fixed=fixed if isinstance(fixed,list) else [],
                assumption_set=assumptions if isinstance(assumptions,dict) else {},
                max_evals=int(max_evals),
                seed=int(seed),
                initial_step_norm=float(init_step),
                min_step_norm=float(min_step),
                step_shrink=float(shrink),
                policy={"generator":"ui"},
            )
        st.session_state["v162_local_search"] = out
        res=((out.get("payload") or {}).get("result") or {})
        st.success(f"Stop reason: {res.get('stop_reason')}")
        st.json(res.get("final") or {})
        st.download_button("Download directed_local_search_v162.json",
                           data=_json.dumps(out, indent=2, sort_keys=True, default=str),
                           file_name="directed_local_search_v162.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v162_dl")


# =====================
# v163 Completion Pack (Actionable Recipe)
# =====================
def _v163_completion_pack_panel():
    import streamlit as st
    from tools.completion_pack import build_completion_pack, render_completion_pack_markdown

    st.subheader("Completion Pack")
    st.caption("Bundle completion evidence into an actionable recipe: witness + knob ranking + bounds recommendations.")

    v159 = st.session_state.get("v159_completion")
    v161 = st.session_state.get("v161_frontier")
    v162 = st.session_state.get("v162_local_search")

    st.markdown("### Inputs")
    colA,colB,colC = st.columns(3)
    with colA:
        up159 = st.file_uploader("Optional: upload v159 evidence JSON", type=["json"], key="v163_up159")
    with colB:
        up161 = st.file_uploader("Optional: upload v161 frontier JSON", type=["json"], key="v163_up161")
    with colC:
        up162 = st.file_uploader("Optional: upload v162 local search JSON", type=["json"], key="v163_up162")

    def _load(up):
        if up is None:
            return None
        try:
            return _json.loads(up.getvalue().decode("utf-8"))
        except Exception:
            return None

    v159 = _load(up159) or v159
    v161 = _load(up161) or v161
    v162 = _load(up162) or v162

    tighten = st.slider("Bounds tighten factor (heuristic)", min_value=0.05, max_value=0.45, value=0.25, step=0.05, key="v163_tighten")

    if st.button("Build Completion Pack", use_container_width=True, key="v163_run"):
        pack = build_completion_pack(v159=v159, v161=v161, v162=v162, policy={"generator":"ui", "tighten": float(tighten)})
        st.session_state["v163_pack"] = pack
        st.success(f"Witness provenance: {((pack.get('payload') or {}).get('witness_provenance') or '')}")
        st.markdown("### Preview")
        st.json((pack.get("payload") or {}) )
        st.download_button("Download completion_pack_v163.json",
                           data=_json.dumps(pack, indent=2, sort_keys=True, default=str),
                           file_name="completion_pack_v163.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v163_dl_json")
        md = render_completion_pack_markdown(pack)
        st.download_button("Download completion_pack_summary_v163.md",
                           data=md,
                           file_name="completion_pack_summary_v163.md",
                           mime="text/markdown",
                           use_container_width=True,
                           key="v163_dl_md")


# =====================
# v164 Sensitivity + Bottleneck Attribution
# =====================
def _v164_sensitivity_panel():
    import streamlit as st
    from tools.sensitivity_v164 import build_sensitivity_report, render_sensitivity_markdown

    st.subheader("Sensitivity + Bottleneck Attribution")
    st.caption("Local finite-difference sensitivities around a witness: ranked leverage variables and dominant-constraint changes.")

    # Prefer completion pack witness if present, else last run
    pack = st.session_state.get("v163_pack")
    witness = None
    if isinstance(pack, dict):
        witness = ((pack.get("payload") or {}).get("recommended_witness"))
    if not isinstance(witness, dict):
        # fallback to baseline last run
        s = _v98_state_init_runlists()
        runs = [r for r in (s.run_history or []) if r.get("id")]
        if runs:
            payload = (runs[-1].get("payload") or {})
            if isinstance(payload, dict) and payload.get("kind")=="shams_run_artifact":
                witness = payload.get("inputs") or payload.get("_inputs")

    if not isinstance(witness, dict) or not witness:
        st.info("No witness found yet. Run v159/v161/v162 or build v163 completion pack first.")
        return

    st.markdown("### Witness source")
    st.code(f"Using witness keys: {len(witness)}", language="text")

    st.markdown("### Variables to perturb")
    keys=sorted([k for k in witness.keys() if isinstance(k,str)])
    dv = st.multiselect("Select variables", options=keys, default=[k for k in keys if k in ("R0_m","B0_T","q95","kappa")], key="v164_dv")
    default_bounds=_json.dumps([{"name":k, "bounds":[float(witness.get(k,0.0) or 0.0)*0.9, float(witness.get(k,0.0) or 0.0)*1.1+1e-9]} for k in (dv or [])][:10], indent=2)
    st.caption('Bounds JSON example: [{"name":"R0_m","bounds":[2.5,3.5]}, ...]')
    bounds_json = st.text_area("Variable bounds (JSON)", value=default_bounds, height=160, key="v164_bounds")
    assumptions_json = st.text_area("Assumption set (JSON object)", value="{}", height=80, key="v164_assumptions")

    col1,col2=st.columns(2)
    with col1:
        rel_step = st.number_input("Relative step (fraction of span)", value=0.01, min_value=0.001, max_value=0.10, step=0.001, format="%.3f", key="v164_relstep")
    with col2:
        abs_step_min = st.number_input("Absolute step min", value=1e-6, min_value=0.0, max_value=1e-2, step=1e-6, format="%.6f", key="v164_absmin")

    if st.button("Compute Sensitivity", use_container_width=True, key="v164_run"):
        try:
            vars_spec = _json.loads(bounds_json) if bounds_json.strip() else []
            assumptions = _json.loads(assumptions_json) if assumptions_json.strip() else {}
        except Exception as e:
            st.error(f"JSON parse error: {e}")
            return
        with st.spinner("Evaluating baseline and perturbations..."):
            rep = build_sensitivity_report(
                witness=witness,
                variables=vars_spec,
                assumption_set=assumptions if isinstance(assumptions,dict) else {},
                rel_step=float(rel_step),
                abs_step_min=float(abs_step_min),
                policy={"generator":"ui"},
            )
        st.session_state["v164_sensitivity"] = rep
        ranked=((rep.get("payload") or {}).get("ranked") or [])
        st.success(f"Computed. Ranked variables: {len(ranked)}")
        st.markdown("### Ranked leverage (preview)")
        st.json(ranked[:15])
        st.download_button("Download sensitivity_v164.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True, default=str),
                           file_name="sensitivity_v164.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v164_dl_json")
        md = render_sensitivity_markdown(rep)
        st.download_button("Download sensitivity_v164.md",
                           data=md,
                           file_name="sensitivity_v164.md",
                           mime="text/markdown",
                           use_container_width=True,
                           key="v164_dl_md")


# =====================
# v165 Study Protocol Generator
# =====================
def _v165_study_protocol_panel():
    import streamlit as st
    from tools.study_protocol_v165 import build_study_protocol, render_study_protocol_markdown

    st.subheader("Study Protocol Generator")
    st.caption("Generate journal-ready, audit-ready study protocol (Methods) with protocol SHA-256. Reporting-only.")

    s = _v98_state_init_runlists()
    runs = [r for r in (s.run_history or []) if r.get("id")]
    if not runs:
        st.info("Run at least one evaluation first (Point Designer / Systems Mode) to generate a run artifact.")
        return
    ids=[r.get("id") for r in runs]
    run_map={r.get("id"): r for r in runs}
    rid = st.selectbox("Select run artifact", options=ids, index=len(ids)-1, key="v165_run_id")
    run_art = (run_map.get(rid) or {}).get("payload")
    if not (isinstance(run_art, dict) and run_art.get("kind")=="shams_run_artifact"):
        st.error("Selected run is missing shams_run_artifact payload.")
        return

    col1,col2=st.columns(2)
    with col1:
        title = st.text_input("Study title", value="SHAMS Design Study", key="v165_title")
    with col2:
        study_id = st.text_input("Study ID (optional)", value="", key="v165_study_id")

    objective = st.text_area("Objective (paper-ready)", value="Feasibility characterization and completion under explicit constraints.", height=80, key="v165_obj")
    notes = st.text_area("Notes (one per line)", value="", height=60, key="v165_notes")

    st.markdown("### Optional: variables varied / scan definition")
    vars_json = st.text_area("variables_varied (JSON list)", value="[]", height=120, key="v165_vars")
    artifacts_json = st.text_area("artifacts_generated (JSON list)", value='["study_protocol_v165.json","study_protocol_v165.md"]', height=80, key="v165_artifacts")
    seed = st.number_input("Seed (optional)", value=0, min_value=0, max_value=10_000_000, step=1, key="v165_seed")

    if st.button("Generate Study Protocol", use_container_width=True, key="v165_run"):
        try:
            vv = _json.loads(vars_json) if vars_json.strip() else []
            ag = _json.loads(artifacts_json) if artifacts_json.strip() else []
        except Exception as e:
            st.error(f"JSON parse error: {e}")
            return
        overrides={
            "title": title,
            "study_id": study_id,
            "objective": objective,
            "notes": [ln.strip() for ln in notes.splitlines() if ln.strip()],
            "variables_varied": vv if isinstance(vv, list) else [],
            "artifacts_generated": ag if isinstance(ag, list) else [],
            "seed": int(seed),
        }
        prot = build_study_protocol(run_artifact=run_art, protocol_overrides=overrides)
        st.session_state["v165_protocol"] = prot
        sha = ((prot.get("payload") or {}).get("integrity") or {}).get("protocol_sha256")
        st.success(f"Generated. Protocol SHA-256: {sha}")
        st.download_button("Download study_protocol_v165.json",
                           data=_json.dumps(prot, indent=2, sort_keys=True, default=str),
                           file_name="study_protocol_v165.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v165_dl_json")
        md = render_study_protocol_markdown(prot)
        st.download_button("Download study_protocol_v165.md",
                           data=md,
                           file_name="study_protocol_v165.md",
                           mime="text/markdown",
                           use_container_width=True,
                           key="v165_dl_md")


# =====================
# v166 Reproducibility Lock + Replay Checker
# =====================
def _v166_repro_lock_panel():
    import streamlit as st
    from tools.repro_lock_v166 import build_repro_lock, replay_check

    st.subheader("Reproducibility Lock + Replay Checker")
    st.caption("Freeze a run (inputs + assumptions + solver meta) into a lockfile and verify replay matches within tolerances.")

    s = _v98_state_init_runlists()
    runs = [r for r in (s.run_history or []) if r.get("id")]
    if not runs:
        st.info("Run at least one evaluation first (Point Designer / Systems Mode).")
        return
    ids=[r.get("id") for r in runs]
    run_map={r.get("id"): r for r in runs}
    rid = st.selectbox("Select run artifact to lock", options=ids, index=len(ids)-1, key="v166_run_id")
    run_art = (run_map.get(rid) or {}).get("payload")
    if not (isinstance(run_art, dict) and run_art.get("kind")=="shams_run_artifact"):
        st.error("Selected run is missing shams_run_artifact payload.")
        return

    st.markdown("### Tolerances (edit JSON)")
    tol_default = _json.dumps({
        "min_margin_abs": 1e-8,
        "constraint_margin_abs": 1e-6,
        "metric_rel": 1e-6,
        "metric_abs": 1e-9,
    }, indent=2)
    tol_json = st.text_area("tolerances JSON", value=tol_default, height=140, key="v166_tol")

    notes = st.text_area("Notes (one per line)", value="", height=60, key="v166_notes")

    col1,col2=st.columns(2)
    with col1:
        if st.button("Create Lock", use_container_width=True, key="v166_lock"):
            try:
                tol=_json.loads(tol_json) if tol_json.strip() else {}
            except Exception as e:
                st.error(f"JSON parse error: {e}")
                return
            lock = build_repro_lock(run_artifact=run_art, lock_overrides={"tolerances": tol, "notes":[ln.strip() for ln in notes.splitlines() if ln.strip()]})
            st.session_state["v166_lock"] = lock
            sha = ((lock.get("payload") or {}).get("integrity") or {}).get("lock_sha256")
            st.success(f"Lock created. lock_sha256: {sha}")
            st.download_button("Download repro_lock_v166.json",
                               data=_json.dumps(lock, indent=2, sort_keys=True, default=str),
                               file_name="repro_lock_v166.json",
                               mime="application/json",
                               use_container_width=True,
                               key="v166_dl_lock")
    with col2:
        lock_up = st.file_uploader("Or upload existing lock JSON", type=["json"], key="v166_up_lock")

    lock = st.session_state.get("v166_lock")
    if lock_up is not None:
        try:
            lock = _json.loads(lock_up.getvalue().decode("utf-8"))
            st.session_state["v166_lock"] = lock
        except Exception:
            st.warning("Could not parse uploaded lock JSON.")

    st.markdown("### Replay check")
    ao_json = st.text_area("assumption_set override (JSON, optional)", value="{}", height=80, key="v166_ao")
    if st.button("Run Replay Check", use_container_width=True, key="v166_replay"):
        if not isinstance(lock, dict) or lock.get("kind")!="shams_repro_lock":
            st.error("No valid lock loaded. Create or upload a lock first.")
            return
        try:
            ao = _json.loads(ao_json) if ao_json.strip() else {}
        except Exception as e:
            st.error(f"JSON parse error: {e}")
            return
        rep = replay_check(lock=lock, assumption_set_override=ao if isinstance(ao, dict) else None, policy={"generator":"ui"})
        st.session_state["v166_replay"] = rep
        ok = ((rep.get("payload") or {}).get("ok"))
        st.success("Replay OK"if ok else "Replay NOT OK")
        st.json((rep.get("payload") or {}).get("checks") or {})
        st.download_button("Download replay_report_v166.json",
                           data=_json.dumps(rep, indent=2, sort_keys=True, default=str),
                           file_name="replay_report_v166.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v166_dl_rep")


# =====================
# v167 Design Study Authority Pack
# =====================
def _v167_authority_pack_panel():
    import streamlit as st
    from tools.authority_pack_v167 import build_authority_pack

    st.subheader("Design Study Authority Pack")
    st.caption("One downloadable ZIP bundling protocol + lock + replay + completion + sensitivity (+ certificate if available).")

    s = _v98_state_init_runlists()
    runs = [r for r in (s.run_history or []) if r.get("id")]
    if not runs:
        st.info("Run at least one evaluation first (Point Designer / Systems Mode).")
        return
    ids=[r.get("id") for r in runs]
    run_map={r.get("id"): r for r in runs}
    rid = st.selectbox("Select run artifact to include", options=ids, index=len(ids)-1, key="v167_run_id")
    run_art = (run_map.get(rid) or {}).get("payload")
    if not (isinstance(run_art, dict) and run_art.get("kind")=="shams_run_artifact"):
        st.error("Selected run is missing shams_run_artifact payload.")
        return

    st.markdown("### Auto-pick from session state (recommended)")
    prot = st.session_state.get("v165_protocol")
    lock = st.session_state.get("v166_lock")
    replay = st.session_state.get("v166_replay")
    comp = st.session_state.get("v163_pack")
    sens = st.session_state.get("v164_sensitivity")
    cert = st.session_state.get("v160_certificate")

    st.markdown("### Optional: upload any missing JSONs")
    col1,col2,col3 = st.columns(3)
    with col1:
        up_prot = st.file_uploader("upload study_protocol_v165.json", type=["json"], key="v167_up_prot")
        up_lock = st.file_uploader("upload repro_lock_v166.json", type=["json"], key="v167_up_lock")
    with col2:
        up_rep = st.file_uploader("upload replay_report_v166.json", type=["json"], key="v167_up_rep")
        up_comp = st.file_uploader("upload completion_pack_v163.json", type=["json"], key="v167_up_comp")
    with col3:
        up_sens = st.file_uploader("upload sensitivity_v164.json", type=["json"], key="v167_up_sens")
        up_cert = st.file_uploader("upload certificate_v160.json", type=["json"], key="v167_up_cert")

    def _load(up):
        if up is None:
            return None
        try:
            return _json.loads(up.getvalue().decode("utf-8"))
        except Exception:
            return None

    prot = _load(up_prot) or prot
    lock = _load(up_lock) or lock
    replay = _load(up_rep) or replay
    comp = _load(up_comp) or comp
    sens = _load(up_sens) or sens
    cert = _load(up_cert) or cert

    if st.button("Build Authority Pack ZIP", use_container_width=True, key="v167_build"):
        res = build_authority_pack(
            run_artifact=run_art,
            study_protocol_v165=prot,
            repro_lock_v166=lock,
            replay_report_v166=replay,
            completion_pack_v163=comp,
            sensitivity_v164=sens,
            certificate_v160=cert,
            policy={"generator":"ui"},
        )
        st.session_state["v167_manifest"] = res["manifest"]
        st.success(f"Built authority_pack_v167.zip (sha256={res['pack']['integrity']['zip_sha256']})")
        st.json(res["manifest"])
        st.download_button("Download authority_pack_v167.zip",
                           data=res["zip_bytes"],
                           file_name="authority_pack_v167.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v167_dl_zip")


# =====================
# v168 Citation-Grade Study Reference
# =====================
def _v168_citation_panel():
    import streamlit as st
    from tools.citation_v168 import build_citation_bundle

    st.subheader("Citation-Grade Study Reference")
    st.caption("Generate Study ID + CITATION.cff + BibTeX from protocol/lock/authority-pack manifest.")

    prot = st.session_state.get("v165_protocol")
    lock = st.session_state.get("v166_lock")
    manifest = st.session_state.get("v167_manifest")

    st.markdown("### Inputs (auto-pick from session state or upload)")
    col1,col2,col3 = st.columns(3)
    with col1:
        up_prot = st.file_uploader("upload study_protocol_v165.json", type=["json"], key="v168_up_prot")
    with col2:
        up_lock = st.file_uploader("upload repro_lock_v166.json", type=["json"], key="v168_up_lock")
    with col3:
        up_man = st.file_uploader("upload authority_pack_manifest_v167.json", type=["json"], key="v168_up_man")

    def _load(up):
        if up is None:
            return None
        try:
            return _json.loads(up.getvalue().decode("utf-8"))
        except Exception:
            return None

    prot = _load(up_prot) or prot
    lock = _load(up_lock) or lock
    manifest = _load(up_man) or manifest

    st.markdown("### Metadata (optional)")
    title = st.text_input("Title override (optional)", value="", key="v168_title")
    repo_url = st.text_input("Repository/URL (optional)", value="", key="v168_repo")
    doi = st.text_input("DOI (optional)", value="", key="v168_doi")
    author = st.text_input("Author name (optional)", value="SHAMS–FUSION-X Contributors", key="v168_author")

    if st.button("Generate Citation Bundle", use_container_width=True, key="v168_run"):
        if not (isinstance(prot, dict) and prot.get("kind")=="shams_study_protocol"):
            st.error("Need a valid study_protocol_v165.json (generate in v165).")
            return
        meta={
            "title": title or None,
            "repository": repo_url or None,
            "url": repo_url or None,
            "doi": doi or None,
            "authors": [{"name": author}] if author else [{"name":"SHAMS–FUSION-X Contributors"}],
            "version": "v168",
        }
        res = build_citation_bundle(
            study_protocol_v165=prot,
            repro_lock_v166=lock if isinstance(lock, dict) else None,
            authority_pack_manifest_v167=manifest if isinstance(manifest, dict) else None,
            metadata=meta,
        )
        st.session_state["v168_citation"] = res
        sid = ((res.get("payload") or {}).get("study_id"))
        st.success(f"Study ID: {sid}")
        st.download_button("Download citation_bundle_v168.json",
                           data=_json.dumps(res, indent=2, sort_keys=True, default=str),
                           file_name="citation_bundle_v168.json",
                           mime="application/json",
                           use_container_width=True,
                           key="v168_dl_json")
        st.download_button("Download CITATION.cff",
                           data=(res.get("payload") or {}).get("citation_cff_text",""),
                           file_name="CITATION.cff",
                           mime="text/yaml",
                           use_container_width=True,
                           key="v168_dl_cff")
        st.download_button("Download study_citation_v168.bib",
                           data=(res.get("payload") or {}).get("bibtex_text",""),
                           file_name="study_citation_v168.bib",
                           mime="text/plain",
                           use_container_width=True,
                           key="v168_dl_bib")
        st.download_button("Download study_reference_v168.md",
                           data=(res.get("payload") or {}).get("reference_markdown",""),
                           file_name="study_reference_v168.md",
                           mime="text/markdown",
                           use_container_width=True,
                           key="v168_dl_md")


# =====================
# v169 Feasibility Boundary Atlas (figure pack)
# =====================
def _v169_atlas_panel():
    import streamlit as st
    from tools.atlas_v169 import build_atlas_pack

    st.subheader("Feasibility Boundary Atlas")
    st.caption("Generate a publishable atlas-style figure pack with consistent captions and a hash manifest.")

    sens = st.session_state.get("v164_sensitivity")
    st.markdown("### Input")
    up_sens = st.file_uploader("Upload sensitivity_v164.json (optional)", type=["json"], key="v169_up_sens")

    if up_sens is not None:
        try:
            sens = _json.loads(up_sens.getvalue().decode("utf-8"))
        except Exception:
            st.warning("Could not parse uploaded JSON.")

    if not isinstance(sens, dict):
        st.info("Run v164 Sensitivity first (or upload sensitivity_v164.json) to build the initial atlas.")
        return

    if st.button("Build Atlas Pack ZIP", use_container_width=True, key="v169_build"):
        res = build_atlas_pack(sensitivity_v164=sens, policy={"generator":"ui"})
        st.session_state["v169_manifest"] = res["manifest"]
        st.success(f"Built atlas_pack_v169.zip (sha256={res['pack']['integrity']['zip_sha256']})")
        st.json(res["manifest"])
        st.download_button("Download atlas_pack_v169.zip",
                           data=res["zip_bytes"],
                           file_name="atlas_pack_v169.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v169_dl_zip")


# =====================
# v170 SHAMS → external systems codes Downstream Export
# =====================
def _v170_process_export_panel():
    import streamlit as st
    from tools.process_export_v170 import build_process_export_pack

    st.subheader("SHAMS → external systems codes Downstream Export")
    st.caption("Export SHAMS study outputs into transparent (systems-code-inspired) tables, keeping SHAMS as upstream authority.")

    s = _v98_state_init_runlists()
    runs = [r for r in (s.run_history or []) if r.get("id")]
    if not runs:
        st.info("Run at least one evaluation first (Point Designer / Systems Mode).")
        return
    ids=[r.get("id") for r in runs]
    run_map={r.get("id"): r for r in runs}
    rid = st.selectbox("Select run artifact to export", options=ids, index=len(ids)-1, key="v170_run_id")
    run_art = (run_map.get(rid) or {}).get("payload")
    if not (isinstance(run_art, dict) and run_art.get("kind")=="shams_run_artifact"):
        st.error("Selected run is missing shams_run_artifact payload.")
        return

    comp = st.session_state.get("v163_pack")
    cite = st.session_state.get("v168_citation")

    st.markdown("### Optional attachments")
    st.write("- completion_pack_v163.json:", "yes"if isinstance(comp, dict) else "no")
    st.write("- citation_bundle_v168.json:", "yes"if isinstance(cite, dict) else "no")

    if st.button("Build external systems codes Export Pack ZIP", use_container_width=True, key="v170_build"):
        res = build_process_export_pack(
            run_artifact=run_art,
            completion_pack_v163=comp if isinstance(comp, dict) else None,
            citation_bundle_v168=cite if isinstance(cite, dict) else None,
            policy={"generator":"ui"},
        )
        st.session_state["v170_manifest"] = res["manifest"]
        st.success(f"Built process_export_pack_v170.zip (sha256={res['pack']['integrity']['zip_sha256']})")
        st.json(res["manifest"])
        st.download_button("Download process_export_pack_v170.zip",
                           data=res["zip_bytes"],
                           file_name="process_export_pack_v170.zip",
                           mime="application/zip",
                           use_container_width=True,
                           key="v170_dl_zip")


# =====================
# v172 Demo seed + hydration
# =====================
def _v172_demo_loader():
    import streamlit as st
    from tools.demo_seed_v172 import install_demo_bundle
    st.subheader("Demo seed")
    st.caption("Loads synthetic demo artifacts into session state so every panel shows content offline. Not authoritative.")
    col1,col2 = st.columns([1,2])
    with col1:
        if st.button("Load demo artifacts", use_container_width=True, key="v172_load_demo"):
            install_demo_bundle(st.session_state)
            st.success("Demo artifacts loaded into session state.")
    with col2:
        if st.button("Clear demo artifacts", use_container_width=True, key="v172_clear_demo"):
            for k in ["v164_sensitivity","v165_protocol","v166_lock","v166_replay","v167_manifest","v168_citation","v163_pack",
                      "pd_last_outputs","pd_last_artifact","demo_run_artifact"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.success("Demo artifacts cleared.")


# --- Deferred PAM render ---
try:
    if 'pam_placeholder' in globals() and pam_placeholder is not None:
        with pam_placeholder.container():
            _v175_panel_availability_map_panel()
except Exception as _e:
    # Never fail the whole app due to PAM rendering
    try:
        st.warning(f'PAM render failed: {_e}')
    except Exception:
        pass

# --- Render Activity Log late so it includes events logged during this run ---
try:
    _render_activity_log_sidebar()
except Exception:
    pass

_render_footer()