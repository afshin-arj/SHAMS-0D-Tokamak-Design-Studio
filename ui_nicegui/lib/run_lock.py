"""Global UX run lock — prevents overlapping long evaluations across decks.

Non-reentrant: the same owner cannot acquire twice. A successful acquire must be
paired with ``release(owner, lease=...)`` from that owner (or ``force_clear`` for
orphan recovery).

WRITE-FENCE-001: ``force_clear`` bumps an epoch. Workers snapshot ``current_lease()``
immediately after acquire; if the lease is no longer valid they must skip session
artifact writes, ``on_complete`` remounts, and ``release`` so a zombie cannot steal
a newer holder's lock or clobber newer results.

HELM-BUSY-001: every successful acquire / release / force_clear paints Helm status
+ run-lock banner immediately so the header never stays "Ready" while a shot is
in progress.
"""
from __future__ import annotations

import threading
from typing import Optional, Tuple

_lock = threading.Lock()
_holder: Optional[str] = None
_task: Optional[str] = None
_epoch: int = 0
_holder_lease: Optional[int] = None


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
    """Acquire the global run lock. Fails if any holder exists (including same owner).

    On success, call ``current_lease()`` immediately and pass that lease to
    ``release`` / gate writes with ``lease_valid``.
    """
    global _holder, _task, _holder_lease
    with _lock:
        if _holder is not None:
            return False
        _holder = owner
        _task = task
        _holder_lease = _epoch
    _paint_busy_chrome()
    return True


def current_lease() -> Optional[int]:
    """Lease epoch of the current holder (call immediately after a successful acquire)."""
    with _lock:
        return _holder_lease


def lease_valid(lease: Optional[int]) -> bool:
    """True when ``lease`` still matches the global epoch (not force-cleared)."""
    if lease is None:
        return False
    with _lock:
        return lease == _epoch


def epoch() -> int:
    """Current write-fence epoch (increments on every force_clear)."""
    with _lock:
        return _epoch


def release(owner: str, lease: Optional[int] = None) -> bool:
    """Release the lock for ``owner``.

    When ``lease`` is provided (preferred), a zombie whose epoch was invalidated by
    ``force_clear`` will not unlock a newer holder. Returns True if the lock was cleared.
    """
    global _holder, _task, _holder_lease
    painted = False
    with _lock:
        if lease is not None and lease != _epoch:
            return False
        if _holder == owner:
            _holder = None
            _task = None
            _holder_lease = None
            painted = True
    if painted:
        _paint_busy_chrome()
    return painted


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
    """Unconditionally release the lock and bump the write-fence epoch.

    Use only after orphan confirmation (Helm). In-flight workers that snapshotted
    a lease before the bump must discard results and skip ``release``.
    Returns the holder that was cleared, or ``None`` if the lock was already free.
    """
    global _holder, _task, _holder_lease, _epoch
    with _lock:
        prev = _holder
        _holder = None
        _task = None
        _holder_lease = None
        _epoch += 1
    _paint_busy_chrome()
    return prev
