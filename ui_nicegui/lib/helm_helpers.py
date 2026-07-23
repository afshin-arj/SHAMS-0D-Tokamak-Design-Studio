"""Helm Console helpers — Streamlit ui/app.py parity (no Streamlit imports)."""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any, TYPE_CHECKING

from ui_nicegui.bootstrap import repo_root

if TYPE_CHECKING:
    from ui_nicegui.session import DesignSession

try:
    from schema.inputs import PointInputs
except ImportError:
    from src.schema.inputs import PointInputs  # type: ignore

try:
    from schema.governance_presets import apply_governance_preset, tritium_tight_closure_default
except ImportError:
    from src.schema.governance_presets import apply_governance_preset, tritium_tight_closure_default  # type: ignore

try:
    from models.reference_machines import REFERENCE_MACHINES, reference_catalog
except ImportError:
    from src.models.reference_machines import REFERENCE_MACHINES, reference_catalog  # type: ignore

from ui.point_inputs_factory import make_point_inputs
from ui_nicegui.lib.pd_overlay_catalog import ALL_OVERLAY_KEYS
from ui_nicegui.lib.point_inputs_builder import _PRIORITY_OVERLAY_KEYS
from ui_nicegui.session import _DEFAULT_INPUTS

# DesignSession attrs cleared on truth-relevant contract changes (Streamlit parity).
_MODE_CACHE_ATTRS: tuple[str, ...] = (
    "pd_last_outputs",
    "pd_last_artifact",
    "pd_last_log_lines",
    "pd_last_run_ts",
    "pd_last_inputs_hash",
    "pd_last_forensics",
    "pd_verdict_summary_cache",
    "pd_no_solution_atlas_cache",
    "last_eval",
    "systems_last_solve_artifact",
    "scan_cartography_artifact",
    "scan_cartography_report",
    "pareto_last",
    "trade_last",
    "cmp_slot_a",
    "cmp_slot_b",
    "cmp_slot_a_meta",
    "cmp_slot_b_meta",
)
_LIST_CACHE_ATTRS = frozenset({"pd_last_log_lines"})
_DICT_CACHE_ATTRS = frozenset({"cmp_slot_a_meta", "cmp_slot_b_meta"})

_SESSION_INPUT_KEYS = frozenset(_DEFAULT_INPUTS.keys()) | frozenset({
    "Paux_for_Q_MW",
    "use_lambda_q",
    "profile_model",
    "profile_mode",
    "require_Hmode",
    "confinement_model",
    "include_secondary_DT",
    "tritium_retention",
    "tau_T_loss_s",
})

_OVERLAY_KEYS = frozenset(ALL_OVERLAY_KEYS) | frozenset(_PRIORITY_OVERLAY_KEYS)


def verification_report_paths() -> tuple[str, str, str, str]:
    """Return (report.json, SHAMS_REQS.yaml, SHAMS_REQS.json, run_verification.py) paths."""
    root = repo_root()
    rep = os.path.join(root, "verification", "report.json")
    reqs = os.path.join(root, "requirements", "SHAMS_REQS.yaml")
    reqs_json = os.path.join(root, "requirements", "SHAMS_REQS.json")
    runner = os.path.join(root, "verification", "run_verification.py")
    return rep, reqs, reqs_json, runner


def verification_needs_run() -> bool:
    """True when verification report is missing or older than requirements/runner deps."""
    rep, reqs, reqs_json, runner = verification_report_paths()
    if not os.path.exists(rep):
        return True
    try:
        rep_m = os.path.getmtime(rep)
        deps = [p for p in (reqs, reqs_json, runner) if os.path.exists(p)]
        if not deps:
            return False
        dep_m = max(os.path.getmtime(p) for p in deps)
        return rep_m < dep_m
    except Exception:
        return False


def run_verification_capture() -> tuple[bool, str, str, float]:
    """Run verification/run_verification.py; return (ok, stdout, stderr, seconds)."""
    import time

    rep, _, _, runner = verification_report_paths()
    t0 = time.time()
    if not os.path.exists(runner):
        return False, "", f"Missing verification runner: {runner}", 0.0
    try:
        proc = subprocess.run(
            [sys.executable, runner],
            cwd=repo_root(),
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


def health_snapshot_rows() -> list[dict[str, str]]:
    """Instant health checks (no subprocess): Python, manifest, benchmarks, write probe."""
    rows: list[dict[str, str]] = []
    root = repo_root()

    try:
        rows.append({
            "Check": "Python",
            "Status": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        })
    except Exception:
        rows.append({"Check": "Python", "Status": "unknown"})

    try:
        repo_ok = os.path.exists(os.path.join(root, "MANIFEST_SHA256.txt"))
        rows.append({"Check": "Repo manifest", "Status": "present" if repo_ok else "missing"})
    except Exception:
        rows.append({"Check": "Repo manifest", "Status": "unknown"})

    try:
        out_dir = os.path.join(root, "benchmarks", "publication")
        rows.append({
            "Check": "Benchmarks folder",
            "Status": "present" if os.path.isdir(out_dir) else "missing",
        })
    except Exception:
        rows.append({"Check": "Benchmarks folder", "Status": "unknown"})

    try:
        probe_dir = os.path.join(root, ".shams_probe")
        os.makedirs(probe_dir, exist_ok=True)
        probe_file = os.path.join(probe_dir, "write_test.txt")
        with open(probe_file, "w", encoding="utf-8") as f:
            f.write("ok")
        rows.append({"Check": "Write access", "Status": "ok"})
    except Exception:
        rows.append({"Check": "Write access", "Status": "blocked"})

    return rows


def _activity_logger(session: "DesignSession"):
    from tools.activity_log import ActivityLogger

    lg = getattr(session, "_activity_logger", None)
    if lg is None:
        lg = ActivityLogger(repo_root=Path(repo_root()), tz_name="Asia/Tehran")
        session._activity_logger = lg
        if not getattr(session, "_activity_log_inited", False):
            session._activity_log_inited = True
            try:
                if bool(getattr(session, "activity_log_auto", True)):
                    lg.log_event("UI", "LogInitialized", {"tz": "Asia/Tehran"})
            except Exception:
                pass
    return lg


def log_ui_event(session: "DesignSession", kind: str, action: str, payload: dict | None = None) -> None:
    """Append one activity-log event when auto-logging is enabled."""
    try:
        if bool(getattr(session, "activity_log_auto", True)):
            _activity_logger(session).log_event(kind, action, payload or {})
    except Exception:
        pass


def invalidate_mode_caches(session: "DesignSession", reason: str = "") -> None:
    """Clear cached outputs/artifacts across modes when a truth-relevant UI contract changes."""
    try:
        for attr in _MODE_CACHE_ATTRS:
            if not hasattr(session, attr):
                continue
            if attr in _LIST_CACHE_ATTRS:
                setattr(session, attr, [])
            elif attr in _DICT_CACHE_ATTRS:
                setattr(session, attr, {})
            else:
                setattr(session, attr, None)
        if reason:
            session.ui_last_invalidation_reason = str(reason)
    except Exception:
        pass


def on_design_intent_changed(session: "DesignSession", prev: str, new: str) -> None:
    """Handle design-intent change: invalidate caches, apply governance preset, log."""
    if str(prev) == str(new):
        return
    session.design_intent = str(new)
    invalidate_mode_caches(session, "design_intent_changed")
    try:
        pi = session.build_point_inputs()
        field_dict = asdict(pi) if hasattr(pi, "__dataclass_fields__") else dict(pi)
        apply_governance_preset(field_dict, design_intent=str(new))
        session.overlay["include_tritium_tight_closure"] = bool(
            field_dict.get(
                "include_tritium_tight_closure",
                tritium_tight_closure_default(str(new)),
            )
        )
    except Exception:
        pass
    log_ui_event(session, "UI", "DesignIntentChanged", {"from": prev, "to": new})


def on_policy_contract_changed(session: "DesignSession") -> None:
    """Invalidate caches when q95/Greenwald enforcement tiering changes."""
    invalidate_mode_caches(session, "policy_contract_changed")


def on_tech_tier_changed(session: "DesignSession") -> None:
    """Invalidate caches when TRL tier changes."""
    invalidate_mode_caches(session, "tech_tier_changed")


def _route_point_field(key: str) -> str:
    """Return target dict name: inputs, overlay, or knobs."""
    if key in _OVERLAY_KEYS:
        return "overlay"
    if key in _SESSION_INPUT_KEYS:
        return "inputs"
    return "knobs"


def push_point_inputs_to_session(session: "DesignSession", base: Any) -> None:
    """Merge a PointInputs instance into session.inputs/knobs/overlay; sync solver bounds."""
    if base is None:
        return
    try:
        data = asdict(base) if hasattr(base, "__dataclass_fields__") else dict(base)
    except Exception:
        return

    valid = {f.name for f in fields(PointInputs)}
    for key, value in data.items():
        if key not in valid:
            continue
        target = _route_point_field(key)
        dest = getattr(session, target)
        dest[key] = value

    # Mirror Streamlit _push_point_inputs_to_pd_widget_keys solver-bound sync.
    try:
        ip = float(data.get("Ip_MA", getattr(base, "Ip_MA", 0.0)))
        session.pd_ip_min = max(0.1, 0.80 * ip)
        session.pd_ip_max = max(0.2, 1.20 * ip)
    except Exception:
        pass
    try:
        fg = float(data.get("fG", getattr(base, "fG", 0.0)))
        session.pd_fg_min = max(0.0, fg - 0.20)
        session.pd_fg_max = min(2.0, fg + 0.20)
    except Exception:
        pass
    try:
        paux = float(data.get("Paux_MW", getattr(base, "Paux_MW", 0.0)))
        session.inputs["Paux_for_Q_MW"] = paux
    except Exception:
        pass


def apply_reference_preset_to_session(session: "DesignSession", ref_key: str) -> None:
    """Load a catalog reference preset into the NiceGUI session."""
    cat = reference_catalog()
    if ref_key not in cat:
        raise KeyError(f"Unknown reference preset: {ref_key}")
    ent = cat[ref_key]
    base = ent.get("inputs")
    if base is None:
        raise ValueError(f"Reference preset missing inputs: {ref_key}")

    intent = str(ent.get("intent", "")).strip().lower()
    if intent.startswith("research"):
        session.design_intent = "Experimental Device (research)"
    elif intent:
        session.design_intent = "Power Reactor (net-electric)"

    push_point_inputs_to_session(session, base)


def force_clear_stuck_runs(session: "DesignSession") -> list[str]:
    """Operator recovery: reset orphaned busy flags + the global run lock.

    A background task can be orphaned if its owning coroutine never reaches its
    ``finally`` release (client disconnect, hard crash in a worker thread). When
    that happens every deck reads "busy" forever with no in-UI way to recover
    short of restarting the process. This clears every ``*_running``/``evaluating``
    dataclass field on the session plus the module-level run lock, and bumps the
    write-fence epoch so zombie workers discard results (WRITE-FENCE-001). It never
    touches physics state (inputs/outputs/artifacts are untouched).
    """
    from ui_nicegui.lib import run_lock

    cleared: list[str] = []
    # Include Forge compile/audit flags that do not end in ``_running`` but still
    # trip FORGE_RUNNING_ATTRS remount guards (Helm force-clear recovery).
    _extra_busy = ("forge_compiling", "forge_auditing")
    for f in fields(session):
        name = f.name
        if name != "evaluating" and not name.endswith("_running") and name not in _extra_busy:
            continue
        if bool(getattr(session, name, False)):
            setattr(session, name, False)
            cleared.append(name)
    holder = run_lock.force_clear()
    if holder:
        cleared.append(f"run_lock[{holder}]")
    log_ui_event(session, "UI", "ForceClearStuckRuns", {"cleared": cleared})
    return cleared


def apply_legacy_reference_machine_to_session(session: "DesignSession", name: str) -> None:
    """Load legacy REFERENCE_MACHINES entry into the NiceGUI session."""
    if name not in REFERENCE_MACHINES:
        raise KeyError(f"Unknown legacy preset: {name}")
    d = dict(REFERENCE_MACHINES[name] or {})
    try:
        base = make_point_inputs(**d)
    except Exception as e:
        raise ValueError(f"Legacy preset could not be converted to PointInputs: {name} ({e})") from e
    push_point_inputs_to_session(session, base)
