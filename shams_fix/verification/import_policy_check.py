"""
Import policy regression gate.

Goal: prevent old/legacy code paths (e.g. shams_v1941) from re-entering runtime
execution via accidental imports, which can resurrect previously-fixed issues.

This check is deterministic and file-based (no execution of user code).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PREFIXES = (
    "import shams_v1941",
    "from shams_v1941",
)

# Allowed locations (legacy sandbox / archival) if they exist
ALLOW_DIR_FRAGMENTS = (
    str(Path("legacy") / ""),
    str(Path("archive") / ""),
)

def _is_allowed(path: Path) -> bool:
    # Allow imports inside the legacy tree itself or dedicated archival folders
    p = str(path).replace("\\", "/")
    if "shams_v1941/" in p:
        return True
    for frag in ALLOW_DIR_FRAGMENTS:
        if frag.replace("\\", "/") in p:
            return True
    return False

def main() -> int:
    offenders = []
    for p in ROOT.rglob("*.py"):
        if not p.is_file():
            continue
        if _is_allowed(p):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for line_no, line in enumerate(txt.splitlines(), start=1):
            s = line.strip()
            if s.startswith("#"):
                continue
            for pref in FORBIDDEN_PREFIXES:
                if s.startswith(pref):
                    offenders.append((str(p.relative_to(ROOT)), line_no, s))
    if offenders:
        print("IMPORT_POLICY_FAIL: forbidden legacy import(s) detected")
        for f in offenders[:50]:
            print(f"- {f[0]}:{f[1]}: {f[2]}")
        return 2
    print("IMPORT_POLICY_OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
