from __future__ import annotations

"""Explain delta between two Publication Benchmark packs (B2).

Usage:
  python benchmarks/publication/explain_delta.py --baseline <dirA> --candidate <dirB> --out <dirB/delta.md>

This tool is deterministic and reviewer-friendly:
- It compares the benchmark CSVs and (when available) per-case artifacts.
- It highlights verdict changes, dominant constraint changes, and key numeric deltas.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _to_float(x: Any) -> float | None:
    try:
        if x is None:
            return None
        s = str(x).strip()
        if s == "" or s.lower() in {"nan","none","n/a"}:
            return None
        return float(s)
    except Exception:
        return None


def _key(row: Dict[str, Any]) -> str:
    return f"{row.get('case_id','')}.{row.get('intent_key','')}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    bdir = Path(args.baseline).resolve()
    cdir = Path(args.candidate).resolve()
    bout = Path(args.out).resolve() if args.out else (cdir / "delta.md")

    bcsv = bdir / "point_designer_benchmark_table.csv"
    ccsv = cdir / "point_designer_benchmark_table.csv"
    if not bcsv.exists() or not ccsv.exists():
        raise SystemExit("Both packs must contain point_designer_benchmark_table.csv")

    brow = { _key(r): r for r in _read_csv(bcsv) }
    crow = { _key(r): r for r in _read_csv(ccsv) }

    keys = sorted(set(brow.keys()) | set(crow.keys()))
    lines: List[str] = []
    lines.append("# Publication Benchmark Delta\n")
    lines.append(f"Baseline: {bdir}\n")
    lines.append(f"Candidate: {cdir}\n")

    channels = ["H98","Q_DT_eqv","P_fus_MW","P_e_net_MW","q95","fG","betaN","q_div_MW_m2","TBR","CAPEX_$","recirc_frac","worst_hard_margin"]

    changed = 0
    for k in keys:
        b = brow.get(k)
        c = crow.get(k)
        if not b or not c:
            continue
        vb = str(b.get("ok_blocking","")) 
        vc = str(c.get("ok_blocking","")) 
        dom_b = str(b.get("dominant_constraint","")) 
        dom_c = str(c.get("dominant_constraint","")) 
        if vb != vc or dom_b != dom_c:
            changed += 1
            lines.append(f"## {k}\n")
            lines.append(f"- Verdict: {vb} → {vc}\n")
            if dom_b != dom_c:
                lines.append(f"- Dominant constraint: {dom_b} → {dom_c}\n")
            # numeric deltas
            deltas: List[str] = []
            for ch in channels:
                bv = _to_float(b.get(ch))
                cv = _to_float(c.get(ch))
                if bv is None or cv is None:
                    continue
                d = cv - bv
                if abs(d) > 0:
                    deltas.append(f"  - d{ch} = {d:.6g} ({bv:.6g} → {cv:.6g})")
            if deltas:
                lines.append("- Key deltas:\n" + "\n".join(deltas) + "\n")
            lines.append("\n")

    if changed == 0:
        lines.append("No verdict or dominant-constraint changes detected between packs.\n")

    bout.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {bout}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
