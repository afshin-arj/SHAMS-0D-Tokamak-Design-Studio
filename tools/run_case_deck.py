from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from models.inputs import PointInputs
from models.reference_machines import REFERENCE_MACHINES
from solvers.constraint_solver import solve_for_targets
from constraints.constraints import evaluate_constraints
from shams_io.case_deck import CaseDeck
from shams_io.run_artifact import build_run_artifact, write_run_artifact


def _apply_preset_and_updates(deck: CaseDeck) -> PointInputs:
    base = PointInputs.from_dict(next(iter(REFERENCE_MACHINES.values())))
    if deck.base_preset and deck.base_preset in REFERENCE_MACHINES:
        base = PointInputs.from_dict({**base.to_dict(), **REFERENCE_MACHINES[deck.base_preset]})
    d = base.to_dict()
    d.update(deck.inputs or {})
    return PointInputs.from_dict(d)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run a single SHAMS Case Deck (YAML/JSON).")
    ap.add_argument("deck", help="Path to case_deck.yaml/.json")
    ap.add_argument("--out", default="case_out", help="Output directory")
    args = ap.parse_args()

    deck = CaseDeck.from_path(args.deck)
    inp = _apply_preset_and_updates(deck)

    # Solve for targets if provided, else direct point eval through solver with empty targets
    variables: Dict[str, Any] = {}
    for k, v in (deck.variables or {}).items():
        try:
            x0, lo, hi = v
            variables[str(k)] = (float(x0), float(lo), float(hi))
        except Exception:
            continue

    res = solve_for_targets(inp, targets=dict(deck.targets), variables=variables)
    out = res.out or {}
    cons = evaluate_constraints(out)

    resolved = deck.to_resolved_config()
    art = build_run_artifact(
        inputs=dict(inp.__dict__),
        outputs=dict(out),
        constraints=cons,
        meta={"label": deck.label, "mode": "deck"},
        solver={"message": res.message, "trace": res.trace or []},
        decision={"resolved_config": resolved, "resolved_config_sha256": deck.resolved_fingerprint_sha256()},
        calibration=dict(resolved.get("calibration", {}) or {}),
        fidelity=dict(resolved.get("fidelity", {}) or {}),
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_run_artifact(out_dir / "shams_run_artifact.json", art)
    (out_dir / "run_config_resolved.json").write_text(json.dumps(resolved, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Wrote artifact to {out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
