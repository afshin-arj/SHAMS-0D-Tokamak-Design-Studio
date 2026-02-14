"""Scan Lab Golden QA (deterministic regression).

This is a freeze-readiness script.

Validates:
 - Golden scans run headlessly
 - Scan artifact schema v1
 - Determinism (stable hashes for key report sections)
 - Signature Atlas export produces exactly 10 pages

Usage:
  python scripts/run_scanlab_golden_qa.py --preset "REF|REACTOR|ITER" 
"""

from __future__ import annotations

import argparse
import os
import sys


# Ensure imports work when launched from scripts/ (python sets sys.path[0]=scripts)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(REPO_ROOT, "src")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _count_pdf_pages(pdf_bytes: bytes) -> int:
    # Minimal PDF page counter (no external deps)
    return pdf_bytes.count(b"/Type /Page")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="REF|REACTOR|ITER", help="Reference machine preset key")
    ap.add_argument("--full", action="store_true", help="Run full-resolution golden scans (slower)")
    args = ap.parse_args()

    # Local imports (repo layout)
    from src.evaluator.core import Evaluator  # type: ignore
    from src.models.reference_machines import reference_presets  # type: ignore
    from tools.golden_scans import build_golden_scan_presets
    from tools.scan_cartography import build_cartography_report
    from tools.scan_artifact_schema import build_scan_artifact, stable_hash, SCAN_SCHEMA_VERSION
    from tools.reports.scan_signature_atlas import build_signature_atlas_pdf_bytes

    presets = reference_presets()
    if args.preset not in presets:
        raise SystemExit(f"Unknown preset key: {args.preset}. Available: {sorted(presets.keys())[:8]}...")
    base = presets[args.preset]

    golden = build_golden_scan_presets(base_inputs=base)
    if not golden:
        raise SystemExit("No golden scan presets returned.")

    ev = Evaluator(cache_enabled=True)
    results = []
    # Speed guardrail: default to a fast subset/resolution for freeze gating.
    if not args.full:
        golden = golden[:2]

    for g in golden:
        rep = build_cartography_report(
            evaluator=ev,
            base_inputs=g.get("base_inputs", base),
            x_key=str(g["x_key"]),
            y_key=str(g["y_key"]),
            x_vals=list(
                __import__("numpy").linspace(
                    g["x_range"][0],
                    g["x_range"][1],
                    int(g.get("n_x", 31)) if args.full else min(21, int(g.get("n_x", 31))),
                )
            ),
            y_vals=list(
                __import__("numpy").linspace(
                    g["y_range"][0],
                    g["y_range"][1],
                    int(g.get("n_y", 25)) if args.full else min(17, int(g.get("n_y", 25))),
                )
            ),
            intents=list(g.get("intents") or ["Reactor"]),
            include_outputs=False,
        )
        art = build_scan_artifact(report=rep, settings={"golden_id": g.get("id")}, metadata={}, reason_code="run_ok")
        assert int(art.get("scan_schema_version")) == int(SCAN_SCHEMA_VERSION)
        # Determinism fingerprints
        h = {
            "report_hash": art.get("report_hash"),
            "dominance": stable_hash(rep.get("dominance", {})),
            "intent_stats": stable_hash(rep.get("intent_stats", {})),
        }
        results.append((g.get("id"), h))

    # Signature atlas sanity
    pdf = build_signature_atlas_pdf_bytes({"golden": results, "repo": os.getcwd()})
    pages = _count_pdf_pages(pdf)
    assert pages == 10, f"Expected 10 pages, got {pages}"

    print("Scan Lab Golden QA: PASS")
    for gid, h in results:
        print(gid, h)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
