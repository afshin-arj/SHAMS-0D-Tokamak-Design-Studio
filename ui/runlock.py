# SHAMS global run lock (server-side) to prevent concurrent solver actions.
# This is posture/UX only; it does not modify physics.

from __future__ import annotations
import json, os, time
from typing import Any, Dict, Optional, Tuple

_DEFAULT_TTL_S = 60 * 60 * 2  # 2 hours safety TTL

# Capture the current Streamlit server process start timestamp at import.
# The lock banner can run before Streamlit session_state is initialized,
# so we need a process-level reference time to safely clear stale locks.
_PROCESS_START_TS = time.time()

def _lock_path() -> str:
    # Keep it inside repo root (cwd) so it works across platforms.
    return os.path.join(os.getcwd(), ".shams_runlock.json")

def read_lock() -> Optional[Dict[str, Any]]:
    p = _lock_path()
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None

def _is_expired(lock: Dict[str, Any], ttl_s: int = _DEFAULT_TTL_S) -> bool:
    try:
        t0 = float(lock.get("started_ts", 0.0))
    except Exception:
        return True
    return (time.time() - t0) > ttl_s

def clear_if_expired(ttl_s: int = _DEFAULT_TTL_S, app_start_ts: Optional[float] = None) -> None:
    """Remove stale/expired locks safely.

    - If lock predates this app process start (crash/previous run), clear it.
    - If lock exceeds TTL, clear it.
    """
    lock = read_lock()
    if not lock:
        return
    # If caller didn't provide an app_start_ts yet (common at startup),
    # fall back to the server-process start time captured at import.
    if app_start_ts is None:
        app_start_ts = _PROCESS_START_TS

    
    # Clear locks held by a different OS process (e.g., server restart)
    try:
        lp = lock.get("pid")
        if lp is not None and int(lp) != int(os.getpid()):
            try:
                os.remove(_lock_path())
            except Exception:
                pass
            return
    except Exception:
        pass

# Clear locks from previous app processes
    if app_start_ts is not None:
        try:
            if float(lock.get("started_ts", 0.0)) < float(app_start_ts) - 5.0:
                try:
                    os.remove(_lock_path())
                except Exception:
                    pass
                return
        except Exception:
            pass
    # Clear TTL-expired locks
    if _is_expired(lock, ttl_s=ttl_s):
        try:
            os.remove(_lock_path())
        except Exception:
            pass


def force_clear() -> None:
    """Unconditionally clear the run lock.

    Used by UI self-tests and recovery workflows. This is UX-only and does not
    modify any physics truth.
    """
    try:
        os.remove(_lock_path())
    except Exception:
        pass

def acquire(task_label: str, owner_token: str, app_start_ts: Optional[float] = None) -> bool:
    """Acquire the global lock for a single run sequence."""
    clear_if_expired(app_start_ts=app_start_ts)
    existing = read_lock()
    if existing:
        return False
    lock = {
        "task": task_label,
        "started_ts": time.time(),
        "owner": owner_token,
        "pid": os.getpid(),
    }
    try:
        with open(_lock_path(), "w", encoding="utf-8") as f:
            json.dump(lock, f, indent=2)
        return True
    except Exception:
        return False

def release(owner_token: str) -> None:
    lock = read_lock()
    if not lock:
        return
    if lock.get("owner") != owner_token:
        return
    try:
        os.remove(_lock_path())
    except Exception:
        pass

def status(owner_token: Optional[str] = None, app_start_ts: Optional[float] = None) -> Tuple[bool, Optional[str], Optional[float], bool]:
    """Return (locked, task, started_ts, is_owner)."""
    clear_if_expired(app_start_ts=app_start_ts)
    lock = read_lock()
    if not lock:
        return (False, None, None, False)
    task = str(lock.get("task", "")) if lock.get("task") is not None else ""
    started = float(lock.get("started_ts", 0.0)) if lock.get("started_ts") is not None else 0.0
    is_owner = (owner_token is not None and lock.get("owner") == owner_token)
    return (True, task or None, started or None, is_owner)
