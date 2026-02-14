#!/usr/bin/env python
"""Generate human-readable release notes from two SHAMS baselines.

Typical usage (from repo root of the *new* version):

  python tools/release_notes.py --old ..\SHAMS_v28 --new . --out RELEASE_NOTES.md

Inputs can be either:
- a repo root (expects benchmarks/golden_artifacts/*.json)
- a single diff report json (benchmarks/last_diff_report.json)

The generator focuses on:
- structural changes: constraint set/meta + model card versions/hashes
- benchmark numeric deltas that exceed tolerance (if diff report provided)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from shams_io.structural_diff import structural_diff


def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _repo_golden_dir(repo: Path) -> Path:
    return repo / "benchmarks" / "golden_artifacts"


def _collect_artifacts(root_or_file: Path) -> Dict[str, Dict[str, Any]]:
    if root_or_file.is_file():
        data = _load_json(root_or_file)
        # If this is a diff report, we can't reconstruct artifacts. Return empty and rely on report sections.
        return {}
    ga = _repo_golden_dir(root_or_file)
    out = {}
    if ga.exists():
        for p in ga.glob("*.json"):
            out[p.stem] = _load_json(p)
    return out


def _collect_diff_report(root_or_file: Path) -> Dict[str, Any] | None:
    if root_or_file.is_file():
        data = _load_json(root_or_file)
        # heuristic for diff report
        if "rows" in data and "created_unix" in data:
            return data
        return None
    p = root_or_file / "benchmarks" / "last_diff_report.json"
    if p.exists():
        return _load_json(p)
    return None


def _summarize_structural(old_repo: Path, new_repo: Path) -> Dict[str, Any]:
    old_arts = _collect_artifacts(old_repo)
    new_arts = _collect_artifacts(new_repo)

    cases = sorted(set(old_arts.keys()) | set(new_arts.keys()))
    per_case = {}
    totals = {"cases": 0, "cases_with_changes": 0, "added_constraints": 0, "removed_constraints": 0, "changed_constraints": 0, "modelcard_changes": 0}

    for c in cases:
        if c not in old_arts or c not in new_arts:
            continue
        d = structural_diff(new_arts[c], old_arts[c])
        per_case[c] = d
        totals["cases"] += 1
        a = len(d["constraints"]["added"])
        r = len(d["constraints"]["removed"])
        ch = len(d["constraints"]["changed_meta"])
        mc = len(d["model_cards"]["added"]) + len(d["model_cards"]["removed"]) + len(d["model_cards"]["changed"])
        totals["added_constraints"] += a
        totals["removed_constraints"] += r
        totals["changed_constraints"] += ch
        totals["modelcard_changes"] += mc
        if a or r or ch or mc or (d["schema_version"]["new"] != d["schema_version"]["old"]):
            totals["cases_with_changes"] += 1

    return {"totals": totals, "per_case": per_case}


def _md_bullets(items: List[str]) -> str:
    return "\n".join([f"- {x}" for x in items]) if items else "- (none)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True, help="Old repo root or diff report json")
    ap.add_argument("--new", required=True, help="New repo root or diff report json")
    ap.add_argument("--out", default="", help="Write markdown to this path (default: stdout)")
    args = ap.parse_args()

    oldp = Path(args.old).resolve()
    newp = Path(args.new).resolve()

    old_rep = _collect_diff_report(oldp)
    new_rep = _collect_diff_report(newp)

    # Prefer repo structural diffs when repo roots provided
    struct = None
    if oldp.is_dir() and newp.is_dir():
        struct = _summarize_structural(oldp, newp)

    lines: List[str] = []
    lines.append(f"# SHAMS Release Notes\n")
    lines.append(f"Comparing:\n- Old: `{oldp}`\n- New: `{newp}`\n")

    if struct:
        t = struct["totals"]
        lines.append("## Structural changes (constraints & model cards)\n")
        lines.append(f"Cases compared: **{t['cases']}** (with changes: **{t['cases_with_changes']}**)\n")
        lines.append(f"- Constraints added: **{t['added_constraints']}**\n- Constraints removed: **{t['removed_constraints']}**\n- Constraint meta changes: **{t['changed_constraints']}**\n- Model card changes: **{t['modelcard_changes']}**\n")
        # Top few cases with changes
        changed_cases = []
        for c,d in struct["per_case"].items():
            if d["constraints"]["added"] or d["constraints"]["removed"] or d["constraints"]["changed_meta"] or d["model_cards"]["added"] or d["model_cards"]["removed"] or d["model_cards"]["changed"]:
                changed_cases.append(c)
        if changed_cases:
            lines.append("### Cases with notable structural changes\n")
            for c in changed_cases[:10]:
                d = struct["per_case"][c]
                lines.append(f"#### {c}\n")
                lines.append("**Constraints added**\n" + _md_bullets(d['constraints']['added']) + "\n")
                lines.append("**Constraints removed**\n" + _md_bullets(d['constraints']['removed']) + "\n")
                if d['constraints']['changed_meta']:
                    lines.append("**Constraint meta changes**\n")
                    for item in d['constraints']['changed_meta'][:10]:
                        fields = ", ".join(item['fields'].keys())
                        lines.append(f"- {item['name']}: {fields}")
                    lines.append("")
                if d['model_cards']['changed'] or d['model_cards']['added'] or d['model_cards']['removed']:
                    lines.append("**Model cards**\n")
                    lines.append("Added\n" + _md_bullets(d['model_cards']['added']) + "\n")
                    lines.append("Removed\n" + _md_bullets(d['model_cards']['removed']) + "\n")
                    if d['model_cards']['changed']:
                        lines.append("Changed\n")
                        for mc in d['model_cards']['changed'][:10]:
                            fields = ", ".join(mc['fields'].keys())
                            lines.append(f"- {mc['id']}: {fields}")
                        lines.append("")
        else:
            lines.append("No structural changes detected between the compared golden artifacts.\n")
    # Numeric diffs
    rep = new_rep
    if rep and "rows" in rep:
        bad = [r for r in rep["rows"] if not r.get("ok", True)]

        # Severity summary from latest diff report (if available)
        rep_for_sev = new_rep or old_rep or {}
        sev_counts = {}
        try:
            sev_counts = (rep_for_sev.get("structural_summary") or {}).get("severity_counts") or {}
        except Exception:
            sev_counts = {}

        if sev_counts:
            lines.append("## Structural diff severity\n")
            lines.append(
                f"- breaking: **{int(sev_counts.get('breaking', 0))}**\n"
                f"- warn: **{int(sev_counts.get('warn', 0))}**\n"
                f"- info: **{int(sev_counts.get('info', 0))}**\n"
            )

        lines.append("## Benchmark numeric deltas (failed tolerances)\n")
        lines.append(
            f"Failed rows: **{len(bad)}** (rtol={rep.get('rtol')}, atol={rep.get('atol')})\n"
        )
        for r in bad[:50]:
            try:
                lines.append(
                    f"- {r.get('case')} :: {r.get('key')}: got {float(r.get('got')):.6g} "
                    f"vs {float(r.get('golden')):.6g} (relerr={float(r.get('rel_err')):.3g})"
                )
            except Exception:
                lines.append(f"- {r}")
        if len(bad) > 50:
            lines.append(f"... ({len(bad)-50} more rows omitted)")
        lines.append("")

    # Structural summary from this run (if present)
    if rep and rep.get("structural_summary"):
        ss = rep["structural_summary"]
        lines.append("## Structural diffs vs golden (this run)\n")
        lines.append(
            f"Cases compared: **{ss.get('n_cases', 0)}**, "
            f"cases with changes: **{ss.get('n_with_changes', 0)}**\n"
        )
        lines.append(
            f"- Added constraints: {ss.get('total_added_constraints', 0)}\n"
            f"- Removed constraints: {ss.get('total_removed_constraints', 0)}\n"
            f"- Constraint changes: {ss.get('total_constraint_changes', 0)}\n"
            f"- Model card changes: {ss.get('total_modelcard_changes', 0)}\n"
        )
    out_md = "\n".join(lines).strip() + "\n"
    if args.out:
        Path(args.out).write_text(out_md, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(out_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
