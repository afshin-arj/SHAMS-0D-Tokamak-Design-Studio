"""Scan Lab — expert UX features (0-D).

This module adds *argument-grade* and *trust-grade* utilities:

- Scan Lab contract text
- Physics/policy fingerprinting for citation-grade provenance
- Claim Builder (evidence-backed; exportable as a 1-page PDF)
- Falsification helpers (counterexample surfacing)

All utilities are deterministic and do not change Point Designer physics.
"""

from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


SCAN_LAB_CONTRACT = (
    "**Scan Lab Contract (0‑D)**\n"
    "- Scan Lab evaluates the frozen **Point Designer** 0‑D physics at many points.\n"
    "- Scan Lab does **not** optimize, relax constraints, or recommend designs.\n"
    "- Scan Lab reveals **constraint structure**: dominant limiters, first‑failure order, regimes, and robustness.\n"
    "- Empty regions are informative: they mean *no blocking-feasible points* exist in that projection under the current assumptions.\n"
    "- Any conclusion is conditional on the **assumptions** and **policy lens (intent)** shown in the report.\n"
)


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def file_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return _sha256_bytes(f.read())


def compute_fingerprints(repo_root: str) -> Dict[str, str]:
    """Return a stable set of fingerprints for citation-grade provenance.

    We avoid Git introspection (not always available) and instead hash a small set
    of critical, stable files that encode physics + constraint policies + intent.

    If a file is missing, it is omitted.
    """

    candidates = {
        "ui_app": os.path.join(repo_root, "ui", "app.py"),
        "requirements_trace": os.path.join(repo_root, "src", "decision", "requirements_trace.py"),
        "scan_cartography": os.path.join(repo_root, "tools", "scan_cartography.py"),
        "scan_insights": os.path.join(repo_root, "tools", "scan_insights.py"),
        "scan_next_tier": os.path.join(repo_root, "tools", "scan_next_tier.py"),
        "constraints_pkg": os.path.join(repo_root, "src", "constraints", "__init__.py"),
        "physics_pkg": os.path.join(repo_root, "src", "physics", "__init__.py"),
    }

    out: Dict[str, str] = {}
    for k, p in candidates.items():
        try:
            if os.path.exists(p) and os.path.isfile(p):
                out[k] = file_sha256(p)[:16]
        except Exception:
            continue

    # Aggregate fingerprint for quick display
    agg = hashlib.sha256()
    for k in sorted(out.keys()):
        agg.update(k.encode("utf-8"))
        agg.update(out[k].encode("utf-8"))
    out["fingerprint"] = agg.hexdigest()[:16]
    return out


@dataclass
class ScanClaim:
    title: str
    statement: str
    intent: str
    claim_type: str
    notes: str = ""


def _dominance_stats(report: Dict[str, Any], intent: str) -> Dict[str, Any]:
    pts = report.get("points") or []
    doms: List[str] = []
    ok = 0
    for r in pts:
        it = ((r.get("intent") or {}).get(intent) or {})
        dom = str(it.get("dominant_blocking") or "PASS")
        doms.append(dom)
        if bool(it.get("blocking_feasible")):
            ok += 1
    total = max(len(doms), 1)
    counts = {d: doms.count(d) for d in sorted(set(doms))}
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "n_points": int(len(doms)),
        "blocking_feasible_fraction": float(ok) / float(total),
        "dominance_counts": counts,
        "dominance_top": top[:5],
    }


def falsify_claim(report: Dict[str, Any], intent: str, claim_type: str, expected: Optional[str] = None) -> Dict[str, Any]:
    """Surface counterexamples for a small set of claim types.

    Returns a summary + up to N example points.
    """

    pts = report.get("points") or []
    examples: List[Dict[str, Any]] = []

    if claim_type == "dominance":
        # Expected dominant constraint
        exp = str(expected or "")
        for r in pts:
            it = ((r.get("intent") or {}).get(intent) or {})
            dom = str(it.get("dominant_blocking") or "PASS")
            if exp and dom != exp:
                examples.append({"x": r.get("x"), "y": r.get("y"), "dominant": dom, "blocking_feasible": it.get("blocking_feasible")})
        return {
            "ok": True,
            "type": "dominance",
            "intent": intent,
            "expected": exp,
            "n_counterexamples": int(len(examples)),
            "examples": examples[:25],
            "note": "Counterexamples are points whose dominant blocking constraint differs from the expected one.",
        }

    if claim_type == "robustness":
        # Expected robustness label
        exp = str(expected or "")
        for r in pts:
            it = ((r.get("intent") or {}).get(intent) or {})
            rb = str(it.get("robustness_label") or "")
            if exp and rb != exp:
                examples.append({"x": r.get("x"), "y": r.get("y"), "robustness": rb, "blocking_feasible": it.get("blocking_feasible")})
        return {
            "ok": True,
            "type": "robustness",
            "intent": intent,
            "expected": exp,
            "n_counterexamples": int(len(examples)),
            "examples": examples[:25],
            "note": "Counterexamples are points whose robustness label differs from the expected one.",
        }

    # Fallback: report dominance entropy hotspots if available
    return {
        "ok": False,
        "reason": "unsupported_claim_type",
        "supported": ["dominance", "robustness"],
    }


def build_claim_evidence(report: Dict[str, Any], intent: str) -> Dict[str, Any]:
    """Build a compact, reproducible evidence packet for Claim Builder."""
    stats = _dominance_stats(report, intent)
    nar = ((report.get("narrative") or {}).get("intents") or {}).get(intent, {})
    cliffs = ((report.get("topology") or {}).get("intents") or {}).get(intent, {})
    return {
        "intent": intent,
        "id": report.get("id"),
        "x_key": report.get("x_key"),
        "y_key": report.get("y_key"),
        "stats": stats,
        "narrative": {
            "plain_language": nar.get("plain_language"),
            "dominant": nar.get("dominant"),
            "feasible_fraction": nar.get("feasible_fraction"),
        },
        "cliffs": {
            "n_components": cliffs.get("n_components"),
            "holes": cliffs.get("holes"),
        },
    }


def build_claim_pdf_bytes(*, claim: ScanClaim, evidence: Dict[str, Any], map_png: Optional[bytes] = None, fingerprint: Optional[Dict[str, str]] = None) -> bytes:
    """Create a 1-page PDF slide summarizing a claim with attached evidence."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    W, H = LETTER

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.75 * inch, H - 0.85 * inch, "SHAMS — Scan Lab Claim")
    c.setFont("Helvetica", 10)
    c.drawString(0.75 * inch, H - 1.1 * inch, f"Intent: {claim.intent}   Scan ID: {evidence.get('id')}   Axes: {evidence.get('x_key')} × {evidence.get('y_key')}")

    # Claim
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75 * inch, H - 1.45 * inch, claim.title[:90])
    c.setFont("Helvetica", 10)
    y = H - 1.65 * inch
    for line in _wrap(claim.statement, 100):
        c.drawString(0.75 * inch, y, line)
        y -= 0.18 * inch

    # Evidence box
    y -= 0.05 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.75 * inch, y, "Evidence")
    y -= 0.22 * inch
    c.setFont("Helvetica", 9)
    stats = (evidence.get("stats") or {})
    top = (stats.get("dominance_top") or [])
    ff = stats.get("blocking_feasible_fraction")
    c.drawString(0.75 * inch, y, f"Blocking-feasible fraction: {ff:.0%}" if isinstance(ff, (int, float)) else "Blocking-feasible fraction: n/a")
    y -= 0.18 * inch
    if top:
        c.drawString(0.75 * inch, y, "Top dominant constraints: " + ", ".join([f"{a} ({b})" for a, b in top]))
        y -= 0.18 * inch

    nar = (evidence.get("narrative") or {}).get("plain_language")
    if nar:
        y -= 0.05 * inch
        c.setFont("Helvetica-Oblique", 9)
        for line in _wrap(str(nar), 105)[:5]:
            c.drawString(0.75 * inch, y, line)
            y -= 0.17 * inch
        c.setFont("Helvetica", 9)

    # Map (optional)
    if map_png:
        try:
            img = ImageReader(io.BytesIO(map_png))
            c.drawImage(img, 0.75 * inch, 0.85 * inch, width=6.9 * inch, height=3.9 * inch, preserveAspectRatio=True, anchor="sw")
        except Exception:
            c.setFont("Helvetica", 9)
            c.drawString(0.75 * inch, 0.95 * inch, "(map unavailable)")

    # Footer fingerprints
    if fingerprint:
        c.setFont("Helvetica", 7)
        fp = fingerprint.get("fingerprint") or ""
        c.drawString(0.75 * inch, 0.6 * inch, f"Fingerprint: {fp}   (ui:{fingerprint.get('ui_app')} req:{fingerprint.get('requirements_trace')})")

    c.showPage()
    c.save()
    return buf.getvalue()


def _wrap(text: str, width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    line = ""
    for w in words:
        if len(line) + len(w) + 1 > width:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        lines.append(line)
    return lines
