"""Global UX run lock — prevents overlapping long evaluations across decks.

Non-reentrant: the same owner cannot acquire twice. A successful acquire must be
paired with ``release(owner)`` from that owner (or ``force_clear`` for orphan recovery).

HELM-BUSY-001: every successful acquire / release / force_clear paints Helm status
+ run-lock banner immediately so the header never stays "Ready" while a shot is
in progress (Forge / Scan / Systems / Pareto / Pub previously refreshed only in
``finally``, leaving Ready visible for the whole run).
"""
from __future__ import annotations

import threading
from typing import Optional, Tuple

_lock = threading.Lock()
_holder: Optional[str] = None
_task: Optional[str] = None


def _paint_busy_chrome() -> None:
    """Best-effort Helm busy/ready refresh (no-op when UI hooks are unregistered)."""
    try:
        from ui_nicegui.lib.navigation import refresh_helm, refresh_status

        refresh_status()
        refresh_helm()
    except Exception:
        # Headless tests / pre-UI import paths must never fail lock bookkeeping.
        pass


def acquire(task: str, owner: str) -> bool:
    """Acquire the global run lock. Fails if any holder exists (including same owner)."""
    global _holder, _task
    with _lock:
        if _holder is not None:
            return False
        _holder = owner
        _task = task
    _paint_busy_chrome()
    return True


def release(owner: str) -> None:
    global _holder, _task
    painted = False
    with _lock:
        if _holder == owner:
            _holder = None
            _task = None
            painted = True
    if painted:
        _paint_busy_chrome()


def status(owner: str) -> Tuple[bool, Optional[str], bool]:
    with _lock:
        if _holder is None:
            return False, None, False
        return True, _task, _holder == owner


def global_status() -> Tuple[bool, Optional[str], Optional[str]]:
    """Return (locked, task_label, holder_owner_id)."""
    with _lock:
        if _holder is None:
            return False, None, None
        return True, _task, _holder


def force_clear() -> Optional[str]:
    """Unconditionally release the lock (operator recovery from an orphaned holder).

    Use only when a background task's owning coroutine can no longer reach its
    ``finally: release(...)`` (e.g. a disconnected client mid-run). Returns the
    holder that was cleared, or ``None`` if the lock was already free.
    """
    global _holder, _task
    with _lock:
        prev = _holder
        _holder = None
        _task = None
    if prev is not None:
        _paint_busy_chrome()
    return prev
