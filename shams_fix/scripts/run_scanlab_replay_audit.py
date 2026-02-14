"""Scan Lab replay audit (determinism).

Runs a small scan twice with identical settings and compares stable hashes.

Exit code 0 => PASS.
"""

from __future__ import annotations

import argparse
import os
import sys


# Ensure imports work when launched from scripts/
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(REPO_ROOT, "src")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="REF|REACTOR|ITER", help="Reference preset key")
    ap.add_argument("--nx", type=int, default=11)
    ap.add_argument("--ny", type=int, default=9)
    ap.add_argument("--x_key", default="Ip_MA")
    ap.add_argument("--y_key", default="R0_m")
    args = ap.parse_args()

    import numpy as np
    from src.evaluator.core import Evaluator
    from src.models.reference_machines import reference_presets
    from tools.scan_cartography import build_cartography_report
    from tools.scan_artifact_schema import stable_hash

    base = reference_presets()[args.preset]
    bx = float(getattr(base, args.x_key, 1.0))
    by = float(getattr(base, args.y_key, 1.0))

    x_vals = list(np.linspace(0.9 * bx, 1.1 * bx, int(args.nx)))
    y_vals = list(np.linspace(0.9 * by, 1.1 * by, int(args.ny)))

    ev = Evaluator(cache_enabled=True)

    rep1 = build_cartography_report(evaluator=ev, base_inputs=base, x_key=args.x_key, y_key=args.y_key, x_vals=x_vals, y_vals=y_vals, intents=["Reactor"])
    rep2 = build_cartography_report(evaluator=ev, base_inputs=base, x_key=args.x_key, y_key=args.y_key, x_vals=x_vals, y_vals=y_vals, intents=["Reactor"])

    h1 = {
        "report": stable_hash(rep1),
        "dominance": stable_hash(rep1.get("dominance", {})),
        "intent_stats": stable_hash(rep1.get("intent_stats", {})),
    }
    h2 = {
        "report": stable_hash(rep2),
        "dominance": stable_hash(rep2.get("dominance", {})),
        "intent_stats": stable_hash(rep2.get("intent_stats", {})),
    }

    if h1 != h2:
        print("Replay audit: FAIL")
        print("h1", h1)
        print("h2", h2)
        return 2

    print("Replay audit: PASS", h1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
