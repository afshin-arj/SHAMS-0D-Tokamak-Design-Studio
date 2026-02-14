#!/usr/bin/env python
"""Tiny local SQLite index for SHAMS artifacts.

Indexes key fields so you can search and compare runs quickly.

Usage:
  python tools/artifact_index.py --db artifacts.db add path/to/artifacts_root
  python tools/artifact_index.py --db artifacts.db query "COE_proxy_USD_per_MWh < 120 AND Q > 10"
"""
from __future__ import annotations
import argparse, json, os, sqlite3, pathlib

SCHEMA = """
CREATE TABLE IF NOT EXISTS artifacts(
  id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  created_utc TEXT,
  input_hash TEXT,
  schema_version INTEGER,
  Q REAL,
  P_e_net_MW REAL,
  COE REAL,
  feasible INTEGER
);
"""

def artifact_id(a: dict) -> str:
    prov = a.get("provenance", {})
    return f"{a.get('input_hash','')}_{prov.get('timestamp_utc','')}_{prov.get('pid','')}"

def add_tree(conn: sqlite3.Connection, root: pathlib.Path) -> int:
    n=0
    for p in root.rglob("shams_run_artifact.json"):
        try:
            a=json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        rid=artifact_id(a) or str(p)
        out=a.get("outputs",{})
        feasible=int(a.get("constraints_summary",{}).get("n_ok",0)==a.get("constraints_summary",{}).get("n",1))
        conn.execute(
            "INSERT OR REPLACE INTO artifacts(id,path,created_utc,input_hash,schema_version,Q,P_e_net_MW,COE,feasible) VALUES(?,?,?,?,?,?,?,?,?)",
            (rid, str(p), a.get("provenance",{}).get("timestamp_utc",""), a.get("input_hash",""), int(a.get("schema_version",0) or 0),
             float(out.get("Q", float('nan'))), float(out.get("P_e_net_MW", out.get("P_net_MW", float('nan')))),
             float(out.get("COE_proxy_USD_per_MWh", float('nan'))), feasible)
        )
        n+=1
    conn.commit()
    return n

def query(conn: sqlite3.Connection, where: str) -> None:
    q="SELECT path,Q,P_e_net_MW,COE,feasible FROM artifacts WHERE " + where + " LIMIT 200"
    for row in conn.execute(q):
        print(row)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    sub=ap.add_subparsers(dest="cmd", required=True)
    a=sub.add_parser("add")
    a.add_argument("root")
    q=sub.add_parser("query")
    q.add_argument("where")
    args=ap.parse_args()

    conn=sqlite3.connect(args.db)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(SCHEMA)

    if args.cmd=="add":
        n=add_tree(conn, pathlib.Path(args.root))
        print(f"Indexed {n} artifacts")
    else:
        query(conn, args.where)

if __name__=="__main__":
    main()
