"""Independence Phase 4.3 — Phase 4 exit evidence checklist.

Assembles an honest, deterministic evidence pack stating what must be true
to declare that *new studies can default to citing SHAMS* (VERSION + artifact
hashes) without depending on PROCESS as feasibility authority.

Honesty (non-negotiable)
------------------------
* Never claims blanket "PROCESS retired".
* Community adoption and APPROVED DOI are EXTERNAL / PENDING — code cannot mark
  them DONE without evidence.
* Scientific release remains CONDITIONAL until APPROVED evidence exists.
* PENDING items cannot be flipped to DONE via mutation without evidence anchors.

L0 risk: none (reads VERSION, docs, benchmarks, prior Phase 4 artifacts only).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

EXIT_SCHEMA = "shams.independence_exit_evidence.v1"
_REPORT_EPOCH_UNIX = 0.0

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON_OUT = (
    _REPO_ROOT / "docs" / "validation" / "reports" / "independence_exit_evidence.json"
)
DEFAULT_MD_OUT = _REPO_ROOT / "docs" / "INDEPENDENCE_EXIT_EVIDENCE.md"

# Status vocabulary — EXTERNAL means "requires outside-world evidence".
ALLOWED_ITEM_STATUS = {"DONE", "PENDING", "EXTERNAL", "CONDITIONAL"}

_FORBIDDEN_BLANKET_PATTERNS = (
    re.compile(r"\bprocess\s+is\s+retired\b", re.I),
    re.compile(r"\bprocess\s+has\s+been\s+retired\b", re.I),
    re.compile(r"\bprocess\s+retired\b(?!\s+claim)", re.I),
    re.compile(r"\bprocess\s+fully\s+retired\b", re.I),
)


def _canon_for_hash(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _canon_for_hash(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (list, tuple)):
        return [_canon_for_hash(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj):
            return "NaN"
        if math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        return obj
    return obj


def canonical_dumps(obj: Any) -> str:
    return json.dumps(_canon_for_hash(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(obj: Any) -> str:
    return hashlib.sha256(canonical_dumps(obj).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_shams_version(repo_root: Optional[Path] = None) -> str:
    root = repo_root or _REPO_ROOT
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"


def _file_anchor(path: Path, *, label: str, repo_root: Path) -> Dict[str, Any]:
    try:
        rel = str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except Exception:
        rel = str(path).replace("\\", "/")
    exists = path.is_file()
    row: Dict[str, Any] = {"label": label, "path": rel, "exists": exists}
    if exists:
        row["sha256"] = sha256_file(path)
        row["bytes"] = path.stat().st_size
    else:
        row["sha256"] = None
        row["bytes"] = None
    return row


def _assert_no_blanket_retirement(text: str) -> None:
    plain = re.sub(r"[*_`]", "", text)
    lower = plain.lower()
    for pat in _FORBIDDEN_BLANKET_PATTERNS:
        for m in pat.finditer(plain):
            start = max(0, m.start() - 64)
            end = min(len(lower), m.end() + 48)
            window_before = lower[start : m.start()]
            window_after = lower[m.end() : end]
            if any(
                neg in window_before
                for neg in (
                    "does not claim",
                    "do not claim",
                    "never claim",
                    "not claim",
                    "no blanket",
                    "without scoped",
                    "not retired",
                    "never emits",
                    "refuses",
                    "anti-overclaim",
                    "forbidden",
                    "blanket",
                    "process_retired_claimed",
                    "process-retired claim",
                )
            ):
                continue
            if window_after.lstrip().startswith("?") or re.match(
                r"\s*[:?]?\s*(no|false|never)\b", window_after
            ):
                continue
            raise ValueError(
                f"Unqualified PROCESS-retirement language near: {plain[m.start() - 20 : m.end() + 20]!r}"
            )


# Checklist specs: (item_id, title, required_status_class, evidence paths relative to repo)
# required_status_class: "shipped" (in-repo DONE when anchors exist),
# "conditional" (DONE only as CONDITIONAL), "external" (always EXTERNAL until outside evidence).
_CHECKLIST_SPECS: Tuple[Dict[str, Any], ...] = (
    {
        "item_id": "cite_shams_handoff_pack",
        "title": "Cite-SHAMS citation unit shipped",
        "class": "shipped",
        "paths": (
            "src/reports/cite_shams_handoff_pack.py",
            "docs/CITE_SHAMS_HANDOFF.md",
            "tests/test_cite_shams_handoff_pack.py",
        ),
        "why": "New studies can export VERSION + artifact SHA-256 packs without PROCESS.",
    },
    {
        "item_id": "scoped_retirement_report",
        "title": "Scoped PROCESS retirement evidence report",
        "class": "shipped",
        "paths": (
            "src/reports/process_retirement_report.py",
            "docs/PROCESS_RETIREMENT_REPORT.md",
            "docs/validation/reports/process_retirement_report.json",
            "tests/test_process_retirement_report.py",
        ),
        "why": "Domain coverage is evidence-backed; blanket retirement is refused.",
    },
    {
        "item_id": "migration_guide",
        "title": "PROCESS → SHAMS migration path live",
        "class": "shipped",
        "paths": (
            "docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md",
            "tests/test_process_migration_guide.py",
        ),
        "why": "Labs can map IN.DAT/MFILE workflows onto Cases and artifacts.",
    },
    {
        "item_id": "champion_templates",
        "title": "Champion feasibility templates",
        "class": "shipped",
        "paths": (
            "docs/CHAMPION_CASES.md",
            "benchmarks/champions/cases.json",
            "src/studies/champion_cases.py",
            "tests/test_champion_cases.py",
        ),
        "why": "SHAMS-only reproducible studies with citation hashes and NO-SOLUTION stories.",
    },
    {
        "item_id": "parity_contribution_channel",
        "title": "Parity contribution channel open",
        "class": "shipped",
        "paths": (
            "docs/PARITY_CONTRIBUTION.md",
            "src/parity_harness/contribution.py",
            "benchmarks/parity/contributions/submission_template.json",
            "tests/test_parity_contribution_and_exit_evidence.py",
        ),
        "why": "Labs can submit licensed PROCESS refs and receive hashed SHAMS delta dossiers.",
    },
    {
        "item_id": "ccfs_firewall",
        "title": "CCFS propose-only firewall",
        "class": "shipped",
        "paths": (
            "src/extopt/certified_solve.py",
            "tests/test_ccfs_verified_hard_gate.py",
        ),
        "why": "Optimizers (including PROCESS) propose inputs only; SHAMS re-certifies.",
    },
    {
        "item_id": "no_solution_atlas",
        "title": "NO-SOLUTION atlas on infeasible artifacts",
        "class": "shipped",
        "paths": (
            "src/diagnostics/no_solution_atlas.py",
            "tests/test_no_solution_atlas.py",
        ),
        "why": "Infeasibility is attributed, not negotiated away.",
    },
    {
        "item_id": "scientific_release_conditional",
        "title": "Scientific release gate (CONDITIONAL)",
        "class": "conditional",
        "paths": (
            "docs/validation/reports/scientific_release_readiness_20260716.md",
            "docs/LIMITATIONS.md",
            "tests/test_scientific_release_gate.py",
        ),
        "why": "Community-facing release is CONDITIONAL with documented limitations — not APPROVED.",
    },
    {
        "item_id": "approved_zenodo_doi",
        "title": "APPROVED release + Zenodo DOI",
        "class": "external",
        "paths": (
            "docs/RELEASE_ARCHIVAL_CHECKLIST.md",
            ".zenodo.json",
            "CITATION.cff",
        ),
        "why": "Packaging exists; DOI mint and APPROVED verdict require external archival evidence.",
    },
    {
        "item_id": "community_adoption",
        "title": "Community adoption (new studies cite SHAMS by default)",
        "class": "external",
        "paths": (),
        "why": (
            "Whether labs actually start new studies in SHAMS is EXTERNAL evidence — "
            "shipping code cannot claim adoption."
        ),
    },
)


def _resolve_item_status(
    spec: Dict[str, Any],
    *,
    repo_root: Path,
) -> Tuple[str, List[Dict[str, Any]], Optional[str]]:
    """Return (status, anchors, note)."""
    anchors: List[Dict[str, Any]] = []
    for rel in spec.get("paths") or ():
        anchors.append(_file_anchor(repo_root / rel, label=str(rel), repo_root=repo_root))

    cls = str(spec["class"])
    if cls == "external":
        # External items stay EXTERNAL even if packaging paths exist.
        missing = [a for a in anchors if not a.get("exists")]
        note = None
        if anchors and missing:
            note = f"Packaging anchors incomplete: {[a['path'] for a in missing]}"
        elif anchors and all(a.get("exists") for a in anchors):
            note = "Packaging/checklist anchors present; adoption/DOI still EXTERNAL."
        else:
            note = "Requires outside-world evidence; cannot be marked DONE by code."
        return "EXTERNAL", anchors, note

    if cls == "conditional":
        if anchors and all(a.get("exists") for a in anchors):
            # Confirm CONDITIONAL language in release gate if present
            gate = repo_root / "docs" / "validation" / "reports" / "scientific_release_readiness_20260716.md"
            status = "CONDITIONAL"
            if gate.is_file():
                text = gate.read_text(encoding="utf-8")
                if re.search(r"\bAPPROVED\b", text) and not re.search(r"\bCONDITIONAL\b", text):
                    # Should not happen; keep CONDITIONAL if CONDITIONAL present
                    pass
            return status, anchors, "Release remains CONDITIONAL — not APPROVED."
        return "PENDING", anchors, "Missing conditional-release anchors."

    # shipped
    if not anchors:
        return "PENDING", anchors, "No evidence paths declared."
    if all(a.get("exists") for a in anchors):
        return "DONE", anchors, None
    missing = [a["path"] for a in anchors if not a.get("exists")]
    return "PENDING", anchors, f"Missing anchors: {missing}"


def validate_exit_evidence_honesty(report: Dict[str, Any]) -> List[str]:
    """Return honesty violations (empty = OK)."""
    issues: List[str] = []
    honesty = report.get("honesty") if isinstance(report.get("honesty"), dict) else {}
    verdict = report.get("verdict") if isinstance(report.get("verdict"), dict) else {}

    if honesty.get("process_retired_claimed") is not False:
        issues.append("honesty.process_retired_claimed must be false")
    if honesty.get("community_adoption_claimed") is not False:
        issues.append("honesty.community_adoption_claimed must be false")
    if honesty.get("approved_doi_claimed") is not False:
        issues.append("honesty.approved_doi_claimed must be false")
    if honesty.get("invented_mfile") is not False:
        issues.append("honesty.invented_mfile must be false")
    if verdict.get("blanket_process_retired") is not False:
        issues.append("verdict.blanket_process_retired must be false")
    if verdict.get("phase4_exit_complete") is not False:
        # Must stay false while EXTERNAL items remain
        issues.append("verdict.phase4_exit_complete must be false while EXTERNAL items remain")

    items = report.get("checklist") if isinstance(report.get("checklist"), list) else []
    by_id = {str(i.get("item_id")): i for i in items if isinstance(i, dict)}

    for eid in ("community_adoption", "approved_zenodo_doi"):
        row = by_id.get(eid)
        if row is None:
            issues.append(f"missing required EXTERNAL checklist item: {eid}")
            continue
        if row.get("status") == "DONE":
            issues.append(
                f"{eid} cannot be marked DONE without external evidence "
                "(status must remain EXTERNAL or PENDING)"
            )
        if row.get("status") not in ("EXTERNAL", "PENDING"):
            issues.append(f"{eid} status must be EXTERNAL or PENDING (got {row.get('status')!r})")

    rel = by_id.get("scientific_release_conditional")
    if rel is not None and rel.get("status") == "DONE":
        issues.append(
            "scientific_release_conditional must be CONDITIONAL (not DONE) — APPROVED not evidenced"
        )
    if rel is not None and rel.get("status") not in ("CONDITIONAL", "PENDING"):
        issues.append(
            f"scientific_release_conditional status invalid: {rel.get('status')!r}"
        )

    # PENDING/EXTERNAL cannot silently become DONE via honesty mutation check:
    # any item with class external in evidence must not be DONE
    for row in items:
        if not isinstance(row, dict):
            continue
        if row.get("evidence_class") == "external" and row.get("status") == "DONE":
            issues.append(
                f"{row.get('item_id')}: EXTERNAL evidence class cannot be DONE"
            )

    try:
        _assert_no_blanket_retirement(canonical_dumps(report))
    except ValueError as exc:
        issues.append(str(exc))

    return issues


def build_independence_exit_evidence(
    *,
    repo_root: Optional[Path] = None,
    created_unix: float = _REPORT_EPOCH_UNIX,
) -> Dict[str, Any]:
    """Build deterministic Phase 4 exit evidence report."""
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    version = read_shams_version(root)

    checklist: List[Dict[str, Any]] = []
    for spec in _CHECKLIST_SPECS:
        status, anchors, note = _resolve_item_status(spec, repo_root=root)
        row: Dict[str, Any] = {
            "item_id": spec["item_id"],
            "title": spec["title"],
            "status": status,
            "evidence_class": spec["class"],
            "why": spec["why"],
            "anchors": anchors,
        }
        if note:
            row["note"] = note
        checklist.append(row)

    n_done = sum(1 for i in checklist if i["status"] == "DONE")
    n_conditional = sum(1 for i in checklist if i["status"] == "CONDITIONAL")
    n_pending = sum(1 for i in checklist if i["status"] == "PENDING")
    n_external = sum(1 for i in checklist if i["status"] == "EXTERNAL")

    # Phase 4 engineering exit is met when all *shipped* items are DONE and
    # release is CONDITIONAL — but full independence exit stays open while EXTERNAL remain.
    shipped_ids = {s["item_id"] for s in _CHECKLIST_SPECS if s["class"] == "shipped"}
    shipped_done = all(
        i["status"] == "DONE" for i in checklist if i["item_id"] in shipped_ids
    )

    report: Dict[str, Any] = {
        "schema": EXIT_SCHEMA,
        "created_unix": float(created_unix),
        "shams_version": version,
        "campaign": {
            "name": "PROCESS independence",
            "phase": 4,
            "ticket": "4.3",
            "title": "Parity contribution process + independence exit evidence",
        },
        "checklist": checklist,
        "summary": {
            "n_items": len(checklist),
            "n_done": n_done,
            "n_conditional": n_conditional,
            "n_pending": n_pending,
            "n_external": n_external,
            "shipped_gates_met": shipped_done,
        },
        "verdict": {
            "blanket_process_retired": False,
            "phase4_engineering_complete": bool(shipped_done and n_pending == 0),
            "phase4_exit_complete": False,  # EXTERNAL items remain
            "release_status": "CONDITIONAL",
            "statement": (
                "In-repo independence engineering for Phase 4.3 is evidence-backed "
                "(citation unit, scoped retirement report, migration, champions, "
                "parity contribution channel, CCFS, atlas). "
                "Full Phase-4 *exit* (new studies default to citing SHAMS in the wild) "
                "remains open: community adoption and APPROVED DOI are EXTERNAL. "
                "Do not claim PROCESS retired."
            ),
        },
        "honesty": {
            "process_retired_claimed": False,
            "community_adoption_claimed": False,
            "approved_doi_claimed": False,
            "invented_mfile": False,
            "numeric_parity_requires_lab_mfile": True,
            "statement": (
                "This report records engineering evidence only. "
                "EXTERNAL checklist items cannot be marked DONE by regenerating this artifact."
            ),
        },
    }
    report["report_sha256"] = sha256_hex(
        {k: v for k, v in report.items() if k != "report_sha256"}
    )
    return report


def render_independence_exit_markdown(report: Dict[str, Any]) -> str:
    """Render human-readable exit evidence markdown."""
    lines: List[str] = []
    lines.append("# SHAMS independence exit evidence (Phase 4.3)")
    lines.append("")
    lines.append(
        f"**Schema:** `{report.get('schema')}`  "
        f"**SHAMS VERSION:** `{report.get('shams_version')}`  "
        f"**Report SHA-256:** `{report.get('report_sha256')}`"
    )
    lines.append("")
    lines.append("## Stance")
    lines.append("")
    lines.append(
        "PROCESS remains available as an optional proposer / legacy reproduce path. "
        "SHAMS is the feasibility authority for admissible designs, NO-SOLUTION attribution, "
        "and citeable VERSION + artifact hashes. "
        "**Blanket PROCESS-retirement claim?** **NO**."
    )
    lines.append("")
    verdict = report.get("verdict") if isinstance(report.get("verdict"), dict) else {}
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    lines.append("## Verdict")
    lines.append("")
    lines.append(f"- Phase 4 engineering complete (shipped gates): **{verdict.get('phase4_engineering_complete')}**")
    lines.append(f"- Phase 4 full exit complete: **{verdict.get('phase4_exit_complete')}**")
    lines.append(f"- Scientific release status: **{verdict.get('release_status')}**")
    lines.append(f"- Blanket PROCESS retired: **{verdict.get('blanket_process_retired')}**")
    lines.append("")
    lines.append(str(verdict.get("statement") or ""))
    lines.append("")
    lines.append("## Checklist")
    lines.append("")
    lines.append("| Status | Item | Evidence class |")
    lines.append("|--------|------|----------------|")
    for item in report.get("checklist") or []:
        if not isinstance(item, dict):
            continue
        lines.append(
            f"| `{item.get('status')}` | {item.get('title')} "
            f"(`{item.get('item_id')}`) | {item.get('evidence_class')} |"
        )
    lines.append("")
    lines.append(
        f"Counts: DONE={summary.get('n_done')}, CONDITIONAL={summary.get('n_conditional')}, "
        f"PENDING={summary.get('n_pending')}, EXTERNAL={summary.get('n_external')}."
    )
    lines.append("")
    lines.append("## Item detail")
    lines.append("")
    for item in report.get("checklist") or []:
        if not isinstance(item, dict):
            continue
        lines.append(f"### {item.get('title')} — `{item.get('status')}`")
        lines.append("")
        lines.append(str(item.get("why") or ""))
        if item.get("note"):
            lines.append("")
            lines.append(f"*Note:* {item['note']}")
        anchors = item.get("anchors") if isinstance(item.get("anchors"), list) else []
        if anchors:
            lines.append("")
            lines.append("Anchors:")
            for a in anchors:
                if not isinstance(a, dict):
                    continue
                exists = "yes" if a.get("exists") else "missing"
                digest = a.get("sha256") or "—"
                lines.append(f"- `{a.get('path')}` ({exists}; sha256=`{digest}`)")
        lines.append("")
    lines.append("## Honesty")
    lines.append("")
    honesty = report.get("honesty") if isinstance(report.get("honesty"), dict) else {}
    lines.append(str(honesty.get("statement") or ""))
    lines.append("")
    lines.append("- `process_retired_claimed`: false")
    lines.append("- `community_adoption_claimed`: false")
    lines.append("- `approved_doi_claimed`: false")
    lines.append("- `invented_mfile`: false")
    lines.append("")
    lines.append("## Related")
    lines.append("")
    lines.append("- `docs/PARITY_CONTRIBUTION.md` — lab contribution process")
    lines.append("- `docs/PROCESS_RETIREMENT_REPORT.md` — scoped coverage")
    lines.append("- `docs/CITE_SHAMS_HANDOFF.md` — citation pack")
    lines.append("- `docs/PROCESS_SURPASS_ROADMAP.md` — campaign roadmap")
    lines.append("")
    return "\n".join(lines)


def write_independence_exit_evidence(
    *,
    repo_root: Optional[Path] = None,
    json_out: Optional[Path] = None,
    md_out: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build, validate, and write JSON + markdown artifacts."""
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    report = build_independence_exit_evidence(repo_root=root)
    issues = validate_exit_evidence_honesty(report)
    if issues:
        raise ValueError("exit evidence honesty failed: " + "; ".join(issues))

    jpath = Path(json_out) if json_out is not None else (root / "docs" / "validation" / "reports" / "independence_exit_evidence.json")
    mpath = Path(md_out) if md_out is not None else (root / "docs" / "INDEPENDENCE_EXIT_EVIDENCE.md")
    jpath.parent.mkdir(parents=True, exist_ok=True)
    jpath.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mpath.write_text(render_independence_exit_markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    r = write_independence_exit_evidence()
    print(f"wrote exit evidence sha256={r['report_sha256']} version={r['shams_version']}")
