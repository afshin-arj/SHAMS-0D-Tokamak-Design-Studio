
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable, List, Optional

class PanelState(Enum):
    AVAILABLE = auto()
    NOT_GENERATED = auto()
    BLOCKED = auto()
    NOT_APPLICABLE = auto()
    DEMO_SUBSTITUTED = auto()

@dataclass
class PanelStatus:
    state: PanelState
    message: str
    missing: List[str] | None = None
    action: str | None = None

def default_status() -> PanelStatus:
    return PanelStatus(
        state=PanelState.NOT_GENERATED,
        message="This panel has not been generated yet.",
        missing=None,
        action=None
    )

def status_from_requirements(title: str, missing: List[str], notes: str="") -> PanelStatus:
    msg = f"**{title}** is not available yet because required artifacts are missing."
    if notes:
        msg += f"\n\n{notes}"
    return PanelStatus(
        state=PanelState.NOT_GENERATED,
        message=msg,
        missing=missing,
        action=None
    )

def status_blocked(title: str, reason: str) -> PanelStatus:
    return PanelStatus(
        state=PanelState.BLOCKED,
        message=f"**{title}** is blocked. {reason}",
        missing=None,
        action=None
    )

def evaluate_contract(contract, session_state: dict) -> PanelStatus:
    # contract: ui.panel_contracts.PanelContract
    missing = [k for k in (contract.requires or []) if k not in session_state]
    if missing:
        return status_from_requirements(contract.title, missing, notes=contract.notes)
    # blocked keys
    for k in (contract.blocked_if_true_keys or []):
        try:
            if bool(session_state.get(k, False)):
                return status_blocked(contract.title, f"Blocking condition `{k}` is true.")
        except Exception:
            continue
    return PanelStatus(state=PanelState.AVAILABLE, message=f"**{contract.title}** available.")
