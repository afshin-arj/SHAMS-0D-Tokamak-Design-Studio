"""Audit user-facing version tags in UI strings."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAT = re.compile(
    r'["\']([^"\']*(?:\(v\d+|Batch \d|Phase \d|Tier[\s\-–]+\d|schema v\d+| v\d+:|v\d+ authority|v\d+\.\d+)[^"\']*)["\']',
    re.IGNORECASE,
)

paths = list((ROOT / "ui").rglob("*.py")) + list((ROOT / "ui_nicegui").rglob("*.py"))
found: set[str] = set()
for p in paths:
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    for m in PAT.finditer(text):
        s = m.group(1)
        if len(s) < 250 and not s.startswith("key="):
            found.add(s)

for s in sorted(found):
    print(s)
print("---TOTAL---", len(found))
