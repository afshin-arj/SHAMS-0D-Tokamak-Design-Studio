"""Scan Lab Freeze QA (release gate).

This script is intended to be run before freezing Scan Lab.

It runs:
  1) Golden regression QA (scripts/run_scanlab_golden_qa.py)
  2) Replay determinism audit (scripts/run_scanlab_replay_audit.py)

It then writes a JSON freeze report to:
  artifacts/freeze_reports/scanlab_freeze_report.json

Exit code 0 => PASS
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return int(proc.returncode), str(proc.stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="REF|REACTOR|ITER", help="Reference preset key")
    args = ap.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out_dir = os.path.join(repo_root, "artifacts", "freeze_reports")
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, "scanlab_freeze_report.json")

    # Capture version
    ver = "unknown"
    try:
        with open(os.path.join(repo_root, "VERSION"), "r", encoding="utf-8") as f:
            ver = f.read().strip().splitlines()[0]
    except Exception:
        pass

    report: dict = {
        "scanlab_freeze_qa": {
            "status": "running",
            "utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "shams_version": ver,
            "preset": args.preset,
            "checks": [],
        }
    }

    # 1) Golden QA
    code, out = _run([sys.executable, os.path.join(repo_root, "scripts", "run_scanlab_golden_qa.py"), "--preset", args.preset])
    report["scanlab_freeze_qa"]["checks"].append(
        {
            "name": "golden_regression",
            "pass": code == 0,
            "returncode": code,
            "output_head": out[:4000],
        }
    )

    # 2) Replay audit
    code2, out2 = _run([sys.executable, os.path.join(repo_root, "scripts", "run_scanlab_replay_audit.py"), "--preset", args.preset])
    report["scanlab_freeze_qa"]["checks"].append(
        {
            "name": "replay_determinism",
            "pass": code2 == 0,
            "returncode": code2,
            "output_head": out2[:4000],
        }
    )

    all_pass = (code == 0) and (code2 == 0)
    report["scanlab_freeze_qa"]["status"] = "pass" if all_pass else "fail"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print(f"Scan Lab Freeze QA: {'PASS' if all_pass else 'FAIL'}")
    print(f"Report: {report_path}")
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
