from __future__ import annotations

import hashlib
import io
import json
import time
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _safe_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, indent=2, sort_keys=True, default=str).encode("utf-8")


def build_decision_report_pdf_bytes(
    *,
    systems_artifact: dict | None,
    point_artifact: dict | None,
    journal: list[dict] | None,
    top_candidates: list[dict] | None,
) -> bytes:
    """Build a compact, audit-friendly PDF decision report.

    Contents:
    - header + timestamp
    - artifact hashes (point/systems)
    - systems headline metrics (if present)
    - top candidates (up to 10)
    - decision journal (last 50 entries)
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    def line(y: float, text: str, size: int = 10):
        c.setFont("Helvetica", size)
        c.drawString(0.8*inch, y, text)

    y = h - 0.9*inch
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.8*inch, y, "SHAMS — Systems Mode Decision Report")
    y -= 0.35*inch
    c.setFont("Helvetica", 10)
    c.drawString(0.8*inch, y, time.strftime("Generated: %Y-%m-%d %H:%M:%S", time.localtime()))
    y -= 0.35*inch

    # Hashes
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.8*inch, y, "Artifact hashes (SHA-256)")
    y -= 0.22*inch
    c.setFont("Helvetica", 9)

    try:
        if systems_artifact is not None:
            b = _safe_json_bytes(systems_artifact)
            line(y, f"Systems artifact: {_sha256_bytes(b)}", 9); y -= 0.18*inch
        else:
            line(y, "Systems artifact: (none)", 9); y -= 0.18*inch
    except Exception:
        line(y, "Systems artifact: (hash failed)", 9); y -= 0.18*inch

    try:
        if point_artifact is not None:
            b = _safe_json_bytes(point_artifact)
            line(y, f"Point artifact:   {_sha256_bytes(b)}", 9); y -= 0.18*inch
        else:
            line(y, "Point artifact:   (none)", 9); y -= 0.18*inch
    except Exception:
        line(y, "Point artifact:   (hash failed)", 9); y -= 0.18*inch

    y -= 0.15*inch

    # Systems headline
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.8*inch, y, "Systems headline (if present)")
    y -= 0.22*inch
    c.setFont("Helvetica", 10)
    try:
        outs = (systems_artifact or {}).get("headline") or (systems_artifact or {}).get("outputs") or {}
        keys = ["Q_DT_eqv", "H98", "P_e_net_MW", "q_div_MW_m2", "q95", "beta_N"]
        for k in keys:
            if y < 1.1*inch:
                c.showPage(); y = h - 0.9*inch
            v = outs.get(k, None)
            line(y, f"{k}: {v}", 10)
            y -= 0.18*inch
    except Exception:
        line(y, "(headline unavailable)", 10)
        y -= 0.18*inch

    y -= 0.15*inch

    # Top candidates
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.8*inch, y, "Top candidates (up to 10)")
    y -= 0.22*inch
    c.setFont("Helvetica", 9)
    try:
        cand = list(top_candidates or [])[:10]
        if not cand:
            line(y, "(none)", 9); y -= 0.18*inch
        else:
            for i, cc in enumerate(cand, 1):
                if y < 1.1*inch:
                    c.showPage(); y = h - 0.9*inch
                    c.setFont("Helvetica", 9)
                hid = cc.get("inputs_hash") or cc.get("hash") or ""
                fam = cc.get("family") or ""
                fb = cc.get("failed_blocking") or []
                line(y, f"{i}. {hid}  {(' | ' + fam) if fam else ''}", 9); y -= 0.16*inch
                if fb:
                    line(y, f"   failed_blocking: {', '.join(map(str, fb[:6]))}{'...' if len(fb)>6 else ''}", 9); y -= 0.16*inch
    except Exception:
        line(y, "(candidates unavailable)", 9); y -= 0.18*inch

    y -= 0.15*inch

    # Journal
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.8*inch, y, "Decision journal (last 50)")
    y -= 0.22*inch
    c.setFont("Helvetica", 9)
    try:
        j = list(journal or [])[-50:]
        if not j:
            line(y, "(none)", 9); y -= 0.18*inch
        else:
            for e in j:
                if y < 1.1*inch:
                    c.showPage(); y = h - 0.9*inch
                    c.setFont("Helvetica", 9)
                ts = e.get("ts_unix", 0) or 0
                tss = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(ts))) if ts else "?"
                kind = e.get("kind", "")
                step = e.get("workflow_step", "")
                line(y, f"- {tss} [{kind}] step={step}", 9)
                y -= 0.16*inch
    except Exception:
        line(y, "(journal unavailable)", 9); y -= 0.18*inch

    c.showPage()
    c.save()
    return buf.getvalue()
