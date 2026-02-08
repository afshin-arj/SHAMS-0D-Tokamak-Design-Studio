from __future__ import annotations
"""CLI: Run Vault (v130)

List recent vault entries:
  python -m tools.cli_run_vault --list

Write an entry from a JSON file:
  python -m tools.cli_run_vault --write-json run_artifact.json --kind run_artifact

"""

import argparse, json
from pathlib import Path
from tools.run_vault import list_entries, write_entry

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Repo root containing out_run_vault")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--write-json", default=None, help="Write entry from JSON file")
    ap.add_argument("--kind", default="run")
    ap.add_argument("--mode", default="")
    args = ap.parse_args()

    root = Path(args.root).resolve()

    if args.list:
        ent = list_entries(root, limit=args.limit)
        for e in ent:
            print(e.get("created_utc"), e.get("record_kind"), e.get("mode"), e.get("entry_dir"), e.get("sha256")[:10])
        return 0

    if args.write_json:
        obj = json.loads(Path(args.write_json).read_text(encoding="utf-8"))
        meta = write_entry(root=root, kind=args.kind, payload=obj, mode=args.mode)
        print("Wrote entry", meta.get("entry_dir"))
        return 0

    print("Nothing to do. Use --list or --write-json.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
