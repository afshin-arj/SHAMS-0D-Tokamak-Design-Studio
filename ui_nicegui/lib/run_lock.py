"""Global UX run lock — prevents overlapping long evaluations across decks."""
from __future__ import annotations

import threading
from typing import Optional, Tuple

_lock = threading.Lock()
_holder: Optional[str] = None
_task: Optional[str] = None


def acquire(task: str, owner: str) -> bool:
    global _holder, _task
    with _lock:
        if _holder is not None and _holder != owner:
            return False
        _holder = owner
        _task = task
        return True


def release(owner: str) -> None:
    global _holder, _task
    with _lock:
        if _holder == owner:
            _holder = None
            _task = None


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
