#!/usr/bin/env python
from __future__ import annotations
import json
import os
from pathlib import Path
import sys

def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    p = repo / "benchmarks" / "last_diff_report.json"
    if not p.exists():
        print("No benchmarks/last_diff_report.json found. Run `python benchmarks/run.py` first.")
        return 2

    data = json.loads(p.read_text(encoding="utf-8"))
    sev = data.get("structural_severity") or {}
    findings = []
    for case, items in sev.items():
        for it in (items or []):
            if (it.get("severity") or "").lower() == "breaking":
                findings.append((case, it))

    ack = os.environ.get("SHAMS_ACK_BREAKING", "").strip().lower() in ("1","true","yes","y")
    if findings and not ack:
        print("BREAKING structural diffs detected (CI failing).")
        for case, it in findings[:50]:
            print(f"- {case}: {it.get('reason','(no reason)')}")
        print("\nIf this is intentional, re-run CI with env var SHAMS_ACK_BREAKING=1 and include approval in artifacts.")
        return 1

    if findings and ack:
        # Require explicit approval artifact for auditability.
        ap = repo / "benchmarks" / "breaking_approval.json"
        if not ap.exists():
            print("SHAMS_ACK_BREAKING=1 set, but benchmarks/breaking_approval.json is missing.")
            print("Run: python tools/make_breaking_approval.py (after python benchmarks/run.py)")
            return 1
        try:
            appr = json.loads(ap.read_text(encoding="utf-8"))
            want = data.get("diff_report_sha256") or data.get("last_diff_report_sha256") or None
            got = appr.get("diff_report_sha256")
            if want and got and str(want) != str(got):
                print("breaking_approval.json does not match last_diff_report.json sha256.")
                print(f"  expected={want}")
                print(f"  got={got}")
                return 1
        except Exception as e:
            print(f"Failed to read/validate breaking_approval.json: {e}")
            return 1
        print("BREAKING structural diffs detected BUT acknowledged + approved. Proceeding.")
    else:
        print("No breaking structural diffs detected.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
