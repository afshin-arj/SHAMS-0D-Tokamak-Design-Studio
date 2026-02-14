from __future__ import annotations
"""CLI: Repro lock + replay (v166)

Examples:
  # create lock from a run artifact
  python -m tools.cli_repro_lock_v166 lock --run_artifact run_artifact.json --outdir out_v166

  # replay check using lock
  python -m tools.cli_repro_lock_v166 replay --lock out_v166/repro_lock_v166.json --outdir out_v166_replay
"""

import argparse, json
from pathlib import Path
from tools.repro_lock_v166 import build_repro_lock, replay_check

def _load(p: str):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def main() -> int:
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd", required=True)

    ap_lock=sub.add_parser("lock")
    ap_lock.add_argument("--run_artifact", required=True)
    ap_lock.add_argument("--overrides", default=None)
    ap_lock.add_argument("--outdir", default="out_repro_lock_v166")

    ap_rep=sub.add_parser("replay")
    ap_rep.add_argument("--lock", required=True)
    ap_rep.add_argument("--assumptions_override", default=None)
    ap_rep.add_argument("--outdir", default="out_replay_v166")

    args=ap.parse_args()

    if args.cmd=="lock":
        run_art=_load(args.run_artifact)
        overrides=_load(args.overrides) if args.overrides else {}
        lock=build_repro_lock(run_artifact=run_art, lock_overrides=overrides)
        outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
        (outp/"repro_lock_v166.json").write_text(json.dumps(lock, indent=2, sort_keys=True, default=str), encoding="utf-8")
        print("Wrote", outp/"repro_lock_v166.json")
        return 0

    lock=_load(args.lock)
    ao=_load(args.assumptions_override) if args.assumptions_override else None
    rep=replay_check(lock=lock, assumption_set_override=ao, policy={"generator":"cli"})
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"replay_report_v166.json").write_text(json.dumps(rep, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"replay_report_v166.json")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
