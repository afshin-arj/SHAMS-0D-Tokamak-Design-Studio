"""Tiny SHAMS UI self-test (run-lock sanity).

Run:
  python ui_selftest.py

This does NOT start Streamlit. It only validates that the global run-lock
file can be force-cleared, acquired, reported, and released.

Exit code 0 = PASS.
"""

import os
import sys
import time

# Import from UI package path
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ui import runlock  # type: ignore


def main() -> int:
    owner = f"selftest-{os.getpid()}"
    runlock.force_clear()

    ok = runlock.acquire(task_label="Selftest", owner_token=owner, app_start_ts=time.time())
    if not ok:
        print("FAIL: could not acquire lock") 
        return 2

    locked, task, started, is_owner = runlock.status(owner_token=owner, app_start_ts=time.time())
    if not locked or not is_owner or (task != "Selftest"):
        print("FAIL: status mismatch", locked, task, is_owner)
        runlock.force_clear()
        return 3

    runlock.release(owner_token=owner)
    locked2, task2, started2, is_owner2 = runlock.status(owner_token=owner, app_start_ts=time.time())
    if locked2:
        print("FAIL: lock still present after release")
        runlock.force_clear()
        return 4

    print("PASS: run-lock acquire/status/release") 
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
