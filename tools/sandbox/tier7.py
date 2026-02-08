"""Tier 7 + Epistemic Guarantees utilities (collaboration, standards, reproducibility).

This module is intentionally lightweight and SHAMS-native:
- No external services.
- No hidden optimization.
- Everything is exportable and provenance-stamped.

These helpers do **not** change evaluator physics, constraints, or policies.
They support:
  * Review sessions (comments/votes/tags over a candidate archive)
  * DOI-ready publication packs (zip bundles)
  * "SHAMS-certified feasible" badges for *audited* candidates
  * Regression benchmark execution (golden suite)

All file formats are JSON-first and schema-stable.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# -------------------------
# Hashing / fingerprints
# -------------------------

def _canon_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(obj: Any) -> str:
    return sha256_hex(_canon_json(obj).encode("utf-8"))


def repo_fingerprint(repo_root: Path) -> str:
    """Stable-ish repo fingerprint based on MANIFEST_SHA256.txt if present."""
    m = repo_root / "MANIFEST_SHA256.txt"
    if m.exists():
        return sha256_hex(m.read_bytes())
    # Fallback: hash of VERSION + ui/app.py sizes
    parts = {
        "version": (repo_root / "VERSION").read_text(encoding="utf-8").strip() if (repo_root / "VERSION").exists() else "",
        "ui_app_bytes": (repo_root / "ui" / "app.py").stat().st_size if (repo_root / "ui" / "app.py").exists() else 0,
        "time": int(time.time()),
    }
    return fingerprint(parts)


def candidate_fingerprint(candidate_inputs: Dict[str, Any], *, intent: str, evaluator_fp: str) -> str:
    return fingerprint({"intent": intent, "evaluator": evaluator_fp, "inputs": candidate_inputs})


# -------------------------
# Badge (SVG)
# -------------------------

def generate_cert_badge_svg(
    *,
    candidate_fp: str,
    intent: str,
    feasible: bool,
    version: str,
    evaluator_fp: str,
    note: str = "",
) -> str:
    """Generate a simple SVG badge for audited feasibility.

    Note: We avoid colors/styles that imply ranking. The badge is descriptive.
    """
    status = "FEASIBLE" if feasible else "INFEASIBLE"
    short_fp = candidate_fp[:12]
    short_eval = evaluator_fp[:12]
    note_line = f"<text x='24' y='128' font-size='12' fill='#111'>{_escape_xml(note)[:60]}</text>" if note else ""
    svg = f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns='http://www.w3.org/2000/svg' width='520' height='160'>
  <rect x='0' y='0' width='520' height='160' rx='16' ry='16' fill='#fff' stroke='#111' stroke-width='2'/>
  <text x='24' y='40' font-size='20' font-family='sans-serif' fill='#111'>SHAMS-certified (audited)</text>
  <text x='24' y='68' font-size='14' font-family='monospace' fill='#111'>status: {status}   intent: {intent}</text>
  <text x='24' y='92' font-size='12' font-family='monospace' fill='#111'>candidate_fp: {short_fp}</text>
  <text x='24' y='112' font-size='12' font-family='monospace' fill='#111'>evaluator_fp: {short_eval}   version: {version}</text>
  {note_line}
</svg>
"""
    return svg


def _escape_xml(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


# -------------------------
# Review sessions (local)
# -------------------------

@dataclass
class ReviewSession:
    session_id: str
    title: str
    created_at: str
    evaluator_fp: str
    intent: str
    candidates: List[Dict[str, Any]]
    notes: str = ""
    comments: List[Dict[str, Any]] = None
    votes: List[Dict[str, Any]] = None
    tags: List[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "shams.review_session.v1",
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "evaluator_fp": self.evaluator_fp,
            "intent": self.intent,
            "notes": self.notes,
            "candidates": self.candidates or [],
            "comments": self.comments or [],
            "votes": self.votes or [],
            "tags": self.tags or [],
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ReviewSession":
        return ReviewSession(
            session_id=str(d.get("session_id", "")),
            title=str(d.get("title", "")),
            created_at=str(d.get("created_at", "")),
            evaluator_fp=str(d.get("evaluator_fp", "")),
            intent=str(d.get("intent", "")),
            notes=str(d.get("notes", "")),
            candidates=list(d.get("candidates", []) or []),
            comments=list(d.get("comments", []) or []),
            votes=list(d.get("votes", []) or []),
            tags=list(d.get("tags", []) or []),
        )


def default_sessions_dir() -> Path:
    # user-local, not repo-committed
    p = Path.home() / ".shams" / "review_sessions"
    p.mkdir(parents=True, exist_ok=True)
    return p


def new_review_session(*, title: str, evaluator_fp: str, intent: str, notes: str = "") -> ReviewSession:
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    sid = fingerprint({"title": title, "created_at": created_at, "intent": intent})[:16]
    return ReviewSession(
        session_id=sid,
        title=title,
        created_at=created_at,
        evaluator_fp=evaluator_fp,
        intent=intent,
        candidates=[],
        notes=notes,
        comments=[],
        votes=[],
        tags=[],
    )


def save_review_session(sess: ReviewSession, path: Path) -> None:
    path.write_text(json.dumps(sess.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def load_review_session(path: Path) -> ReviewSession:
    return ReviewSession.from_dict(json.loads(path.read_text(encoding="utf-8")))


def export_review_session_zip(sess: ReviewSession) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("review_session.json", json.dumps(sess.to_dict(), indent=2, sort_keys=True))
        z.writestr("README.txt", "SHAMS Review Session\n\nContains comments/votes/tags for a candidate archive.\n")
    buf.seek(0)
    return buf.getvalue()


def import_review_session_zip(data: bytes) -> ReviewSession:
    with zipfile.ZipFile(io.BytesIO(data), "r") as z:
        d = json.loads(z.read("review_session.json").decode("utf-8"))
    return ReviewSession.from_dict(d)


# -------------------------
# DOI-ready publication pack
# -------------------------

def export_doi_ready_pack(
    *,
    repo_root: Path,
    run_meta: Dict[str, Any],
    archive_rows: List[Dict[str, Any]],
    trace_rows: List[Dict[str, Any]],
    extra_files: Optional[List[Tuple[str, bytes]]] = None,
) -> bytes:
    """Export a standards-oriented publication pack (zip).

    Includes citation + governance + freeze docs + run provenance.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # Core
        z.writestr("run_meta.json", json.dumps(run_meta, indent=2, sort_keys=True))
        z.writestr("archive.json", json.dumps(archive_rows, indent=2, sort_keys=True))
        z.writestr("trace.json", json.dumps(trace_rows, indent=2, sort_keys=True))
        # Standards
        for fn in ["CITATION.cff", "GOVERNANCE.md", "NON_OPTIMIZER_MANIFESTO.md", "ARCHITECTURE.md"]:
            p = repo_root / fn
            if p.exists():
                z.writestr(fn, p.read_text(encoding="utf-8"))
        # Freeze declarations (best effort)
        docs_dir = repo_root / "docs"
        if docs_dir.exists():
            for fn in [
                "SCANLAB_FREEZE.md",
                "PARETO_V1_FREEZE_DECLARATION.md",
            ]:
                p = docs_dir / fn
                if p.exists():
                    z.writestr(f"docs/{fn}", p.read_text(encoding="utf-8"))
        if extra_files:
            for name, content in extra_files:
                z.writestr(name, content)
        z.writestr(
            "README.md",
            "# SHAMS publication pack\n\nThis bundle is exportable and auditable.\n\n"
            "Contents:\n- run_meta.json (objective contract + bounds + provenance)\n"
            "- archive.json (candidate machine archive)\n- trace.json (run trace)\n"
            "- CITATION.cff + governance docs\n",
        )
    buf.seek(0)
    return buf.getvalue()


# -------------------------
# Regression runner
# -------------------------

def run_regression_suite(repo_root: Path, *, rtol: float = 0.01, atol: float = 1e-6) -> Dict[str, Any]:
    """Run benchmarks/run.py and return a structured report."""
    bench = repo_root / "benchmarks" / "run.py"
    if not bench.exists():
        return {"ok": False, "error": "benchmarks/run.py not found"}
    cmd = [
        os.environ.get("PYTHON", "python"),
        str(bench),
        "--write-diff",
        "--rtol",
        str(rtol),
        "--atol",
        str(atol),
    ]
    p = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    diff_path = repo_root / "benchmarks" / "last_diff_report.json"
    diff = None
    if diff_path.exists():
        try:
            diff = json.loads(diff_path.read_text(encoding="utf-8"))
        except Exception:
            diff = None
    return {"ok": p.returncode == 0, "returncode": p.returncode, "output": out, "diff": diff}
