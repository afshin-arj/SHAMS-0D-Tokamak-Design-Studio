from __future__ import annotations
"""CLI: Run Integrity Lock (v152)

Lock:
  python -m tools.cli_run_integrity_lock lock --artifact artifact.json --run_id r1 --outdir out_lock
Verify:
  python -m tools.cli_run_integrity_lock verify --artifact artifact.json --lock out_lock/run_integrity_lock_v152.json
"""

import argparse, json
from pathlib import Path
from tools.run_integrity_lock import lock_run, verify_run

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["lock","verify"])
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--run_id", default="run")
    ap.add_argument("--lock", default="")
    ap.add_argument("--outdir", default="out_run_integrity_v152")
    args=ap.parse_args()

    art=json.loads(Path(args.artifact).read_text(encoding="utf-8"))
    if args.cmd=="lock":
        out=lock_run(args.run_id, art, extras=None, policy={"source":"cli"})
        outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
        (outp/"run_integrity_lock_v152.json").write_text(json.dumps(out["lock"], indent=2, sort_keys=True, default=str), encoding="utf-8")
        print("Wrote", outp/"run_integrity_lock_v152.json")
        return 0
    lock=json.loads(Path(args.lock).read_text(encoding="utf-8"))
    rep=verify_run(lock, art, extras=None)
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"run_integrity_verify_v152.json").write_text(json.dumps(rep, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("OK" if rep.get("ok") else "FAILED")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
