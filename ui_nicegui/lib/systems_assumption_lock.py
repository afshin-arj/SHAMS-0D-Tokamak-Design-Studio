"""Assumption lock — block solve/precheck when Systems settings drift."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Tuple


def assumption_settings_snapshot(session: Any) -> dict:
    return {
        "targets_overrides": dict(getattr(session, "systems_targets_overrides", {}) or {}),
        "bounds_overrides": dict(getattr(session, "systems_bounds_overrides", {}) or {}),
        "base_overrides": dict(getattr(session, "systems_base_overrides", {}) or {}),
        "inputs_overrides": dict(getattr(session, "systems_inputs_overrides", {}) or {}),
        "use_q": bool(getattr(session, "systems_use_q", False)),
        "use_h": bool(getattr(session, "systems_use_h", False)),
        "use_pnet": bool(getattr(session, "systems_use_pnet", False)),
        "use_pfus": bool(getattr(session, "systems_use_pfus", False)),
        "q_target": float(getattr(session, "systems_q_target", 0)),
        "h_target": float(getattr(session, "systems_h_target", 0)),
        "pnet_target": float(getattr(session, "systems_pnet_target", 0)),
        "pfus_target": float(getattr(session, "systems_pfus_target", 0)),
        "solve_ip": bool(getattr(session, "systems_solve_ip", False)),
        "solve_fg": bool(getattr(session, "systems_solve_fg", False)),
        "solve_paux": bool(getattr(session, "systems_solve_paux", False)),
        "fs_objective": str(getattr(session, "systems_fs_objective", "")),
        "overlay_transport": {
            k: bool((getattr(session, "overlay", {}) or {}).get(k, False))
            for k in (
                "include_transport_contracts_v371",
                "include_transport_envelope_v396",
                "include_profile_proxy_v397",
            )
        },
    }


def assumption_settings_hash(session: Any) -> str:
    payload = assumption_settings_snapshot(session)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]


def check_assumption_lock(session: Any) -> Tuple[bool, str]:
    """Return (ok, message). ok=False blocks precheck/solve."""
    if not bool(getattr(session, "systems_assumption_lock_enabled", False)):
        return True, ""
    locked = str(getattr(session, "systems_assumption_lock_hash", "") or "")
    if not locked:
        return True, ""
    current = assumption_settings_hash(session)
    if current != locked:
        return (
            False,
            "Assumption lock: settings drifted since capture. Re-capture lock on tab 2 or disable lock.",
        )
    return True, ""
